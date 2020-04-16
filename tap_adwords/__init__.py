from .discover import discover_reports
from .client import AdwordsClient
from .sync import sync
import json
import singer
from singer import bookmarks
import sys
from singer import utils

LOGGER = singer.get_logger()
CONFIG = {}
STATE = {}
REQUIRED_CONFIG_KEYS = [
    "start_date",
    "oauth_client_id",
    "oauth_client_secret",
    "user_agent",
    "refresh_token",
    "customer_ids",
    "developer_token",
]


def do_discover(client):
    LOGGER.info('Starting discover')
    catalog = discover_reports(client)
    json.dump(catalog, sys.stdout, indent=2)
    LOGGER.info('Finished discover')


@singer.utils.handle_top_exception(LOGGER)
def main():
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)
    CONFIG.update(args.config)
    STATE.update(args.state)
    customer_ids = CONFIG['customer_ids'].split(",")

    if args.discover:
        client = AdwordsClient(CONFIG['oauth_client_id'],
        CONFIG['oauth_client_secret'],
        CONFIG['developer_token'],
        CONFIG['refresh_token'],
        customer_ids[0])
        do_discover(client)
        LOGGER.info("Discovery complete")
    elif args.properties:
        for customer_id in customer_ids:
            client = AdwordsClient(CONFIG['oauth_client_id'],
            CONFIG['oauth_client_secret'],
            CONFIG['developer_token'],
            CONFIG['refresh_token'],
            customer_id)
            
            LOGGER.info('Syncing customer ID %s ...', customer_id)
            sync(args.properties, client, customer_id, CONFIG, STATE)
            LOGGER.info('Done syncing customer ID %s.', customer_id)
        LOGGER.info("Sync Completed")
    else:
        LOGGER.info("No properties were selected")


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        LOGGER.critical(exc)
        raise exc

