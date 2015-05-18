from omekaclient import OmekaClient
from omekautils import get_omeka_config
from omekautils import create_stream_logger
from sys import stdout
import argparse
import json
import os
import tempfile


#Hacky stuff as this is a one off
import sys
sys.path
sys.path.append('../jischtml5/tools/commandline')
import word2html


logger = create_stream_logger('converting', stdout)


config = get_omeka_config()
parser = argparse.ArgumentParser()
parser.add_argument('-k', '--key', default=None, help='Omeka API Key')
parser.add_argument('-u', '--api_url',default=None, help='Omeka API Endpoint URL (hint, ends in /api)')
args = vars(parser.parse_args())

endpoint = args['api_url'] if args['api_url'] <> None else config['api_url']
apikey   = args['key'] if args['api_url'] <> None else config['key']
omeka_client = OmekaClient(endpoint.encode("utf-8"), logger, apikey)

resp, cont = omeka_client.get("items")
items = json.loads(cont)
temp_dir = tempfile.mkdtemp()
os.chmod(temp_dir, 0o2770) #Sets group permissions and "sticky bit"
for item in items:
    logger.info('Looking at %s', item['id'])
    for f in omeka_client.get_files_for_item(item['id']):
        fname = f['original_filename']
        name, ext = os.path.splitext(fname)
        if ext.lower() in [".docx", ".doc"]:
            print f['url']
            res, data = omeka_client.get_file(f['file_urls']['original'])
            download_file = os.path.join(temp_dir, fname)
            out = open(download_file, 'wb')
            out.write(data)
            out.close()
            
            out_dir, x = os.path.split(download_file)
            html_file =  os.path.join(temp_dir, name + ".html")
            word2html.convert(download_file, html_file , True, True, False)
            print omeka_client.post_file_from_filename(
                html_file, item['id'])
            
        
