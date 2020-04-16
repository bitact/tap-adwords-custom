from datetime import datetime, timedelta
import backoff
import requests

import singer
from singer import metrics
from singer import utils
import googleads
import sys
from googleads import adwords
from googleads import oauth2
from oauth2client import client
import xml.etree.ElementTree as ET
import time 

SCOPE = 'https://www.googleapis.com/auth/adwords'
RETRY_SLEEP_TIME = 60
VERSION = 'v201809'
MAX_ATTEMPTS = 3
LOGGER = singer.get_logger()

def with_retries_on_exception(sleepy_time, max_attempts):
    def wrap(some_function):
        def wrapped_function(*args):
            attempts = 1
            ex = None
            result = None

            try:
                result = some_function(*args)
            except Exception as our_ex:
                ex = our_ex

            while ex and attempts < max_attempts:
                LOGGER.warning("attempt {} of {} failed".format(attempts, some_function))
                LOGGER.warning("waiting {} seconds before retrying".format(sleepy_time))
                time.sleep(RETRY_SLEEP_TIME)
                try:
                    ex = None
                    result = some_function(*args)
                except Exception as our_ex:
                    ex = our_ex

                attempts = attempts + 1

            if ex:
                LOGGER.critical("Error encountered when contacting Google AdWords API after {} retries".format(MAX_ATTEMPTS))
                raise ex #pylint: disable=raising-bad-type

            return result
        return wrapped_function
    return wrap


class AdwordsClient: # pylint: disable=too-many-instance-attributes
    def __init__(self,
                 client_id,
                 client_secret,
                 developer_token,
                 refresh_token,
                 customer_id,
                 user_agent=''):
                 
        self.__client_id = client_id
        self.__client_secret = client_secret
        self.__refresh_token = refresh_token
        self.__developer_token = developer_token
        self.__customer_id = customer_id
        self.__user_agent = user_agent
        self.__scope = u'https://www.googleapis.com/auth/adwords'

        self._validate_refresh_token()
        self.__sdk_client = self._create_sdk_client()

    def _validate_refresh_token(self):
        if not self.__refresh_token:
            LOGGER.error('refresh_token is missing. Please follow steps below and update it')
            self.__generate_refresh_token()
            sys.exit(1)

    def get_report_definition_service(self, report_type):
        report_definition_service = self.__sdk_client.GetService(
            'ReportDefinitionService', version=VERSION)
        fields = report_definition_service.getReportFields(report_type)
        return fields    

    @classmethod
    def get_report_types_service(cls, reports):
        url = f'https://adwords.google.com/api/adwords/reportdownload/{VERSION}/reportDefinition.xsd'
        xsd = requests.get(url).text
        root = ET.fromstring(xsd)
        nodes = list(root.find(".//*[@name='ReportDefinition.ReportType']/*"))
        return [p.attrib['value'] for p in nodes if p.attrib['value'] in reports]

    def _create_sdk_client(self):
        oauth2_client = oauth2.GoogleRefreshTokenClient(self.__client_id, \
                                                        self.__client_secret, \
                                                        self.__refresh_token)

        sdk_client = adwords.AdWordsClient(self.__developer_token, oauth2_client, \
                                            user_agent=self.__user_agent, \
                                            client_customer_id=self.__customer_id)

        return  sdk_client            

    @with_retries_on_exception(RETRY_SLEEP_TIME, MAX_ATTEMPTS)
    def report_download(self, report):    
        try:
            report_downloader = self.__sdk_client.GetReportDownloader(version=VERSION)
            result = report_downloader.DownloadReportAsStream(
                    report, skip_report_header=True, skip_column_header=False,
                    skip_report_summary=True,
                    include_zero_impressions=False)
        except Exception as exc:
            LOGGER.info(exc)            
        return result

    def _generate_refresh_token(self):
        flow = client.OAuth2WebServerFlow(
            client_id=self.__client_id,
            client_secret=self.__client_secret,
            scope=[SCOPE],
            user_agent='Ads Python Client Library',
            redirect_uri='urn:ietf:wg:oauth:2.0:oob')

        authorize_url = flow.step1_get_authorize_url()

        print(f'Log into the Google Account you use to access your AdWords account and go to the following URL: \n{authorize_url}\n')
        print('After approving the token enter the verification code (if specified).')

        code = input('Code: ').strip()

        try:
            credential = flow.step2_exchange(code)
            LOGGER.info(f'Please copy the following to config, access_token : {credential.access_token}, refresh_token : {credential.refresh_token}')             
        except client.FlowExchangeError as flow_exchange_error:
            print('Authentication has failed: %s' % flow_exchange_error)
        