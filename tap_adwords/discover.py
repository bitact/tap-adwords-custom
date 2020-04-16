import requests 
import json 
import singer
import os
import sys
from singer import metrics
from singer import bookmarks
from singer import utils
from singer import metadata
from singer import (transform,
                    UNIX_MILLISECONDS_INTEGER_DATETIME_PARSING,
                    Transformer)
import xml.etree.ElementTree as ET
from .client import AdwordsClient
from .reports import VERIFIED_REPORTS_NO_DATE, \
    VERIFIED_REPORTS, REPORTS_WITH_90_DAY_MAX, REPORT_TYPE_MAPPINGS


LOGGER = singer.get_logger()
SESSION = requests.Session()


def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def load_schema(entity):
    return utils.load_json(get_abs_path("schemas/{}.json".format(entity)))


def load_metadata(entity):
    return utils.load_json(get_abs_path("metadata/{}.json".format(entity)))


def request_xsd(url):
    req = requests.Request("GET", url=url).prepare()
    LOGGER.info("GET {}".format(req.url))
    resp = SESSION.send(req)

    return resp.text


def create_type_map(typ):
    if REPORT_TYPE_MAPPINGS.get(typ):
        return REPORT_TYPE_MAPPINGS.get(typ)
    return {'type' : ['null', 'string']}


def create_field_metadata_for_report(stream, fields, field_name_lookup):
    mdata = {}
    mdata = metadata.write(mdata, (), 'inclusion', 'available')

    for field in fields:
        breadcrumb = ('properties', str(field['xmlAttributeName']))
        if  hasattr(field, "exclusiveFields"):
            mdata = metadata.write(mdata,
                                   breadcrumb,
                                   'fieldExclusions',
                                   [['properties', field_name_lookup[x]]
                                    for x
                                    in field['exclusiveFields']])
        mdata = metadata.write(mdata, breadcrumb, 'behavior', field['fieldBehavior'])
        mdata = metadata.write(mdata, breadcrumb, 'adwords.fieldName', field['fieldName'])

        #inclusion
        if field['xmlAttributeName'] == 'day':
            # Every report with this attribute errors with an empty
            # 400 if it is not included in the field list.
            mdata = metadata.write(mdata, breadcrumb, 'inclusion', 'automatic')
        else:
            mdata = metadata.write(mdata, breadcrumb, 'inclusion', 'available')

    if stream == 'GEO_PERFORMANCE_REPORT':
        # Requests for this report that don't include countryTerritory
        # fail with an empty 400. There's no evidence for this in the
        # docs but it is what it is.
        mdata = metadata.write(mdata, ('properties', 'countryTerritory'), 'inclusion', 'automatic')

    return mdata


def create_schema_for_report(client, stream):
    report_properties = {}
    field_name_lookup = {}
    LOGGER.info('Loading schema for %s', stream)

    fields = client.get_report_definition_service(stream)

    for field in fields:
        field_name_lookup[field['fieldName']] = str(field['xmlAttributeName'])
        report_properties[field['xmlAttributeName']] = {'description': field['displayFieldName']}
        report_properties[field['xmlAttributeName']].update(create_type_map(field['fieldType']))

    if stream == 'AD_PERFORMANCE_REPORT':
        # The data for this field is "image/jpeg" etc. However, the
        # discovered schema from the report description service claims
        # that it should be an integer. This is needed to correct that.
        report_properties['imageMimeType']['type'] = ['null', 'string']

    if stream == 'CALL_METRICS_CALL_DETAILS_REPORT':
        # The data for this field is something like `Jan 1, 2016 1:32:22
        # PM` but the discovered schema is integer.
        report_properties['startTime']['type'] = ['null', 'string']
        report_properties['startTime']['format'] = 'date-time'
        # The data for this field is something like `Jan 1, 2016 1:32:22
        # PM` but the discovered schema is integer
        report_properties['endTime']['type'] = ['null', 'string']
        report_properties['endTime']['format'] = 'date-time'

    mdata = create_field_metadata_for_report(stream, fields, field_name_lookup)

    return ({"type": "object",
             "is_report": 'true',
             "properties": report_properties},
            mdata)


def discover_reports(client):
    reports = VERIFIED_REPORTS + VERIFIED_REPORTS_NO_DATE
    stream_names = client.get_report_types_service(reports)
    streams = []
    LOGGER.info("Starting report discovery")
    for stream_name in stream_names:
        schema, mdata = create_schema_for_report(client, stream_name)
        streams.append({'stream': stream_name,
                        'tap_stream_id': stream_name,
                        'metadata' : metadata.to_list(mdata),
                        'schema': schema})
    
    LOGGER.info("Report discovery complete")
    return {"streams": streams}
