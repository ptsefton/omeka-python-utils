#!/usr/bin/python
import json
import tablib
import yaml
import argparse
from sys import stdin
from sys import stdout
import httplib2
import os
import urlparse
from omekaclient import OmekaClient
from omekautils import get_omeka_config
from omekautils import create_stream_logger



""" Uploads an entire spreadsheet to an Omeka server """

logger = create_stream_logger('xlxx2omeka', stdout)

# Define and parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('inputfile', type=argparse.FileType('rb'),  default=stdin, help='Name of input Excel file')
parser.add_argument('-k', '--key', default=None, help='Omeka API Key')
parser.add_argument('-u', '--api_url',default=None, help='Omeka API Endpoint URL (hint, ends in /api)')
parser.add_argument('-i', '--identifier', default="Identifier", help='Name of an Identifier column in the input spreadsheet. ')
parser.add_argument('-d', '--download_cache', default="./data", help='Path to a directory in which to chache dowloads (defaults to ./data)')
parser.add_argument('-t', '--title', default="Title", help='Name of a Title column in the input spreadsheet. ')
parser.add_argument('-p', '--public', action='store_true', help='Make items public')
parser.add_argument('-f', '--featured', action='store_true', help='Make items featured')
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
title_column = args['title']
data_dir = args['download_cache']
if args["quietly"]:
    logger.setLevel(30)


#Auto-map to elements from these sets
#TODO make the 'bespoke' one configurable
default_element_set_names = ['Dublin Core','Item Type Metadata', 'Bespoke Metadata']


def download_and_upload_files(new_item_id, original_id, URLs, files):
    """Handle any dowloads, cache as files, then upload all files"""
    for url in URLs:
        http = httplib2.Http()
        file_path = mapping.downloaded_file(url)
        download_this = True

        logger.info("Found something to download and re-upload %s", url)

        if file_path == None or file_path == "None": #Previous bug put "None" in spreadsheet
            filename = urlparse.urlsplit(url).path.split("/")[-1]
            new_path = os.path.join(data_dir, str(original_id))
            if not os.path.exists(new_path):
                os.makedirs(new_path)
            file_path = os.path.join(new_path, filename)
        logger.info("Local filename: %s", file_path)

        #Check if we have one the same size already
        if os.path.exists(file_path):
            response, content = http.request(url, "HEAD")
            download_size = int(response['content-length']) if 'content-length' in response else -1
            file_size = os.path.getsize(file_path)
            if download_size == file_size:
                logger.info("Already have a download of the same size: %d", file_size)
                download_this = False

        if download_this:
            try:
                response, content = http.request(url, "GET")
                open(file_path,'wb').write(content)
                logger.info(response)
            except:
                logger.warning("Some kind of download error happened fetching %s - pressing on" % url)

        files.append(file_path)
        mapping.add_downloaded_file(url, file_path)

    for fyle in files:
        logger.info("Uploading %s", fyle)
        try:
            omeka_client.post_file_from_filename(fyle, new_item_id )
            
            logger.info("Uploaded %s", fyle)
        except:
            logger.warning("Some kind of error happened uploading %s - pressing on" % fyle)

def upload(previous_id, original_id, jsonstr, title, URLs, files, iterations):
    #TODO - get rid of the global mapping variable 
    if iterations > 1:
        previous_id = None
        
    for iteration in range(0, iterations):
        if previous_id <> None:
            logger.info("Re-uploading %s", previous_id)
            response, content = omeka_client.put("items" , previous_id, jsonstr)
        else:
            logger.info("Uploading new version, iteration %d", iteration)
            response, content = omeka_client.post("items", jsonstr)

        #Looks like the ID wasn't actually there, so get it to mint a new one
        if response['status'] == '404':
            logger.info("retrying")
            response, content = omeka_client.post("items", jsonstr)

        new_item = json.loads(content)

        try:
            new_item_id = new_item['id']
            if iterations == 1:
                id_mapping.append({'Omeka ID': new_item_id, identifier_column: original_id, "Title": title})
            
            logger.info("New ID %s", new_item_id)
            
            for (property_id, object_id) in relations:
                omeka_client.addItemRelation(new_item_id, property_id, object_id)

            download_and_upload_files(new_item_id, original_id, URLs, files)
        except:
            logger.error('********* FAILED TO UPLOAD: \n%s\n%s\n%s', item_to_upload, response, content)




       

