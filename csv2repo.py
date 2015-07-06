"""
Library for representing a set of repository items and collections via a csv file
Deals with multiple item types, assigning items to collections, file uploads and downloads from URLs
Initial implementation is for use with Omeka, but we are planning to use this with other repositories
such as Fedora Commons 4, 
"""

import csv

class Namespace:
    """ Crude way of handling vocabs - ATM there is no checking involved
        TODO: Allow user to load more of these from a file"""
    
    def __init__(self, prefix):
        dc = {"name": "Dublin Core", "URI": "http://purl.org/dc/terms/", "prefix": "dcterms"}
        bibo = {"name": "BIBO", "URI": "http://purl.org/ontology/bibo/", "prefix": "bibo"}
        foaf = {"name": "FOAF", "URI": "http://xmlns.com/foaf/0.1/", "prefix": "foaf"}
        custom = {"name": "custom", "URI": "", "prefix": "custom"}
        frbr = {"name": "FRBR", "URI": "http://purl.org/vocab/frbr/core#", "prefix": "foaf"}
        vocabs = {"dc": dc, "dcterms": dc, "foaf": foaf, "bibo": bibo, "custom": custom, "FRBDR": frbr}
        self.prefix = None
        self.name = None
        self. URI = None
        if prefix in vocabs.keys():
            self.prefix = vocabs[prefix]["prefix"]
            self.name = vocabs[prefix]["name"]
            self.URI = vocabs[prefix]["URI"]
        else:
            self.prefix = prefix
class CSVData:
    def __init__(self, stream):
        self._reader = csv.DictReader(stream)
        self.fieldnames = self._reader.fieldnames
        self.fields = {}
        self.items = []
        self.collections = []
        for name in self.fieldnames:
            self.fields[name] =  Field(name)
            
    def get_items(self):
        """ Get a set of abstract repository items and collections from the rows in the CSV"""
        for row in self._reader:
            item = Item(row)
            if item.is_collection:
                self.collections.append(item)
            else:
                self.items.append(item)

        
class Field:
    TEXT, FILE, URL, RELATION, ITEM_TYPE, IN_COLLECTION = range(6)
    def  __init__(self, field_name):
        self.type = None
        self.namespace = Namespace("")
        self.field_name = None
        self.qualified_name = None
        self.value = None
        self.item_type_field = "dcterms:type" #TODO add a method to change
        self.collection_field = "pcdm:Collection"
        
        if ":" in field_name:
            ns, name = field_name.split(":", 1)
            if ns == "FILE":
                self.type = self.FILE
                self.field_name = name
            elif ns == "URL":
                self.type = self.URL
                self.field_name = name
            elif (ns == "REL" or ns == "RELATION"):
                if  ":" in name:
                    self.type = self.RELATION
                    ns, self.field_name = name.split(":", 1)
                    self.namespace = Namespace(ns)
                    self.qualified_name = ':'.join([self.namespace.prefix, self.field_name])
            else:
                self.namespace = Namespace(ns)
                self.field_name = name
                self.qualified_name = ':'.join([self.namespace.prefix, self.field_name])
                if self.qualified_name == self.item_type_field:
                    self.type = self.ITEM_TYPE
                elif self.qualified_name == self.collection_field:
                    self.type = self.IN_COLLECTION
                else:
                    self.type = self.TEXT


class Item:
    """Repository item to be uploaded"""
    def __init__(self, row = {}):
        self.files = []
        self.URLs = []
        self.relations = []
        self.text_fields = []
        self.is_collection = False
        self.in_collection = None
        self.type = None
        self.dc_id = None
        self.dc_title = None
        for key, value in row.items():
            f = Field(key)
            f.value = value
            if value:
                if f.type == Field.URL:
                    self.URLs.append(f)
                elif f.type == Field.FILE:
                    self.files.append(f)           
                elif f.type == Field.RELATION:
                    self.relations.append(f)
                elif f.type == Field.IN_COLLECTION: #TODO - allow multiples?
                    self.in_collection = value # Should be an id
                elif f.type == Field.TEXT:
                    # Some fields are special, want these to bubble up as
                    # properties of the Item
                    #TODO - maybe make what's special configurable but
                    # these are good defaults
                    if f.qualified_name == "dcterms:title":
                        self.title = value
                    elif f.qualified_name == "dcterms:identifier":
                        self.id = value
                    
                    self.text_fields.append(f)
                elif f.type == Field.ITEM_TYPE:
                    self.type = value
                    if value == "pcdm:Collection":
                        self.is_collection = True
                       
                  
        # etc

            
        
