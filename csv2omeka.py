from omekaclient import OmekaClient
from omekautils import get_omeka_config
from omekautils import create_stream_logger
from sys import stdout, stdin
import argparse
from csv2repo import CSVData



""" Uploads an a csv file to an Omeka server """

logger = create_stream_logger('csv2omeka', stdout)

# Define and parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('inputfile', type=argparse.FileType('rb'),  default=stdin, help='Name of input Excel file')
parser.add_argument('-k', '--key', default=None, help='Omeka API Key')
parser.add_argument('-u', '--api_url',default=None, help='Omeka API Endpoint URL (hint, ends in /api)')
parser.add_argument('-i', '--identifier', default="Identifier", help='Name of an Identifier column in the input spreadsheet. ')
parser.add_argument('-d', '--download_cache', default="./data", help='Path to a directory in which to chache dowloads (defaults to ./data)')
parser.add_argument('-p', '--public', action='store_true', help='Make items public')
parser.add_argument('-c', '--create_collections', action='store_true', help='Auto-create missing collections')
parser.add_argument('-e', '--create_elements', action='store_true', help='Auto-create missing element types')
parser.add_argument('-y', '--create_item_types', action='store_true', help='Auto-create missing Item Types')
parser.add_argument('-q', '--quietly', action='store_true', help='Only log errors and warnings not the constant stream of info')
args = vars(parser.parse_args())


config = get_omeka_config()
endpoint = args['api_url'] if args['api_url'] <> None else config['api_url']
apikey   = args['key'] if args['api_url'] <> None else config['key']
omeka_client = OmekaClient(endpoint.encode("utf-8"), logger, apikey)
inputfile = args['inputfile']
identifier_column = args['identifier']
data_dir = args['download_cache']

if args["quietly"]:
    logger.setLevel(30)

csv_data = CSVData(inputfile)
csv_data.get_items()

for collection in csv_data.collections:
    id = collection.dc_id
    title = collection.dc_title
    if id != None:
        collection_id = omeka_client.get_collection_id_by_dc_identifier(id, name=title, create=args['create_collections'], public=args["public"])
        print "Collection ID", collection_id
           
    
for item in []: # csv_data.items:
    print item.type
    
    for f in item.text_fields:
        if f.field_name == "identifier":
            omeka_client.get_item_id_by_dc_identifier(f.value)
        

    for u in item.URLs:
        print f.field_name, f.value

    
