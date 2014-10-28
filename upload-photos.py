from omekaclient import OmekaClient
from omekautils import get_omeka_config
import argparse
import sys
import os
import subprocess
import json
import re
import os.path
"""Uploads a directory tree of photos to Omeka"""

# Define and parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('dir', default ='.', help='Directory to upload')
parser.add_argument('-k', '--key', default=None, help='Omeka API Key')
parser.add_argument('-u', '--api_url',default=None, help='Omeka API Endpoint URL (hint, ends in /api)')
parser.add_argument('-p', '--public', action='store_true', help='Make items public')
args = vars(parser.parse_args())
extensions =['.jpg','.jpeg','.png']
config = get_omeka_config()
endpoint = args['api_url'] if args['api_url'] <> None else config['api_url']
apikey   = args['key'] if args['api_url'] <> None else config['key']
omeka_client = OmekaClient(endpoint.encode("utf-8"), apikey)
file_stash = re.sub(":|/","_",endpoint) + ".json"

print file_stash;

if os.path.exists(file_stash):
    id_map = json.load(open(file_stash))
else:
    id_map = {}

dir = args['dir']

exif_id = omeka_client.getSetId("EXIF", create=True)
dc_id = omeka_client.getSetId("Dublin Core")
title_id = omeka_client.getElementId(dc_id, "Title")
collection_id = omeka_client.getCollectionId("Photos", create=True)
item_type_id = omeka_client.getItemTypeId("Still Image", create=True)
exif_fields = ["LensID", "FOV", "DOF", "Make", "Model", "FileName", "ExposureTime", "FNumber", "FocusDistance"]
for root, dirs, files in os.walk(dir):
    for file in files:
        ext = os.path.splitext(file)[1]
        if ext.lower() in extensions:
            file_path = os.path.join(root, file)
            pic_data = json.loads(subprocess.check_output(["exiftool", "-json", file_path]))[0]
            #TODO - upload the pics

            #TODO Create new fields for new metadata.
           
            element_texts = []
            
            for field in exif_fields:
                if field in pic_data:
                    element_id = omeka_client.getElementId(exif_id, field, create=True)
                    print field, element_id
                    
                    element_text = {"html": False, "text": pic_data[field]} 
                    element_text["element"] = {"id": element_id}
                    element_texts.append(element_text)
                    

            element_texts.append({"html": False, "text" : file_path, "element" : {"id" : title_id}})
            item_to_upload = {"collection": {"id": collection_id}, "item_type": {"id":item_type_id}, "public": args["public"]}
            item_to_upload["element_texts"] = element_texts
            jsonstr = json.dumps(item_to_upload)
            previous_id =   id_map[file_path] if file_path in id_map else None
                
            if previous_id <> None:
                print "Re-uploading ", previous_id
                response, content = omeka_client.put("items" , previous_id, jsonstr)
                if response['status'] == '404':
                    previous_id = None
                    
            if previous_id == None:
                response, content = omeka_client.post("items", jsonstr)
            print content
            new_item = json.loads(content)
            new_item_id = new_item['id']
            print "Item ID", new_item_id
            id_map[file_path] = new_item_id
            #Save ID map every time - make this an option
            with open(file_stash, 'w') as outfile:
                json.dump(id_map, outfile)
            print omeka_client.post_file_from_filename(file_path, new_item_id )

            
with open(file_stash, 'w') as outfile:
                json.dump(id_map, outfile)