class XlsxMapping:
    """Keep track of all the mapping stuff from spreadsheet to Omeka"""
    #Still needs work on methods rather than direct access to data structures
    
    def __init__(self, o_client, data = []):
        self.collection_field_mapping = {}
        self.id_to_omeka_id = {}
        self.linked_fields = {}
        self.related_fields = {}
        self.id_to_title = {}
        self.download_fields  = {}
        self.url_to_file = {}
        self.downloads = []
        self.supplied_element_names = []
        self.file_fields = {} 
        self.multiple_uploads = {} #Collection: Iterations
        self.multiples = [{'Collection': '', 'Iterations': 0}]
        for sheet in data:
            if sheet['title'] == 'Omeka Mapping':
                self.supplied_element_names = sheet['data']
                for row in sheet['data']:
                    collection = row["Collection"]
                    element_set = row["Omeka Element Set"]
                    column = row["Column"]
                    omeka_element = row["Omeka Element"]
                    if not "Linked" in row:
                        row["Linked"] = None
                    if  not "Related" in row:
                        row["Related"] = None
                    if not "File" in row:
                        row["File"] = None
                       
            
                    if row['Download'] <> None and collection <> None:
                        if not collection in self.download_fields:
                            self.download_fields[collection] = {}
                        self.download_fields[collection][column] = True
 

                    if row['File'] <> None and collection <> None:
                        if not collection in self.file_fields:
                            self.file_fields[collection] = {}
                        self.file_fields[collection][column] = True
                        
                    if row["Linked"] <> None and collection <> None:
                        if not collection in self.linked_fields:
                            self.linked_fields[collection] = {}
                        self.linked_fields[collection][column] = True
                        
                    if row["Related"] <> None and collection <> None:
                        if not collection in self.related_fields:
                            self.related_fields[collection] = {}
                        relation = row["Related"]
                        relation_id = None
                        if ":" in str(relation):
                            prefix, label = relation.split(":")
                            relation_id = omeka_client.getRelationPropertyId(prefix,label)
                            self.related_fields[collection][column] = relation_id
                        
                    if omeka_element <> None and column <> None and collection <> None:
                        if not collection in self.collection_field_mapping:
                            self.collection_field_mapping[collection] = {}
                       
                        set_id = o_client.getSetId(element_set)
                        element_id = o_client.getElementId(set_id,omeka_element)
    
                        self.collection_field_mapping[collection][column] = element_id
                    #Stop 'None' values appearing in the spreadsheet
                    # And inexplicable 'null' columns  
                    for key, value in row.items():
                        if key == None:
                            del row[key]
                        elif value == None:
                            row[key] = ""
                        
            elif sheet['title'] == 'ID Mapping':
                for row in sheet['data']:
                    self.id_to_omeka_id[row[identifier_column]] = row["Omeka ID"]
                    title = row["Title"]
                    if title <> None:
                        self.id_to_title[row[identifier_column]] = title

            #TODO - new sheet, download cache
            elif sheet['title'] == 'Downloads':
                for row in sheet['data']:
                    self.url_to_file[row['url']] = row['file']

            elif sheet['title'] == 'Multiple Uploads':
                self.multiples = sheet['data']
                for row in sheet['data']:
                    self.multiple_uploads[row['Collection']] = row['Iterations']
    
    def has_map(self, collection, key):
        return collection in mapping.collection_field_mapping and key in mapping.collection_field_mapping[collection]
    
    def is_linked_field(self, collection_name, key, value):
        return collection_name in self.linked_fields and key in self.linked_fields[collection_name] and self.linked_fields[collection_name][key]  and value in self.id_to_omeka_id

    def item_relation(self, collection_name, key, value):
        if collection_name in self.related_fields and key in self.related_fields[collection_name] and self.related_fields[collection_name][key] and value in self.id_to_omeka_id:
            return (self.related_fields[collection_name][key], self.id_to_omeka_id[value])
        else:
            return (None, None)
    
    def to_download(self, collection_name, key):
        return collection_name in self.download_fields and key in self.download_fields[collection_name] and self.download_fields[collection_name][key]

    def is_file(self, collection_name, key):
        return collection_name in self.file_fields and key in self.file_fields[collection_name] and self.file_fields[collection_name][key]

    def downloaded_file(self, url):
        return self.url_to_file[url] if url in self.url_to_file else None
    
    def add_downloaded_file(self, url, filename):
        self.url_to_file['url'] = filename
        self.downloads.append({'url': url, 'file': filename})

    def upload_collection_multiple_times(self, collection_name):
        return self.multiple_uploads[collection_name] if collection_name in  self.multiple_uploads else 1

#Get the main data
databook = tablib.import_book(inputfile)
data = yaml.load(databook.yaml)
#Get mapping data
mapfile = inputfile.name + ".mapping.xlsx"
if os.path.exists(mapfile):
    previous_output = tablib.import_book(open(mapfile,"rb"))
    previous = yaml.load(previous_output.yaml)
else:
    previous = []    

mapping = XlsxMapping(omeka_client, previous)


