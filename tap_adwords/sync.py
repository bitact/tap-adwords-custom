
import singer
from singer import metrics
from singer import bookmarks
from singer import utils
from singer import metadata
from singer import (transform,
                    UNIX_MILLISECONDS_INTEGER_DATETIME_PARSING,
                    Transformer)
import xml.etree.ElementTree as ET
from .client import AdwordsClient
from dateutil.relativedelta import (relativedelta)
import io
import csv
import zeep
from .reports import VERIFIED_REPORTS_NO_DATE, \
    VERIFIED_REPORTS, REPORTS_WITH_90_DAY_MAX
import copy

LOGGER = singer.get_logger()
REPORT_RUN_DATETIME = utils.strftime(utils.now())


def get_bookmark(state, stream, customer_id, sub_type, default=None):
    if (state is None) or ('bookmarks' not in state):
        return default
    return (
        state
        .get('bookmarks', {})
        .get(stream, {})
        .get(customer_id, {})
        .get(sub_type, default)
    )


def clear_bookmark(state, stream, customer_id, key, default=None):
    state['bookmarks'][stream][customer_id].pop(key, default)
    singer.write_state(state)


def write_bookmark(state, stream, customer_id, sub_type, value):
    if 'bookmarks' not in state:
        state['bookmarks'] = {}
    if stream not in state['bookmarks']:
        state['bookmarks'][stream] = {}
    if customer_id not in state['bookmarks'][stream]:
        state['bookmarks'][stream][customer_id] = {}
    state['bookmarks'][stream][customer_id][sub_type] = value
    LOGGER.info('Write state for Stream: {}, CustomerId: {}, Type: {}, value: {}'.format(
        stream, customer_id, sub_type, value))
    singer.write_state(state)


def get_xml_attribute_headers(stream_schema, description_headers):
    description_to_xml_attribute = {}
    for key, value in stream_schema['properties'].items():
        description_to_xml_attribute[value['description']] = key
    description_to_xml_attribute['Ad policies'] = 'policy'

    xml_attribute_headers = [description_to_xml_attribute[header] for header in description_headers]
    return xml_attribute_headers


def parse_csv_stream(csv_stream):
    # Wrap the binary stream in a utf-8 stream
    tw = io.TextIOWrapper(csv_stream, encoding='utf-8')

    # Read a single line into a String, and parse the headers as a CSV
    headers = csv.reader(io.StringIO(tw.readline()))
    header_array = list(headers)[0]

    # Create another CSV reader for the rest of the data
    csv_reader = csv.reader(tw)
    return header_array, csv_reader


def get_attribution_window_bookmark(customer_id, stream_name, state={}):
    mid_bk_value = get_bookmark(state, stream_name, customer_id, 'last_attribution_window_date')
    return utils.strptime_with_tz(mid_bk_value) if mid_bk_value else None


def apply_conversion_window(start_date, conversion_window_days):
    conversion_window_days = int(conversion_window_days)
    return start_date+relativedelta(days=conversion_window_days)


def get_end_date(end_date):
    if end_date:
        return utils.strptime_with_tz(end_date)

    return utils.now()


def state_key_name(customer_id, report_name):
    return report_name + "_" + customer_id


def dates_sequence_list(start_date, end_date, step=1):
    if step < 1:
        step = 1
        LOGGER.error('setting step to 1...')
    dates = dates_sequence(start_date, end_date)
    dates_all = [dates[i:i + step] for i in range(0, len(dates), step)]
    dates_end = [[x[-0], x[-1]] for x in dates_all]
    return dates_end


def dates_sequence(start_date, end_date):
    seq = []
    delta = end_date - start_date
    for i in range(delta.days + 1):
        seq.append(start_date + relativedelta(days=i))
    return seq


