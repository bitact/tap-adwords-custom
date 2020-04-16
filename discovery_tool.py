import json
import copy
import argparse

def create_catalog(data, streams_to_include):
    streams = []
    for item in data["streams"]:
        if item['stream'] in streams_to_include.keys():
            stream_to_keep = copy.deepcopy(item)
            
            stream_to_keep['tap_stream_id'] = streams_to_include[item['stream']].get("name")
            stream_to_keep['metadata'] = []
            stream_to_keep['schema']['properties'] = {}

            primary_keys_to_inlcude = streams_to_include[item['stream']].get("primary_keys")
            if primary_keys_to_inlcude:
                stream_to_keep['key_properties'] = primary_keys_to_inlcude

            fields_to_include = streams_to_include[item['stream']].get("fields")
            conversion_window_days = streams_to_include[item['stream']].get("conversion_window_days")

            for m in item['metadata']:
                if not m['breadcrumb']:
                    m['metadata'].update({"selected":True})
                    m['metadata'].update({"conversion_window_days":conversion_window_days})
                    stream_to_keep['metadata'].append(m)
                else:
                    if m['breadcrumb'][1] in fields_to_include:
                        if m['metadata']["inclusion"] == 'available':
                            m['metadata'].update({"selected":True})

                        stream_to_keep['metadata'].append(m)

            for key in item['schema']['properties']:
                if key in fields_to_include:
                    stream_to_keep['schema']['properties'].update({key:item['schema']['properties'][key]})
                    
            streams.append(stream_to_keep)

    return {'streams' : streams}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-r', '--report',
        help='Report file',
        required=True)

    parser.add_argument(
        '-i', '--input',
        help='Input file',
        required=True)

    parser.add_argument(
        '-o', '--output',
        help='Output file',
        required=True)

    args = parser.parse_args()

    input_file = args.input
    output_file = args.output
    report_file = args.report

    with open(report_file, 'r', encoding='utf8') as f:
        streams_to_include = json.load(f)
    
    with open(input_file, 'r', encoding='utf8') as k:
        data = json.load(k)

    rs = create_catalog(data, streams_to_include)    

    with open(output_file, 'w', encoding='utf8') as n:
        json.dump(rs, n, indent=3)
