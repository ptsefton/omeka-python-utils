import unittest
from csv2repo import CSVData, Field, Item, Namespace

class TestNS(unittest.TestCase):
    def test_ns(self):
        ns = Namespace("something")
        self.assertEqual(ns.name, None)
        ns = Namespace("foaf")
        self.assertEqual(ns.name, "FOAF")
        self.assertEqual(ns.URI, "http://xmlns.com/foaf/0.1/")
        self.assertEqual(Namespace("dc").URI, Namespace("dcterms").URI)

   
        
class TestCSVData(unittest.TestCase):
     def test_item_types(self):
        c = CSVData(['dcterms:title,dcterms:identifier'])
        self.assertEqual(c.fieldnames, ['dcterms:title','dcterms:identifier'])
        f = c.fields["dcterms:title"]
        self.assertEqual(f.type, Field.TEXT)
        self.assertEqual(f.namespace.prefix, "dcterms")
        self.assertEqual(f.field_name, "title")

        data = ['dcterms:title,dcterms:identifier,IS_COLLECTION,URL:1,RELATION:dc:creator']
        data.append("My title 1,1234,,http://ptsefton.com,12345")
        data.append("My title 2,1235,,http://ptsefton.com,")
        data.append("My title 3,1236,,http://ptsefton.com,")
        data.append("My collection,1237,yes,")
        c = CSVData(data)
        c.get_items()
        self.assertEqual(len(c.items), 3)
        self.assertEqual(len(c.collections), 1)

class TestFields(unittest.TestCase):
    def test_file(self):
        f = Field("FILE:1")
        self.assertEqual(f.type, Field.FILE)
        self.assertEqual(f.namespace.URI, None)
        self.assertEqual(f.field_name, "1")
        
    def test_url(self):
        f = Field("URL:1001 1")
        self.assertEqual(f.type, Field.URL)
        self.assertEqual(f.namespace.URI, None)
        self.assertEqual(f.field_name, "1001 1")

    def test_relation(self):
        f = Field("RELATION:dc:title")
        self.assertEqual(f.type, Field.RELATION)
        self.assertEqual(f.namespace.prefix, "dcterms")
        self.assertEqual(f.field_name, "title")


        f = Field("REL:dc:title")
        self.assertEqual(f.type, Field.RELATION)
        self.assertEqual(f.namespace.prefix, "dcterms")
        self.assertEqual(f.field_name, "title")

        
        f = Field("RELATION:title")
        self.assertEqual(f.type, None)
        self.assertEqual(f.namespace.name, None)
        self.assertEqual(f.field_name, None)

        self.assertEqual(Field("IS_COLLECTION").type, Field("IS_SET").type)
        self.assertEqual(Field("IS_COLLECTION").type, Field.IS_COLLECTION)
        
if __name__ == '__main__':
    unittest.main()
