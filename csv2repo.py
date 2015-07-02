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
    TEXT, FILE, URL, RELATION, IS_COLLECTION, ITEM_TYPE = range(6)
    def  __init__(self, field_name):
        self.type = None
        self.namespace = Namespace("")
        self.field_name = None
        self.qualified_name = None
        self.value = None
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
                self.type = self.TEXT
                self.namespace = Namespace(ns)
                self.field_name = name
                self.qualified_name = ':'.join([self.namespace.prefix, self.field_name])
                
        else:
            if field_name in ["IS_COLLECTION", "IS_SET"]:
                self.type = Field.IS_COLLECTION
            if field_name == "ITEM_TYPE":
                self.type = Field.ITEM_TYPE



class Item:
    """Repository item to be uploaded"""
    def __init__(self, row = {}):
        self.files = []
        self.URLs = []
        self.relations = []
        self.text_fields = []
        self.is_collection = False
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
                    self.files(f)           
                elif f.type == Field.RELATION:
                    self.relations.append(f)
                elif f.type == Field.TEXT:
                    # Some fields are special we want immediate access!
                    #TODO - maybe make what's special configurable
                    if f.qualified_name == "dcterms:title":
                        self.dc_title = value
                    elif f.qualified_name == "dcterms:identifier":
                        self.dc_id = value
                    else:
                        self.text_fields.append(f)
                elif f.type == Field.IS_COLLECTION and value.lower() in ["yes","true","1"]:
                    self.is_collection = True
                elif f.type == Field.ITEM_TYPE:
                    self.item_type = value
            
        # etc

            
        
