import httplib2
import urllib
import mimetypes
import json
import os


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
    
    def __init__(self, endpoint, key=None):
        self._endpoint = endpoint
        
        self._key = key
        self._http = httplib2.Http()
        self.sets = {} #Keep a dict of element sets keyed by name
        self.elements = {} #Dict of elements keyed by name then set-id
        self.collections = {} #Dict of collections keyed by Title

        
        self.types = {} # Dict of item_types
        
    def addItemRelation(self, subject_id, property_id, object_id):
        """Relate two items (for now has a check to make sure they aren't related in the same way already until that can be baked into the API"""
        relation_data = {"subject_item_id": subject_id,
                         "object_item_id":  object_id,
                         "property_id": property_id}
        response, content = self.get('item_relations', query=relation_data)
       
        res = json.loads(content)
        print "relations search:" , res
        if len(res) == 0:
            response, content = self.post('item_relations', json.dumps(relation_data))
            print content;
        else:
            print "Already related"

    def getItemTypeId(self, name, create=False):
        """Find get item_type by ID by name and cache the results:
           WARNING - does not deal with multiple pages of results or collections with the same Title"""
        
        if name in self.types:   
            return self.types[name]["id"]
        else:
            response, content = self.get('item_types', query={"name":name})
            types_data = json.loads(content)
            if types_data <> []:
                self.types[name] = types_data[0]
                return types_data[0]["id"]
            elif create:
                response, content = self.post('item_types', query={"name":name})
                types_data = json.loads(content)
                self.types[name] = types_data[0]
                return types_data[0]["id"]
            else:
                return None
            

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
                if create and res == []: #TODO deal with t
                    response, content = self.post('elements', json.dumps({"name": name, "element_set" : {"id": set_id}}))
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

    def getCollectionId(self, name, create=False):
        """Find an Omeka collection by name and cache the results:
           WARNING - does not deal with multiple pages of results or collections with the same Title"""
        def getTitle(collection):
            for t in collection['element_texts']:
                    if t['element']['name'] == 'Title':
                        self.collections[t['text']] =  collection
                        
        if self.collections == {}:
            response, content = self.get('collections')
            collections_data = json.loads(content)
            for collection in collections_data:
                 getTitle(collection)
                 
        if name in self.collections:   
            return self.collections[name]["id"]
        elif create:
            response, content = self.post('collections', json.dumps({"name": name}))
            collection = json.loads(content)
            return None
    
    def get(self, resource, id=None, query={}):
        return self._request("GET", resource, id=id, query=query)
    
    def post(self, resource, data, query={}, headers={}):
        return self._request("POST", resource, data=data, query=query, headers=headers)
    
    def post_file_from_filename(self, file, id):
        if os.path.exists(file):
            size = os.path.getsize(file)
            filename = os.path.split(file)[-1]

            res, content = self.get("files",query={"item": id})
            attachments = json.loads(content)
            upload_this = True
            
            for attachment in attachments:
                if attachment["size"] == size and attachment["original_filename"] == filename:
                    print "********** There is already a %s byte file named %s, not uploading *******" % (str(size),filename)
                    upload_this = False
            if upload_this:
                uploadjson = {"item": {"id": id}}
                uploadmeta = json.dumps(uploadjson)
                http = httplib2.Http()
                content = open(file, "rb").read()
                return self.post_file(uploadmeta, filename, content) 
        else:
            print "File not found", file
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
        url = self._endpoint + "/" + resource
        if id is not None:
            url += "/" + str(id)
        if self._key is not None:
            query["key"] = self._key
        url += "?" + urllib.urlencode(query)
        resp, content = self._http.request(url, method, body=data, headers=headers)
        return resp, content
