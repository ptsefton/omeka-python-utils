import tablib
import yaml
import json
import argparse
from sys import stdin
from omekaclient import OmekaClient
""" Uploads an entire spreadsheet to an Omeka server """

# Define and parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('inputfile', type=argparse.FileType('rb'),  default=stdin, help='Name of input Excel file')
parser.add_argument('endpoint',  default=stdin, help='Omeka Server')
parser.add_argument('keyfile',nargs="?", help='File name where you have stashed your Omeka key') #  type=argparse.FileType('rb'), 
parser.add_argument('-p', '--public', action='store_true', help='Make item public')
parser.add_argument('-f', '--featured', action='store_true', help='Make item featured')
parser.add_argument('-c', '--collection', type=int, default=None, help='Add item to collection n')
parser.add_argument('-t', '--type', type=int, default=1, help='Specify item type using Omeka id; default is 1, for "Document"')
parser.add_argument('-u', '--upload', default=None, help='Name of file to upload and attach to item')
parser.add_argument('-m', '--mdmark', default="markdown>", help='Change string prefix that triggers markdown conversion; default is "markdown>"')
args = vars(parser.parse_args())

apikey = args['keyfile']#.read()
endpoint = args['endpoint']

print apikey

def fetch_elements():
    response, content = OmekaClient(endpoint, apikey).get('elements')
    things = json.loads(content)
    thing_names = {}
    for thing in things:
        thing_names[thing['name']] = thing['id']   
    return thing_names
element_names = fetch_elements()
print element_names
#Find the names & ids of collections, not as easy as it sounds
def fetch_collections():
    response, content = OmekaClient(endpoint, apikey).get('collections')
    things = json.loads(content)
    thing_names = {}

    for thing in things:
        for t in thing['element_texts']:
            if t['element']['name'] == 'Title':
                thing_names[t['text']] =  thing['id'] 
                
    return thing_names

collection_names = fetch_collections()



databook = tablib.import_book(args['inputfile'])

data = yaml.load(databook.yaml)

for d in data:
    collection =  d['title']
    print "Collection:", collection
    if collection in collection_names:
        for item in d['data']:
          
            for key,value in item.items():
                if value <> None:
                    if key in element_names:
                        print 'Uploading ', key, value
                    else:
                        print 'warning ', key, value
              

            

