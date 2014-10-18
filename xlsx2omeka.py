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
""" Uploads an entire spreadsheet to an Omeka server """

# Define and parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('inputfile', type=argparse.FileType('rb'),  default=stdin, help='Name of input Excel file')
parser.add_argument('endpoint',  default=stdin, help='Omeka Server')
parser.add_argument('keyfile',nargs="?", help='File name where you have stashed your Omeka key') #  type=argparse.FileType('rb'),
parser.add_argument('-i', '--identifier', action='store_true',default="Identifier", help='Name of an Identifier column in the input spreadsheet. ')
parser.add_argument('-t', '--title', action='store_true',default="Title", help='Name of a Title column in the input spreadsheet. ')
parser.add_argument('-p', '--public', action='store_true', help='Make items public')
parser.add_argument('-f', '--featured', action='store_true', help='Make items featured')
#parser.add_argument('-c', '--collection', type=int, default=None, help='Add item to collection n')
#parser.add_argument('-t', '--type', type=int, default=1, help='Specify item type using Omeka id; default is 1, for "Document"')
#parser.add_argument('-u', '--upload', default=None, help='Name of file to upload and attach to item')
parser.add_argument('-m', '--mdmark', default="markdown>", help='Change string prefix that triggers markdown conversion; default is "markdown>"')
args = vars(parser.parse_args())
#TODO - fix reading API key from file
apikey = args['keyfile']#.read()
endpoint = args['endpoint']
inputfile = args['inputfile']
identifier_column = args['identifier']
title_column = args['title']


#Auto-map to elements from these sets
default_element_set_names = ['Dublin Core','Item Type Metadata']


omeka_client = OmekaClient(endpoint, apikey)

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
        self.supplied_element_names = []
        for sheet in data:
            if sheet['title'] == 'Omeka Mapping':
                self.supplied_element_names = sheet['data']
                for row in sheet['data']:
                    collection = row["Collection"]
                    set = row["Omeka Element Set"]
                    column = row["Column"]
                    omeka_element = row["Omeka Element"]
                    if "Linked" in row:
                        linked = row["Linked"]
                    else:
                        row["Linked"] = ""
                    if "Related" in row:
                        related = row["Related"]
                    else:
                        row["Related"] = ""
            
                    if row['Download'] <> None and collection <> None:
                        if not collection in self.download_fields:
                           self.download_fields[collection] = {}
                        self.download_fields[collection][column] = True
                        
                    if linked <> None and collection <> None:
                        if not collection in self.linked_fields:
                            self.linked_fields[collection] = {}
                        self.linked_fields[collection][column] = True
                        
                    if related <> None and collection <> None:
                        if not collection in self.related_fields:
                            self.related_fields[collection] = {}
                        self.related_fields[collection][column] = related
                        
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
        return collection_name in mapping.download_fields and key in mapping.download_fields[collection_name] and mapping.download_fields[collection_name][key]

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

print mapping



count = 0
sheet = 0

id_mapping = []
for d in data:
    collection_name =  d['title']
    print "Processing potential collection: ", collection_name
    collection_id = omeka_client.getCollectionId(collection_name)
    if collection_name <> "Omeka Mapping" and collection_id <> None:
        print collection_id
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
                                            "Download": ""})   

        print mapping.collection_field_mapping[collection_name]

        #TODO - combine with omekadd?
        for item in d['data']:
            stuff_to_upload = False
            relations = []
            element_texts = []
            URLs = []
            for key,value in item.items():
                (property_id, object_id) = mapping.item_relation(collection_name, key, value)
                
                if value <> None:
                    if mapping.has_map(collection_name, key):
                        #print 'Uploading ', key, value
                        element_text = {"html": False, "text": "none"} #, "element_set": {"id": 0}}
                        element_text["element"] = {"id": mapping.collection_field_mapping[collection_name][key] }
                       
                        if mapping.to_download(collection_name, key):
                            URLs.append(value)
                      
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
                     response, content = omeka_client.post("items", jsonstr)

                new_item = json.loads(content)
                new_item_id = new_item['id']
                for url in URLs:
                    print "Uploading", url
                    filename = urlparse.urlsplit(url).path.split("/")[-1]
                    uploadjson = {"item": {"id": new_item_id}}
                    uploadmeta = json.dumps(uploadjson)
                    
                    http = httplib2.Http()
                    response, content = http.request(url, "GET")
                    print response
                    response, content = omeka_client.post_file(uploadmeta, filename, content) 
                    print response, content
                    
                id_mapping.append({'Omeka ID': new_item_id, identifier_column: item[identifier_column], title_column: item[title_column]})
                print "New ID", new_item_id
                
                for (property_id, object_id) in relations:
                   omeka_client.addItemRelation(new_item_id, property_id, object_id) 

                
                
   



mapdata = []

id_sheet = tablib.import_set(mapping.id_to_omeka_id)

mapdata.append({'title': 'Omeka Mapping', 'data': mapping.supplied_element_names})
mapdata.append({'title': 'ID Mapping', 'data': id_mapping})

new_book = tablib.Databook()
new_book.yaml = yaml.dump(mapdata)

with open(mapfile,"wb") as f:
    f.write(new_book.xlsx)

