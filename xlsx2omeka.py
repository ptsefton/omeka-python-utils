import tablib
import yaml
import json
import argparse
from sys import stdin
import sys
from omekaclient import OmekaClient
""" Uploads an entire spreadsheet to an Omeka server """

# Define and parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('inputfile', type=argparse.FileType('rb'),  default=stdin, help='Name of input Excel file')
parser.add_argument('endpoint',  default=stdin, help='Omeka Server')
parser.add_argument('keyfile',nargs="?", help='File name where you have stashed your Omeka key') #  type=argparse.FileType('rb'),
#parser.add_argument('outputfile', type=argparse.FileType('rwb'),  default=stdin, help='Name of input Excel file')
parser.add_argument('-p', '--public', action='store_true', help='Make item public')
parser.add_argument('-f', '--featured', action='store_true', help='Make item featured')
parser.add_argument('-c', '--collection', type=int, default=None, help='Add item to collection n')
parser.add_argument('-t', '--type', type=int, default=1, help='Specify item type using Omeka id; default is 1, for "Document"')
parser.add_argument('-u', '--upload', default=None, help='Name of file to upload and attach to item')
parser.add_argument('-m', '--mdmark', default="markdown>", help='Change string prefix that triggers markdown conversion; default is "markdown>"')
args = vars(parser.parse_args())

apikey = args['keyfile']#.read()
endpoint = args['endpoint']



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

def find_mapping(data):
    collection_field_mapping = {}
    for sheet in data:
        if sheet['title'] == 'Omeka Mapping':
            for row in sheet['data']:
                collection = row["Collection"]
                set = row["Omeka Element Set"]
                column = row["Column"]
                omeka_element = row["Omeka Element"]
                if omeka_element <> None and column <> None and collection <> None:
                    if not collection in collection_field_mapping:
                        collection_field_mapping[collection] = {}
                    element_id = element_names[omeka_element]
                    set_id = element_set_names[set]
                    collection_field_mapping[collection][column] = element_id[set_id]
                for key, value in row.items():
                    if value == None:
                        row[key] = ""
            return collection_field_mapping, sheet['data']
    else:
        return {}, []       

element_sets, element_set_names = fetch_element_sets()

#Auto-map to elements from these sets
default_element_set_names = ['Dublin Core','Item Type Metadata']

elements, element_names = fetch_elements()

record_type_names = fetch_item_types()
collections, collection_names = fetch_collections()
databook = tablib.import_book(args['inputfile'])
data = yaml.load(databook.yaml)

#TODO add a parameter here
try:
    previous_output = tablib.import_book(open("output.xlsx","rb"))
    previous = yaml.load(previous_output.yaml)
    previous_run = True
except:
   previous_run = False


collection_field_mapping = {}
#TODO refactor so this can replace omekadd.py
count = 0
sheet = 0

#Look for mapping data only in original spreadsheet
collection_field_mapping, supplied_element_names = find_mapping(data)



print supplied_element_names
print collection_field_mapping


#TODO read mapping from spreadsheet (last position?)
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
                                            "Omeka Element": element_name})   

        #TODO get mapping table

        
        #TODO - combine with omekadd?
        for item in d['data']:
            stuff_to_upload = False
            element_texts = []
            #First find out what maps to what
            
            for key,value in item.items():
                if value <> None:
                    if collection in collection_field_mapping and key in collection_field_mapping[collection]:
                        print 'Uploading ', key, value
                        element_text = {"html": False, "text": "none"} #, "element_set": {"id": 0}}
                        element_text["element"] = {"id": collection_field_mapping[collection][key] }
                        
                        try:
                            element_text["text"] = str(value)
                        except:
                            print "ERROR - failed to add", value
                            pass
                        element_texts.append(element_text)
                       
                    elif key == "Omeka Type" and value in record_type_names:
                        item_type = record_type_names[value]
                        stuff_to_upload = True
                    else:
                        print 'Warning, not uploaded ', collection, key, value
                else:
                    item[key] = ""
                    
                
            if stuff_to_upload:
                item_to_upload = {"collection": {"id": collection_id}, "item_type": {"id":item_type}, "featured": args["featured"], "public": args["public"]}
                item_to_upload["element_texts"] = element_texts
                jsonstr = json.dumps(item_to_upload)
                
                if previous_run and 'Omeka ID' in previous[sheet]['data'][i] and previous[sheet]['data'][i]['Omeka ID'] <> "":
                    print "Re-uploading (found ID in output)", previous[sheet]['data'][i]['Omeka ID']
                    response, content = OmekaClient(endpoint, apikey).put("items" , str(previous[sheet]['data'][i]['Omeka ID']), jsonstr)
                elif ("Omeka ID" in item) and (item["Omeka ID"] <> ""):
                    print "Re-uploading (found ID in original)", item["Omeka ID"]
                    response, content = OmekaClient(endpoint, apikey).put("items" , str(item["Omeka ID"]), jsonstr)
                else:
                    response, content = OmekaClient(endpoint, apikey).post("items", jsonstr)
               
                print response
               
           
                if response['status'] == '404':
                     response, content = OmekaClient(endpoint, apikey).post("items", jsonstr)
                print response
                new_item = json.loads(content)
                new_item_id = new_item['id']
                item["Omeka ID"] = new_item_id
                print "New ID", new_item_id
               
            i += 1
    
    sheet += 1



#data.append({'title': 'Omeka Mapping', 'data': supplied_element_names})
new_book = tablib.Databook()
new_book.yaml = yaml.dump(data)


with open("output.xlsx","wb") as f:
    f.write(new_book.xlsx)
