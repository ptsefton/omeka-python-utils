## xlsx2omeka Omeka Hack Day Tests

### Install

`git clone https://github.com/uws-eresearch/omekadd.git`

### Test for missing Python libraries

* `cd omekadd`
* `python xlsx2omeka.py`
* `sudo easy_install` missing libraries until errors cease

### Generate API key

* go to Omeka server > Admin > Users > YourName > API Keys
* enter New key label (any)
* copy Key (see **Set up config file** step)

### Set up config file

* create file `~/.omeka.config`
* copy & paste: `{ "api_url":"http://omeka_server", "key":"paste_key" }`

API URLs:  
UTS Omeka test server API url = http://130.56.251.103/omeka/api  
UWS Omeka test server API url = http://130.220.210.60/api

Key:  
See **Generate API key** step

## xslsx2omeka tests

### Test 1 - Create a new Omeka collection

In test 1 a spreadsheet of hack day attendees was used to create a new collection titled **Omeka Hack Day**, populated with person items.

* in test spreadsheet, rename worksheet tab to desired Omeka collection name (Omeka Hack Day)
* add column titled **Omeka Type** & enter an existing Omeka Item Type for each row (Person)
* add column titled **Title** (names of hack day attendees were concatenated: LastName, FirstName)
* add column titled **Identifier** & create unique ID for each row (Note: A row represents an item in a collection; unique IDs prevent new items being created on subsequent uploads)
* `cd omekadd`
* run `python xlsx2omeka.py -c ~/input-file.xlsx` (where option -c creates new collection)

Edit mapping spreadsheet created by script:

* open `input-file.xlsx.mapping.xlsx`
* add rows:

| Omeka Element | Omeka Element Set | Column | Collection | Related | File | Download | Linked |
| ------------- | ----------------- | ------ | ---------- | ------- | ---- | -------- | ------ |
| Identifier | Dublin Core | Identifier | Omeka Hack Day |
| Omeka Type | Item Type Metadata | Omeka Type | Omeka Hack Day |
| Title | Item Type Metadata | Title | Omeka Hack Day |

### Test 2 - Create a new Item Type and sub-collections

In test 2 a new Omeka Item Type **Group** was created and person-items in Test 1 were grouped together into sub-collections under a new collection titled **Groups**.

* first, create new Item Type in Omeka server (Group)
* in test spreadsheet, add new worksheet (tab title = Groups) to enable creation of new collection, add:

| Title | Omeka Type | Identifier |
| ----- | ---------- | ---------- |
| Deployment | Group | 1 |
| Manifest | Group | 2 |
| Lab Rats | Group | 3 |
| Testers | Group | 4 |

* in Test 1's collection worksheet (tab = Omeka Hack Day), add column titled **Group** & enter an identifier for each row (1 or 2 or 3 or 4)
* in mapping spreadsheet (see Test 1), add rows:

| Omeka Element | Omeka Element Set | Column | Collection | Related | File | Download | Linked |
| ------------- | ----------------- | ------ | ---------- | ------- | ---- | -------- | ------ |
| Identifier | Dublin Core | Identifier | Groups |
| Omeka Type | Item Type Metadata | Omeka Type | Groups |
| Title | Item Type Metadata | Title | Groups |

* query API to obtain Omeka server ID for new Omeka Item Type **Group** (in our case "7") (EXPAND ON HOW TO DO THIS)
* in mapping spreadsheet, add row:

| Omeka Element | Omeka Element Set | Column | Collection | Related | File | Download | Linked |
| ------------- | ----------------- | ------ | ---------- | ------- | ---- | -------- | ------ |
| Relation | Dublin Core | Group | Omeka Hack Day | 7 |

* run `python xlsx2omeka.py -c ~/input_file.xlsx`

### Test 3 - Add two one or more images to items created in Test 1

In Test 1's collection worksheet (tab = Omeka Hack Day):

* add column titled **Path** & enter file path to object 1 (e.g. /Users/carmi/Downloads/avitar-1.png)
* add column titled **Path2** & enter file path to object 2 (e.g. /Users/carmi/Downloads/avitar-2.png)
* in mapping spreadsheet (see Test 1), add rows:

| Omeka Element | Omeka Element Set | Column | Collection | Related | File | Download | Linked |
| ------------- | ----------------- | ------ | ---------- | ------- | ---- | -------- | ------ |
| Relation | Dublin Core | Path | Omeka Hack Day | | yes |
| Relation | Dublin Core | Path2 | Omeka Hack Day | | yes |

* run `python xlsx2omeka.py ~/input_file.xlsx`

## Issues

* -p option did not create public collections/items

## Notes

* mappings occur between column names and Omeka fields - use names from Dublin Core set or create new ones to suit your data





