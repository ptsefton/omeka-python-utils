from omekaclient import OmekaClient
from omekautils import get_omeka_config
from omekautils import create_stream_logger
from sys import stdout
import argparse
import json

logger = create_stream_logger('deleting', stdout)


config = get_omeka_config()
parser = argparse.ArgumentParser()
parser.add_argument('-k', '--key', default=None, help='Omeka API Key')
parser.add_argument('-u', '--api_url',default=None, help='Omeka API Endpoint URL (hint, ends in /api)')
args = vars(parser.parse_args())

endpoint = args['api_url'] if args['api_url'] <> None else config['api_url']
apikey   = args['key'] if args['api_url'] <> None else config['key']
omeka_client = OmekaClient(endpoint.encode("utf-8"), logger, apikey)
for to_delete in ["items", "collections"]:
    resp, cont = omeka_client.get(to_delete)
    items = json.loads(cont)
    for item in items:
        print "Deleteing ", to_delete, ": ", item['id']
        omeka_client.delete(to_delete, item['id'])