def sync_report_for_day(stream_name, stream_id, stream_schema, client, start, end, field_list, customer_id, start_date, state): # pylint: disable=too-many-locals
    report = {
        'reportName': 'Seems this is required',
        'dateRangeType': 'CUSTOM_DATE',
        'reportType': stream_name,
        'downloadFormat': 'CSV',
        'selector': {
            'fields': field_list,
            }}

    # If start is defined include dateRange filter
    if start:
        report['selector']['dateRange'] = {'min': start.strftime('%Y%m%d'),
                          'max': end.strftime('%Y%m%d')}

    # Fetch the report as a csv string
    with metrics.http_request_timer(stream_name):
        result = client.report_download(report)

    headers, csv_reader = parse_csv_stream(result)
    with metrics.record_counter(stream_name) as counter:
        time_extracted = utils.now()

        with Transformer(singer.UNIX_MILLISECONDS_INTEGER_DATETIME_PARSING) as bumble_bee:
            for row in csv_reader:
                obj = dict(zip(get_xml_attribute_headers(stream_schema, headers), row))
                obj['_sdc_customer_id'] = customer_id
                obj['_sdc_report_datetime'] = REPORT_RUN_DATETIME

                bumble_bee.pre_hook = transform_pre_hook
                obj = bumble_bee.transform(obj, stream_schema)

                singer.write_record(stream_id, obj, time_extracted=time_extracted)
                counter.increment()

        # If start is defined write bookmark
        if start:
            if end > get_start_for_stream(customer_id, stream_id, start_date, state):
                LOGGER.info('updating bookmark: %s > %s', end, get_start_for_stream(customer_id, stream_id, start_date, state))
                write_bookmark(state, stream_id, customer_id, 'date', end.strftime(utils.DATETIME_FMT_SAFE))
            else:
                LOGGER.info('not updating bookmark: %s <= %s', end, get_start_for_stream(customer_id, stream_id, start_date, state))

        LOGGER.info("Done syncing %s records for the %s report for customer_id %s on %s",
                    counter.value, stream_name, customer_id, end)


def transform_pre_hook(data, typ, schema): # pylint: disable=unused-argument
    # A value of two dashes (--) indicates there is no value
    # See https://developers.google.com/adwords/api/docs/guides/reporting#two_dashes
    if isinstance(data, str) and data.strip() == '--':
        data = None

    elif data and typ == "number":
        if data == "> 90%":
            data = "90.01"

        if data == "< 10%":
            data = "9.99"

        if data.endswith(" x"):
            data = data[:-2]

        data = data.replace('%', '')
    elif data and typ == 'object':
        data = zeep.helpers.serialize_object(data, target_cls=dict)

    return data


def should_sync(mdata, field):
    if mdata.get(('properties', field), {}).get('selected'):
        return True
    elif mdata.get(('properties', field), {}).get('inclusion') == 'automatic':
        return True

    return False


def get_fields_to_sync(stream_schema, stream_metadata):
    fields = stream_schema['properties'] # pylint: disable=unsubscriptable-object
    return [field for field in fields if should_sync(stream_metadata, field)]


def check_selected_fields(steam_name, stream_metadata, client, field_list):
    field_set = set(field_list)
    fields = client.get_report_definition_service(steam_name)
    field_map = {f.fieldName: f.xmlAttributeName for f in fields}
    errors = []
    for field in fields:
        if field.fieldName not in field_set:
            continue

        if not hasattr(field, "exclusiveFields"):
            continue

        field_errors = []
        for ex_field in field.exclusiveFields:
            if ex_field in field_set:
                field_errors.append(field_map[ex_field])

        if field_errors:
            errors.append("{} cannot be selected with {}".format(
                field.xmlAttributeName, ",".join(field_errors)))

    if errors:
        advice_message = "You should correct it in the catalog being passed to the tap."

        raise Exception(f"Field selections violate Google's exclusion rules. {advice_message}\n\t{','.join(errors)}")


def write_schema(stream_name, schema, primary_keys, config, bookmark_properties=None):
    schema_copy = copy.deepcopy(schema)
    singer.write_schema(stream_name, schema_copy, primary_keys, bookmark_properties=bookmark_properties)


