import tablib
import yaml
import json
import argparse
from sys import stdin
import sys
import httplib2
import os
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

# TODO: make all these into proper classes so you can find out tha item set an item belongs to etc without having to
# navigate the structure directly (lots of the stuff returned by the API is lists so we want convenient ways to find things in those lists)

def fetch_element_sets():
    response, content = OmekaClient(endpoint, apikey).get('element_sets')
    things = json.loads(content)
    thing_names = {}
    for thing in things:
        thing_names[thing['name']] = thing['id']   
    return things, thing_names

def fetch_elements():
    response, content = OmekaClient(endpoint, apikey).get('elements')
    things = json.loads(content)
    thing_names = {}
    for thing in things:
       if not thing['name'] in thing_names:
           thing_names[thing['name']] = {}
       set_id = thing['element_set']['id']
       thing_names[thing['name']][set_id] =  thing['id']
    return things, thing_names

def fetch_item_types():
    response, content = OmekaClient(endpoint, apikey).get('item_types')
    things = json.loads(content)
    thing_names = {}
    for thing in things:
        thing_names[thing['name']] = thing['id']
        
    return thing_names

#Find the names & ids of collections
def fetch_collections():
    response, content = OmekaClient(endpoint, apikey).get('collections')
    collections_data = json.loads(content)
    collection_names = {}
    collections = {}
    for collection in collections_data:
        collections[collection["id"]] = collection 
        for t in collection['element_texts']:
            if t['element']['name'] == 'Title':
                collection_names[t['text']] =  collection['id']
    return collections, collection_names

#TODO make this a proper grown-up class



#THis has grown into a big mess - returning several things
#TODO: Refactor into an ItemsData class with all the lookups as methods
def find_mapping(data):
    collection_field_mapping = {}
    supplied_id_to_omeka_id = {}
    linked_fields = {}
    supplied_id_to_title = {}
    download_fields  = {}
    #So, seems like I keep adding new mapping tables all of which involve the same code

    for sheet in data:
        if sheet['title'] == 'Omeka Mapping':
            supplied_element_names = sheet['data']
            for row in sheet['data']:
               
                collection = row["Collection"]
                set = row["Omeka Element Set"]
                column = row["Column"]
                omeka_element = row["Omeka Element"]
                linked = row["Linked"]
                if 'Download' in row and row['Download'] <> None and collection <> None:
                    if not collection in download_fields:
                       download_fields[collection] = {}
                    download_fields[collection][column] = True
                if linked <> None and linked <> False:
                    if not collection in linked_fields:
                        linked_fields[collection] = {}
                    linked_fields[collection][column] = True
                if omeka_element <> None and column <> None and collection <> None:
                    if not collection in collection_field_mapping:
                        collection_field_mapping[collection] = {}
                    element_id = element_names[omeka_element]
                    set_id = element_set_names[set]
                    collection_field_mapping[collection][column] = element_id[set_id]
                #Stop 'None'     
                for key, value in row.items():
                    if value == None:
                        row[key] = ""
                        
        elif sheet['title'] == 'ID Mapping':
            for row in sheet['data']:
                supplied_id_to_omeka_id[row[identifier_column]] = row["Omeka ID"]
                title = row["Title"]
                if title <> None:
                    supplied_id_to_title[row[identifier_column]] = title
                

    return collection_field_mapping, supplied_element_names, supplied_id_to_omeka_id, linked_fields, supplied_id_to_title, download_fields
          

element_sets, element_set_names = fetch_element_sets()

#Auto-map to elements from these sets
default_element_set_names = ['Dublin Core','Item Type Metadata']

elements, element_names = fetch_elements()
record_type_names = fetch_item_types()
collections, collection_names = fetch_collections()

#Get the main data
databook = tablib.import_book(inputfile)
data = yaml.load(databook.yaml)
#Get mapping data
mapfile = inputfile.name + ".mapping.xlsx"
if os.path.exists(mapfile):
    previous_output = tablib.import_book(open(mapfile,"rb"))
    previous = yaml.load(previous_output.yaml)
    
    collection_field_mapping, supplied_element_names, id_to_omeka_id, linked_fields, id_to_title, download_fields = find_mapping(previous)
else:
    collection_field_mapping = {}
    id_to_omeka_id = {}
    supplied_element_names = []
    linked_fields = {}
    id_to_title = {}

print download_fields




#TODO refactor so this can replace omekadd.py
count = 0
sheet = 0

