import tablib
import yaml
import json
import argparse
from sys import stdin
import sys
import httplib2
import os
import urlparse
from omekaclient import OmekaClient
from omekautils import get_omeka_config

""" Uploads an entire spreadsheet to an Omeka server """

# Define and parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('inputfile', type=argparse.FileType('rb'),  default=stdin, help='Name of input Excel file')
parser.add_argument('-k', '--key', default=None, help='Omeka API Key')
parser.add_argument('-u', '--api_url',default=None, help='Omeka API Endpoint URL (hint, ends in /api)')
parser.add_argument('-i', '--identifier', action='store_true',default="Identifier", help='Name of an Identifier column in the input spreadsheet. ')
parser.add_argument('-d', '--download_cache', action='store_true',default="./data", help='Path to a directory in which to chache dowloads (defaults to ./data)')
parser.add_argument('-t', '--title', action='store_true',default="Title", help='Name of a Title column in the input spreadsheet. ')
parser.add_argument('-p', '--public', action='store_true', help='Make items public')
parser.add_argument('-f', '--featured', action='store_true', help='Make items featured')
parser.add_argument('-c', '--createcollections', action='store_true', help='Auto-create missing collections')
parser.add_argument('-y', '--createtypes', action='store_true', help='Auto-create missing item types')
args = vars(parser.parse_args())

print args['createcollections']


config = get_omeka_config()
endpoint = args['api_url'] if args['api_url'] <> None else config['api_url']
apikey   = args['key'] if args['api_url'] <> None else config['key']
omeka_client = OmekaClient(endpoint.encode("utf-8"), apikey)
inputfile = args['inputfile']
identifier_column = args['identifier']
title_column = args['title']
data_dir = args['download_cache']


#Auto-map to elements from these sets
default_element_set_names = ['Dublin Core','Item Type Metadata']


omeka_client = OmekaClient(endpoint.encode("utf-8"), apikey)

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
        for sheet in data:
            if sheet['title'] == 'Omeka Mapping':
                self.supplied_element_names = sheet['data']
                for row in sheet['data']:
                    collection = row["Collection"]
                    set = row["Omeka Element Set"]
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
                        self.related_fields[collection][column] = row["Related"]
                        
                    if omeka_element <> None and column <> None and collection <> None:
                        if not collection in self.collection_field_mapping:
                            self.collection_field_mapping[collection] = {}
                       
                        set_id = o_client.getSetId(set)
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
                  
            
    def has_map(self, collection, key):
        return collection in mapping.collection_field_mapping and key in mapping.collection_field_mapping[collection]
    
    def is_linked_field(self, collection_name, key, value):
        return collection_name in self.linked_fields and key in self.linked_fields[collection_name] and self.linked_fields[collection_name][key] == 'yes' and value in self.id_to_omeka_id

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
    
    def add_downloaded_file(self, url, file):
        self.url_to_file['url'] = file
        self.downloads.append({'url': url, 'file': file})

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

count = 0
sheet = 0