def get_start_for_stream(customer_id, stream_id, start_date, state={}):
    bk_value = get_bookmark(state, stream_id, customer_id, 'date')   
    LOGGER.info(f'bookmark {stream_id} - {customer_id}  found: {bk_value}')
    bk_start_date = utils.strptime_with_tz(bk_value or start_date)
    return bk_start_date


def add_synthetic_keys_to_stream_schema(stream_schema):
    stream_schema['properties']['_sdc_customer_id'] = {'description': 'Profile ID',
                                                       'type': 'string',
                                                       'field': "customer_id"}
    stream_schema['properties']['_sdc_report_datetime'] = {'description': 'DateTime of Report Run',
                                                           'type': 'string',
                                                           'format' : 'date-time'}
    return stream_schema


def sync_report(catalog, client, customer_id, bookmark_properties, config, state):
    stream_name = catalog['stream']
    stream_id = catalog['tap_stream_id']
    stream_schema = catalog['schema']
    stream_metadata = metadata.to_map(catalog.get('metadata'))
    stream_key_properties = catalog.get('key_properties')
    conversion_window_days = int(stream_metadata.get((), {}).get('conversion_window_days',0))

    stream_schema = add_synthetic_keys_to_stream_schema(stream_schema)

    # Get fields > selected : true, and check if their combination is valid
    xml_attribute_list = get_fields_to_sync(stream_schema, stream_metadata)
    field_list = []
    for field in xml_attribute_list:
        field_list.append(stream_metadata[('properties', field)]['adwords.fieldName'])

    check_selected_fields(stream_name, stream_metadata, client, field_list)
    LOGGER.info('Selected fields: %s', field_list)

    # Make use of primary keys
    primary_keys = stream_key_properties or []
    LOGGER.info("{} primary keys are {}".format(stream_name, primary_keys))

    write_schema(stream_id, stream_schema, primary_keys, config.get('start_date'), bookmark_properties)

    if bookmark_properties:
        # If an attribution window sync is interrupted, start where it left off
        start_date = get_attribution_window_bookmark(customer_id, stream_name, state)

        if start_date is None:
            start_date = apply_conversion_window(get_start_for_stream(customer_id, stream_id, config.get('start_date'), state), conversion_window_days)

        if stream_name in REPORTS_WITH_90_DAY_MAX:
            cutoff = utils.now()+relativedelta(days=-90)
            if start_date < cutoff:
                start_date = cutoff

        dates_list = dates_sequence_list(start_date, get_end_date(config.get('end_date')), int(config.get('step', 1)))

        for dt in dates_list:
            sync_report_for_day(stream_name, stream_id, stream_schema, client, dt[0], dt[1], field_list, customer_id, config.get('start_date'), state)
            write_bookmark(state, stream_id, customer_id, 'last_attribution_window_date',  dt[1].strftime(utils.DATETIME_FMT_SAFE))
        clear_bookmark(state, stream_id, customer_id, 'last_attribution_window_date')
    else:
        sync_report_for_day(stream_name, stream_id, stream_schema, client, None, None, field_list, customer_id, config.get('start_date'), state)

    LOGGER.info("Done syncing the %s report for customer_id %s", stream_id, customer_id)


def sync_stream(catalog, client, customer_id, config, state):
    # This bifurcation is real. Generic Endpoints have entirely different
    # performance characteristics and constraints than the Report
    # Endpoints and thus should be kept separate.
    stream_name = catalog.get('stream')
    if stream_name in VERIFIED_REPORTS_NO_DATE:    
        sync_report(catalog, client, customer_id, None, config, state)
    else:
        sync_report(catalog, client, customer_id, ['day'], config, state)


def sync(properties, client, customer_id, config, state):
    for catalog in properties['streams']:
        stream_name = catalog.get('stream')
        stream_metadata = metadata.to_map(catalog.get('metadata'))

        if stream_metadata.get((), {}).get('selected'):
            LOGGER.info('Syncing stream %s ...', stream_name)
            sync_stream(catalog, client, customer_id, config, state)
        else:
            LOGGER.info('Skipping stream %s.', stream_name)