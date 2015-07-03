from omekaclient import OmekaClient
from omekautils import get_omeka_config
from omekautils import create_stream_logger
from sys import stdout, stdin
import argparse
from csv2repo import CSVData
import json
import httplib2
import urlparse
import os



""" Uploads an a csv file to an Omeka server """

def download_and_upload_files(item):
    """Handle any dowloads, cache as files locally, then upload all files"""
    http = httplib2.Http()
    download_this = True
    files = []
    for url_field in item.URLs:
        url = url_field.value
        filename = urlparse.urlsplit(url).path.split("/")[-1]
        new_path = os.path.join(data_dir, str(item.id))
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
       
        
    for f in item.files:
        files.append(os.path.join(data_dir, str(original_id), item.value))
    for fyle in files:
        logger.info("Uploading %s", fyle)
        try:
            omeka_client.post_file_from_filename(fyle, item.omeka_id )
            
            logger.info("Uploaded %s", fyle)
        except:
            logger.warning("Some kind of error happened uploading %s - pressing on" % fyle)



logger = create_stream_logger('csv2omeka', stdout)



def omekaize(item): #TODO make this a kind of repository item
    dc_set_id = omeka_client.getSetId("Dublin Core",
                                  create=args['create_item_types'] )
    item_type_id = omeka_client.getItemTypeId(item.type, create=args['create_item_types'])
    item.omeka_data =  {"public": args["public"],
                        "item_type" : {"id": item_type_id }}
    

                       
    if item.in_collection != None:
        collection_id = omeka_client.get_collection_id_by_dc_identifier(item.in_collection,
                                                                        name=title,
                                                                        create=args['create_collections'],
                                                                        public=args["public"])
        if collection_id != None:
            item.omeka_data["collection"] = {"id": collection_id}


    #Lets deal with DC fields to start with worry about other namespaces later...
    element_texts = []
    for f in item.text_fields:
        if f.namespace.prefix == "dcterms":
             element_id = omeka_client.getElementId(dc_set_id ,f.field_name, create=args['create_item_types'] )
             element_text = {"html": False, "text": unicode(f.value)}
             element_text["element"] = {"id": element_id }
             element_texts.append(element_text)
             
    
        item.omeka_data["element_texts"] = element_texts

  


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
    id = collection.id
    title = collection.title
    print id
    if id != None:
        collection_id = omeka_client.get_collection_id_by_dc_identifier(id, name=title, create=args['create_collections'], public=args["public"])
        print "Collection ID", collection_id

uploaded_item_ids = []
    
for item in csv_data.items:
    print item.type
    id = item.id
    if id != None:
        title = item.title
        type = item.type
        previous_id = omeka_client.get_item_id_by_dc_identifier(id)
        omekaize(item)
        jsonstr = json.dumps(item.omeka_data)
        
        # Upload it
        if previous_id != None:
            logger.info("Re-uploading %s", previous_id)
            response, content = omeka_client.put("items" , previous_id, jsonstr)
        else:
            logger.info("Uploading new version")
            response, content = omeka_client.post("items", jsonstr)
        #Looks like the ID wasn't actually there, so get it to mint a new one
        if response['status'] == '404':
            logger.info("retrying")
            response, content = omeka_client.post("items", jsonstr)
            
        # Have new (or old) item now
        new_item = json.loads(content)
        item.omeka_id = new_item['id']
        uploaded_item_ids.append(item.omeka_id)
        
        # Relate to other items
        for r in item.relations:
            property_id = omeka_client.getRelationPropertyIdByLocalPart(r.namespace.prefix, r.field_name)
            object_id = previous_id = omeka_client.get_item_id_by_dc_identifier(r.value)
            if object_id != None:
                logger.info("Relating this item %s to another. Property %s, target %s", item.omeka_id, property_id, object_id)
                omeka_client.addItemRelation(item.omeka_id, property_id, object_id)
                
        download_and_upload_files(item)