id_mapping = []
for d in data:
    collection_name =  d['title']
    logger.info("Processing potential collection: %s", collection_name)
    iterations = mapping.upload_collection_multiple_times(collection_name)
    collection_id = omeka_client.getCollectionId(collection_name, create=args['create_collections'], public=args["public"])
    if collection_id <> None:
        #Work out which fields can be automagically mapped
        if not collection_name in mapping.collection_field_mapping:
            logger.info("No mapping data for this collection. Attempting to make one")
            mapping.collection_field_mapping[collection_name] = {}
            
      
        
        def map_element(key, element_id, set_name):
            mapping.collection_field_mapping[collection_name][key] = element_id
            mapping.supplied_element_names.append({"Collection": collection_name,
                            "Column": key,
                            "Omeka Element Set": set_name,
                            "Omeka Element": key,
                            "Linked": "",
                            "Related": "",
                            "Download": "",
                            "File": ""})
            
        for key in d['data'][0]:

            for set_name in default_element_set_names:
                set_id = omeka_client.getSetId(set_name)
                element_id = omeka_client.getElementId(set_id, key)
                if element_id <> None and not key in mapping.collection_field_mapping[collection_name]:
                    map_element(key, element_id, set_name)
                    
            if args['create_elements'] and key <> "Omeka Type" and not key in mapping.collection_field_mapping[collection_name]:
                set_name = 'Bespoke Metadata'
                set_id = omeka_client.getSetId(set_name, create=True)
                element_id = omeka_client.getElementId(set_id, key, create=args['create_elements'])
                map_element(key, element_id, set_name)
    
        for item in d['data']:
            stuff_to_upload = False
            relations = []
            element_texts = []
            URLs = []
            files = []
            for key,value in item.items():
                (property_id, object_id) = mapping.item_relation(collection_name, key, value)
                if value <> None:
                    if key == "Omeka Type":
                        item_type_id = omeka_client.getItemTypeId(value, create=args['create_item_types'])
                        if item_type_id <> None:
                            stuff_to_upload = True
                    else:
                        if mapping.has_map(collection_name, key):
                            if  mapping.collection_field_mapping[collection_name][key] <> None:
                                element_text = {"html": False, "text": "none"} #, "element_set": {"id": 0}}
                                element_text["element"] = {"id": mapping.collection_field_mapping[collection_name][key] }
                            else:
                                element_text = {}
                            
                            if mapping.is_linked_field(collection_name, key, value):
                                #TODO - deal with muliple values
                                to_title =  mapping.id_to_title[value]
                                if to_title == None:
                                    to_title =  mapping.id_to_omeka_id[value]
                                element_text["text"] = "<a href='/items/show/%s'>%s</a>" % (mapping.id_to_omeka_id[value], to_title)
                                element_text["html"] = True
                                logger.info("Uploading HTML %s, %s, %s", key, value, element_text["text"])
                            elif property_id <> None:
                                logger.info("Relating this item to another")
                                relations.append((property_id, object_id))
                            else:
                                try: # Have had some encoding problems - not sure if this is still needed
                                    element_text["text"] = unicode(value)

                                except:
                                    logger.error("failed to add this string \n********\n %s \n*********\n" % value)

                            element_texts.append(element_text)
               
                else:
                    item[key] = ""

                if mapping.to_download(collection_name, key):
                    URLs.append(value)
                if mapping.is_file(collection_name, key) and value:
                    filename = os.path.join(data_dir,value)
                    if os.path.exists(filename):
                        files.append(filename)    
                    else:
                        logger.warning("skipping non existent file %s" % filename)
            if not(identifier_column) in item:
                stuff_to_upload = False
                logger.info("No identifier (%s) in table", identifier_column)
                
            if stuff_to_upload:
                item_to_upload = {"collection": {"id": collection_id}, "item_type": {"id":item_type_id}, "featured": args["featured"], "public": args["public"]}
                item_to_upload["element_texts"] = element_texts
                jsonstr = json.dumps(item_to_upload)
                previous_id = None
                original_id = item[identifier_column]
                title = item[title_column] if title_column in item else "Untitled"
                if identifier_column in item and original_id in mapping.id_to_omeka_id:
                    previous_id = mapping.id_to_omeka_id[original_id]

                
                upload(previous_id, original_id, jsonstr, title, URLs, files, iterations)
                

                
                
   



mapdata = []

id_sheet = tablib.import_set(mapping.id_to_omeka_id)

mapdata.append({'title': 'Omeka Mapping', 'data': mapping.supplied_element_names})
mapdata.append({'title': 'ID Mapping', 'data': id_mapping})
mapdata.append({'title': 'Downloads', 'data': mapping.downloads})
mapdata.append({'title': 'Multiple Uploads', 'data': mapping.multiples})
               
new_book = tablib.Databook()
new_book.yaml = yaml.dump(mapdata)

with open(mapfile,"wb") as f:
    f.write(new_book.xlsx)
logger.info("Finished")