id_mapping = []
for d in data:
    collection_name =  d['title']
    print "Processing potential collection: ", collection_name
    collection_id = omeka_client.getCollectionId(collection_name, create=args['createcollections'])
    if collection_id <> None:
       #Work out which fields can be automagically mapped
        if not collection_name in mapping.collection_field_mapping:
            print "No mapping data for this collection. Attempting to make one"
            mapping.collection_field_mapping[collection_name] = {}
            for key in d['data'][0]:
                for set_name in default_element_set_names:
                    set_id = omeka_client.getSetId(set_name)
                    element_id = omeka_client.getElementId(set_id, key)
                    if element_id <> None and not key in mapping.collection_field_mapping[collection_name]:
                        mapping.collection_field_mapping[collection_name][key] = element_id
                        mapping.supplied_element_names.append({"Collection": collection_name,
                                            "Column": key,
                                            "Omeka Element Set": set_name,
                                            "Omeka Element": key,
                                            "Linked": "",
                                            "Related": "",
                                            "Download": "",
                                             "File": ""})   
       
        for item in d['data']:
            stuff_to_upload = False
            relations = []
            element_texts = []
            URLs = []
            files = []
            for key,value in item.items():
                (property_id, object_id) = mapping.item_relation(collection_name, key, value)


                if value <> None:
                    if mapping.has_map(collection_name, key):
                        if  mapping.collection_field_mapping[collection_name][key] <> None:
                            element_text = {"html": False, "text": "none"} #, "element_set": {"id": 0}}
                            element_text["element"] = {"id": mapping.collection_field_mapping[collection_name][key] }
                        else:
                            element_text = {}
                        if mapping.to_download(collection_name, key):
                            print "Need to map"
                            URLs.append(value)
                        if mapping.is_file(collection_name, key):
                            print "Need to map"
                            files.append(value)
                            
                        if mapping.is_linked_field(collection_name, key, value):
                            #TODO - deal with muliple values
                            to_title =  mapping.id_to_title[value]
                            if to_title == None:
                                to_title =  mapping.id_to_omeka_id[value]
                            element_text["text"] = "<a href='/items/show/%s'>%s</a>" % (mapping.id_to_omeka_id[value], to_title)
                            element_text["html"] = True
                            print "Uploading HTML", key, value, element_text["text"]
                        elif property_id <> None:
                            print "Relating this item to another"
    
                            relations.append((property_id, object_id))
                            #TODO check for existing relation
                            
                        else:
                            try: # Have had some encoding problems - not sure if this is still needed
                                element_text["text"] = value
                                
                            except:
                                print "ERROR - failed to add", value

                        element_texts.append(element_text)
                       
                    elif key == "Omeka Type":
                        item_type_id = omeka_client.getItemTypeId(value)
                        if item_type_id <> None:
                            stuff_to_upload = True
                        
                    else:
                        pass #TODO - log failure to upload
                        #print 'Warning, not uploaded ', collection, key, value
                    
                else:
                    item[key] = ""
                    
            if not(identifier_column) in item:
                stuff_to_upload = False
                print "No identifier (%s) in table" % identifier_column
                
            if stuff_to_upload:
                item_to_upload = {"collection": {"id": collection_id}, "item_type": {"id":item_type_id}, "featured": args["featured"], "public": args["public"]}
                item_to_upload["element_texts"] = element_texts
                jsonstr = json.dumps(item_to_upload)
                # Find ID
                previous_id = None
                if identifier_column in item and item[identifier_column] in mapping.id_to_omeka_id:
                    previous_id = mapping.id_to_omeka_id[item[identifier_column]]
                
                if previous_id <> None:
                    print "Re-uploading ", previous_id
                    response, content = omeka_client.put("items" , previous_id, jsonstr)
                
                else:
                    response, content = omeka_client.post("items", jsonstr)
              
                #Looks like the ID wasn't actually there, so get it to mint a new one
                if response['status'] == '404':
                     print "retrying"
                     response, content = omeka_client.post("items", jsonstr)

                new_item = json.loads(content)
                
                try:
                    new_item_id = new_item['id']
                except:
                    print '********* FAILED TO UPLOAD'
                    print item_to_upload, response, content
                    
                for url in URLs:
                    file_path = mapping.downloaded_file(url)
                    print "Found something to download and re-upload", url, file_path
                    
                    if file_path and os.path.exists(file_path):
                        print "Already had that download:", file_path
                        files.append(file_path)
        
                    else:
                        filename = urlparse.urlsplit(url).path.split("/")[-1]
                        new_path = os.path.join(data_dir, str(item[identifier_column]))
                        if not os.path.exists(new_path):
                            os.mkdirs(new_path)
                        file_path = os.path.join(new_path, filename)
                        http = httplib2.Http()
                        response, content = http.request(url, "GET")
                        print response
                        open(file_path,'wb').write(content)
                        mapping.add_downloaded_file(url, file_path)
                        files.append(file_path)

                for file in files:
                    print "Uploading", file
                    print omeka_client.post_file_from_filename(file, new_item_id )

                   
                id_mapping.append({'Omeka ID': new_item_id, identifier_column: item[identifier_column], title_column: item[title_column]})
                print "New ID", new_item_id
                
                for (property_id, object_id) in relations:
                   omeka_client.addItemRelation(new_item_id, property_id, object_id) 

                
                
   



mapdata = []

id_sheet = tablib.import_set(mapping.id_to_omeka_id)

mapdata.append({'title': 'Omeka Mapping', 'data': mapping.supplied_element_names})
mapdata.append({'title': 'ID Mapping', 'data': id_mapping})
mapdata.append({'title': 'Downloads', 'data': mapping.downloads})

new_book = tablib.Databook()
new_book.yaml = yaml.dump(mapdata)

with open(mapfile,"wb") as f:
    f.write(new_book.xlsx)

