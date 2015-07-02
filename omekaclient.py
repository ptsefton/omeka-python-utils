"""
Adapted from https://github.com/wcaleb/omekadd

A basic Python API for Omeka, extended to deal with extra functionalist added by the Ozmeka project
such as an API for item relations

https://github.com/ozmeka

"""


import httplib2
import urllib
import mimetypes
import json
import os
import re

import sys  

reload(sys)  
sys.setdefaultencoding('utf8')


from omekautils import create_null_logger


class OmekaItem:
    def __init__(self):
        self.data = {}

class OmekaElement:
    def __init__(self):
        self.data = {}

    
class OmekaCollection:
    def __init__(self):
        self.data = {}

        
class OmekaClient:
    
    def __init__(self, endpoint, logger=None, key=None):
        self._endpoint = endpoint
        
        self._key = key
        self._http = httplib2.Http()
        self.sets = {} #Keep a dict of element sets keyed by name
        self.elements = {} #Dict of elements keyed by name then set-id
        self.collections = {} #Dict of collections keyed by Title
        self.collections_by_dc_identifier = {} #Dictt of collections keyed by dc:Identifier
        self.vocabs = {} #Dict of vocabularies keyed by namespace prefix
        self.relation_properties = {} # Dict of Item Relations Properties keyed by vocab id, then name
        self.dublinCoreID = self.getSetId("Dublin Core")
        self.omekaMetadataID = self.getSetId("Omeka Metadata")
        if logger is None:
            self.logger = create_null_logger("OmekaClient")
        else:
            self.logger = logger
        
        self.types = {} # Dict of item_types

    def checkResult(self, res):
        if res['status'] == '201':
            return True
        else:
            logger.error(res)
            return False 
        
    def addItemRelation(self, subject_id, property_id, object_id):
        """Relate two items (for now has a check to make sure they aren't related in the same way already until that can be baked into the API"""
        relation_data = {"subject_item_id": subject_id,
                         "object_item_id":  object_id,
                         "property_id": property_id}
        response, content = self.get('item_relations', query=relation_data)
       
        res = json.loads(content)
        if len(res) == 0:
            response, content = self.post('item_relations', json.dumps(relation_data))
            self.logger.info("Response = %s, content = %s", response, content);
        else:
            self.logger.info("Already related")

    def getItemTypeId(self, name, create=False):
        """Find item_type ID by name and cache the results:"""
        if name in self.types:   
            return self.types[name]["id"]
        else:
            response, content = self.get('item_types', query={"name":name})
            types_data = json.loads(content)
            if types_data <> []:
                self.types[name] = types_data[0]
                return types_data[0]["id"]
            elif create:
                self.logger.info("Item type %s not found, attempting to make one" % name)
                response, content = self.post('item_types',  json.dumps({"name": name}))
                types_data = json.loads(content)
                self.types[name] = types_data
               
                return types_data["id"]
            else:
                return None
            
    def getVocabularyId(self, name):
        """Find an the ID of an ItemRelations vocabulary using its prefix (eg dcterms)"""
        if not name in self.vocabs:
            response, content = self.get('item_relations_vocabularies', query={"namespace_prefix": name})
            res = json.loads(content)
            if res <> []:
                self.vocabs[name]  = res[0]
            else:
                return None
        return self.vocabs[name]["id"]

    def getRelationPropertyId(self, prefix, label):
        """Find an the ID of a vocabulary using its prefix (eg dcterms)"""
        vocab_id = self.getVocabularyId(prefix)
        if vocab_id <> None:
            if not vocab_id in self.relation_properties:
                self.relation_properties[vocab_id] = {}
            if not label in  self.relation_properties[vocab_id]:
                response, content = self.get('item_relations_properties', query={"label": label, "vocabulary_id": vocab_id})
                res = json.loads(content)
                if res <> []:
                    self.relation_properties[vocab_id][label]  = res[0]
                else:
                    return None
            return  self.relation_properties[vocab_id][label]["id"]       

    def getSetId(self, name, create=False):
        """Find an Omeka element_set by name and cache the results"""
        if not name in self.sets:
            response, content = self.get('element_sets', query={"name": name})
            res = json.loads(content)
            if res <> [] or create:
                if create and res == []:
                    response, content = self.post('element_sets', json.dumps({"name": name}))
                    set_data = json.loads(content)
                else:
                    set_data = res[0]
                self.sets[name]  = set_data
            else:
                return None
        return self.sets[name]["id"]

    def getElementId(self, set_id, name, create=False):
        """Find all the elements by element name and cache the results keyed by name / element set id"""
        if not name in self.elements:
            response, content = self.get('elements', query={"name": name, "element_set": set_id})
            res = json.loads(content)
            if res <> [] or create:
                if create and res == []: #TODO deal with 
                    response, content = self.post('elements', json.dumps({"name": name, "element_set" : {"id": set_id}}))
                    self.logger.info("Trying to make an element %s %s", response, content)
                    el_data = json.loads(content)
                else:
                    el_data = res[0]
                if not name in self.elements:
                    self.elements[name] = {}
                self.elements[name][set_id] = el_data

        if name in self.elements and set_id in self.elements[name] and "id" in self.elements[name][set_id]:
            return self.elements[name][set_id]["id"]
        else:
            return None

    def getCollectionId(self, name, create=False, public=False):
        """Find an Omeka collection by name and cache the results. Does not deal with collections with the same title"""
        def getTitle(collection):
            for t in collection['element_texts']:
                    if t['element']['name'] == 'Title':
                        self.collections[t['text']] =  collection
                        
        if self.collections == {}:
            response, content = self.get('collections')
            collections_data = json.loads(content)
            for collection in collections_data:
                getTitle(collection)
                 
        
        if not name in self.collections and create:
            title_id = self.getElementId(self.dublinCoreID, "Title")
            element_text = {"html": False, "text": name} 
            element_text["element"] = {"id": title_id }
            
            response, content = self.post('collections', json.dumps({"element_texts": [element_text], "public" : public}))
            collection = json.loads(content)
            getTitle(collection)
            
        
        return self.collections[name]["id"] if name in self.collections else None

    def get_collection_id_by_dc_identifier(self, dcid, name=None, create=False, public=False):
        """Find an Omeka collection by name and cache the results. Does not deal with collections with the same title"""
        element_id = self.getElementId(self.dublinCoreID, "Identifier")
        title_id = self.getElementId(self.dublinCoreID, "Title")  
        def get_identifier(collection):
            for t in collection['element_texts']:
                    if t['element']['id'] == element_id:
                        self.collections_by_dc_identifier[t['text']] =  collection
                        
        if self.collections_by_dc_identifier == {}:
            response, content = self.get('collections')
            collections_data = json.loads(content)
            for collection in collections_data:
                get_identifier(collection)
                 
        if not dcid in self.collections_by_dc_identifier and create:
            if name == None:
                name = dcid
            element_text1 = {"html": False, "text": name} 
            element_text1["element"] = {"id": title_id }

            element_text2 = {"html": False, "text": dcid} 
            element_text2["element"] = {"id": element_id}
            
            response, content = self.post('collections', json.dumps({"element_texts": [element_text1, element_text2], "public" : public}))
            collection = json.loads(content)
            get_identifier(collection)
        
        return self.collections_by_dc_identifier[dcid]["id"] if dcid in self.collections_by_dc_identifier else None
    
    def get(self, resource, id=None, query={}):
        return self._request("GET", resource, id=id, query=query)
        
    
    def post(self, resource, data, query={}, headers={}):
        return self._request("POST", resource, data=data, query=query, headers=headers)

    def get_file(self, url):
        resp, content = self._http.request(url, 'GET')
        return resp, content

    def get_files_for_item(self, id):
        res, content = self.get("files",query={"item": id})
        try:
            attachments = json.loads(content)
            return attachments
        except:
            self.logger.error("Unable to parse file-list %s", content)
            return []
        
    def get_item_id_by_dc_identifier(self, id):
        element_id = self.getElementId(self.dublinCoreID, "Identifier")
        url = self._endpoint.replace("/api","/items/browse?search=&advanced[0][element_id]=%s&advanced[0][type]=is+exactly&advanced[0][terms]=%s&range=&collection=&type=&user=&tags=&public=&featured=&submit_search=Search+for+items&output=json" % (element_id, id))
        resp, content = self._http.request(url, "GET")
        
        
