import httplib2
import urllib
import mimetypes
import json


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
        response, content = self.get('item_types')
        types_data = json.loads(content)
        for type in types_data:
            self.types[type["name"]] = type

    def getItemTypeId(self, name):
        """Find get item_type by ID by name and cache the results:
           WARNING - does not deal with multiple pages of results or collections with the same Title"""
        if name in self.types:   
            return self.types[name]["id"]
        else:
            return None

    def getSetId(self, name):
        """Find an Omeka element_set by name and cache the results"""
        if not name in self.sets:
            response, content = self.get('element_sets', query={"name": name})
            res = json.loads(content)
            if res <> []:
                self.sets[name]  = res[0]
            else:
                return None
        return self.sets[name]["id"]

    def getElementId(self, set_id, name):
        """Find all the elements by element name and cache the results keyed by name / element set id"""
        if not name in self.elements:
            response, content = self.get('elements', query={"name": name})
            res = json.loads(content)
            if res <> []:
                self.elements[name] = {}
                for el in res:
                    self.elements[name][el["element_set"]["id"]] = el

        if name in self.elements and set_id in self.elements[name] and "id" in self.elements[name][set_id]:
            return self.elements[name][set_id]["id"]
        else:
            return None

    def getCollectionId(self, name):
        """Find an Omeka collection by name and cache the results:
           WARNING - does not deal with multiple pages of results or collections with the same Title"""
        if self.collections == {}:
            response, content = self.get('collections')
            collections_data = json.loads(content)
            for collection in collections_data:
                 for t in collection['element_texts']:
                    if t['element']['name'] == 'Title':
                        self.collections[t['text']] =  collection
                 
        if name in self.collections:   
            return self.collections[name]["id"]
        else:
            return None
    
    def get(self, resource, id=None, query={}):
        return self._request("GET", resource, id=id, query=query)
    
    def post(self, resource, data, query={}, headers={}):
        return self._request("POST", resource, data=data, query=query, headers=headers)
    
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
        print url
        resp, content = self._http.request(url, method, body=data, headers=headers)
        return resp, content