id_mapping = []
for d in data:
    collection =  d['title']
    print "Processing collection:", collection
   
    
    if collection <> "Omeka Mapping" and collection in collection_names:
        collection_id = collection_names[collection]
        i = 0
        
       #Work out which fields can be automagically mapped
        if not collection in collection_field_mapping:
            print "No mapping data for this collection. Attempting to make one"
            collection_field_mapping[collection] = {}
            for key in d['data'][0]:
                element_set_name = ""
                element_name = ""
                for set_name in default_element_set_names:
                    set_id = element_set_names[set_name]
                    if key in element_names and set_id in element_names[key]:
                        element_name = key
                        element_set_name = set_name
                        element_set_id = set_id
                        element_id = element_names[key][set_id]
                        collection_field_mapping[collection][element_name]= element_id
                        
                supplied_element_names.append({"Collection": collection,
                                            "Column": key,
                                            "Omeka Element Set": element_set_name,
                                            "Omeka Element": element_name,
                                            "Linked:": "",
                                            "Download": ""})   

      
        
        #TODO - combine with omekadd?
        for item in d['data']:
            stuff_to_upload = False
            element_texts = []
            URLs = []
            for key,value in item.items():
                
                if value <> None:
                    if collection in collection_field_mapping and key in collection_field_mapping[collection]:
                        #print 'Uploading ', key, value
                        element_text = {"html": False, "text": "none"} #, "element_set": {"id": 0}}
                        element_text["element"] = {"id": collection_field_mapping[collection][key] }
                        if collection in download_fields and key in download_fields[collection] and download_fields[collection][key]:
                            print
                            URLs.append(value)

                        if collection in linked_fields and key in linked_fields[collection] and linked_fields[collection][key] and value in id_to_omeka_id:
                            #TODO - deal with muliple values
                            to_title =  id_to_title[value]
                            if to_title == None:
                                to_title =  id_to_omeka_id[value]
                            element_text["text"] = "<a href='/items/show/%s'>%s</a>" % (id_to_omeka_id[value], to_title)
                            element_text["html"] = True
                            print "Uploading HTML", key, value, element_text["text"]
                        else:
                            try: # Have had some encoding problems - not sure if this is still needed
                                element_text["text"] = value
                                
                            except:
                                print "ERROR - failed to add", value
                                pass
                        element_texts.append(element_text)
                       
                    elif key == "Omeka Type" and value in record_type_names:
                        item_type = record_type_names[value]
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
                item_to_upload = {"collection": {"id": collection_id}, "item_type": {"id":item_type}, "featured": args["featured"], "public": args["public"]}
                item_to_upload["element_texts"] = element_texts
                jsonstr = json.dumps(item_to_upload)
                # Find ID
                previous_id = None
                if identifier_column in item and item[identifier_column] in id_to_omeka_id:
                    previous_id = id_to_omeka_id[item[identifier_column]]
                
                if previous_id <> None:
                    print "Re-uploading ", previous_id
                    response, content = OmekaClient(endpoint, apikey).put("items" , previous_id, jsonstr)
               
                else:
                    response, content = OmekaClient(endpoint, apikey).post("items", jsonstr)
              
                #Looks like the ID wasn't actually there, so get it to mint a new one
                if response['status'] == '404':
                     response, content = OmekaClient(endpoint, apikey).post("items", jsonstr)

                new_item = json.loads(content)
                new_item_id = new_item['id']
                for url in URLs:
                    print "Uploading", url
                    uploadjson = {"item": {"id": new_item_id}}
                    uploadmeta = json.dumps(uploadjson)
                    #uploadfile = open(args["upload"], "r").read()
                    http = httplib2.Http()
                    response, content = http.request(url, "GET")
                    print response
                    response, content = OmekaClient(endpoint, apikey).post_file(uploadmeta,"test.kmz", content) 
                    print response
                id_mapping.append({'Omeka ID': new_item_id, identifier_column: item[identifier_column], title_column: item[title_column]})
                print "New ID", new_item_id
               
            i += 1
    
    sheet += 1



#data.append({'title': 'Omeka Mapping', 'data': supplied_element_names})
mapdata = []
##element_sheet = tablib.import_set(supplied_element_names)
id_sheet = tablib.import_set(id_to_omeka_id)

mapdata.append({'title': 'Omeka Mapping', 'data': supplied_element_names})
mapdata.append({'title': 'ID Mapping', 'data': id_mapping})


new_book = tablib.Databook()
new_book.yaml = yaml.dump(mapdata)


with open(mapfile,"wb") as f:
    f.write(new_book.xlsx)