#http://192.168.99.100/omeka-2.2.2/items/browse?search=&advanced[0][element_id]=43&advanced[0][type]=is+exactly&advanced[0][terms]=cp6-ds-1&submit_search=Search+for+items&output=json


    def post_file_from_filename(self, file, id):
        if os.path.exists(file):
            size = os.path.getsize(file)
            filename = os.path.split(file)[-1]
            attachments = self.get_files_for_item(id)
            upload_this = True
            filename = filename.encode("utf-8")
            for attachment in attachments:
                if attachment["size"] == size and attachment["original_filename"] == filename:
                    self.logger.info("********** There is already a %d byte file named %s, not uploading *******", size,filename)
                    upload_this = False
            if upload_this:
                uploadjson = {"item": {"id": id}}
                uploadmeta = json.dumps(uploadjson)
                
                with open(file, 'rb' ) as f:
                    content = f.read()
                    f.close()
             
                res, content = self.post_file(uploadmeta, filename, content)
                return self.checkResult(res)
                
        else:
            self.error("File %s not found", file)
            return False
        return True
            
    def put(self, resource, id, data, query={}):
        return self._request("PUT", resource, id, data=data, query=query)
    
    def delete(self, resource, id, query={}):
        return self._request("DELETE", resource, id, query=query)
    
    def post_file(self, data, filename, contents):
        
        """ data is JSON metadata, filename is a string, contents is file contents """
        BOUNDARY = '----------E19zNvXGzXaLvS5C'
        CRLF = '\r\n'
        headers = {'Content-Type': 'multipart/form-data; boundary=' + BOUNDARY}
        L = []
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="data"')
        L.append('')
        L.append(data)
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="file"; filename="%s"' % filename)
        L.append('Content-Type: %s' % self.get_content_type(filename))
        L.append('')
        L.append(contents)
        L.append('--' + BOUNDARY)
        body = CRLF.join(L)
        headers['content-length'] = str(len(body))
        query = {}
        return self.post("files", body, query, headers)
      
    def get_content_type(self, filename):
        """ use mimetypes to detect type of file to be uploaded """
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    def _request(self, method, resource, id=None, data=None, query=None, headers=None):
        if resource == "search":
            url = self._endpoint.replace("api","items/browse")
        else:
            url = self._endpoint + "/" + resource
        if id is not None:
            url += "/" + str(id)
        if self._key is not None:
            query["key"] = self._key
        url += "?" + urllib.urlencode(query)

        resp, content = self._http.request(url, method, body=data, headers=headers)
        
        links = resp['link'] if 'link' in resp else ""
        for link in links.split(", "):
            l = link.split("; ")
            if l[-1] == 'rel="next"':
                pages = re.findall(r'\Wpage=(\d+)', l[0])
                per_pages = re.findall(r'\Wper_page=(\d+)', l[0])
                page = int(pages[0]) if len(pages) > 0 else None
                per_page = int(per_pages[0]) if len(per_pages) > 0 else None

                if page and per_page:
                    query['page'] = page
                    query['per_page'] = per_page
                    resp, cont = self._request(method, resource, id, data, query, headers)
                    content = json.dumps(json.loads(content) + json.loads(cont))
        #Returns strings - this is not ideal but to fix would require a breaking change
        return resp, content
