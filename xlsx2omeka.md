# About

This is a work-in-progress script to upload an excel spreadsheet (.xlsx) of data with one or more worksheets to one or more Omeka collections. The purpose of the script is to allow a tecnically adept person to load data into an Omeka instance 

# Audience

This document is aimed at technical staff familiar with commandline systems administration and Python programming, and assumes the reader may have to do some experimentation, research and problem solving.

# How-to use this script
## Set up an Omeka server

* Install Omeka 2.2
* Increase the upload limits in the PHP5.ini file to a big enough number for your project's files
  In /etc/php.ini change these two settings.
```  
   post_max_size = 48M
   upload_max_filesize = 48M
```
  Replace '48M' with the maximum file size you are expecting to upload during your project.

* In the Admin, allow upload of all the file types you have in your data (or allow all)
* Get an API key for a superuser
* Add the following plugins: eResearch version of ItemRelations, Extended Dublin Core


# Get ready to run the script
To get set up:
* Put the address of the server and your API key in ~/.omeka.config, e.g.:
```
{
   "api_url":"http://130.220.210.60/api",
   "key":"apparentlyrandomcharacters"
}
```

* Or pass these detail on the commandline using the -u (URL) and -k (Key) flags (examples below will assume the .omeka.config file exists.

## Set up a spreadsheet

To structure your spreadsheet:
* Name each worksheet/tab with the name of a collection to which you want to upload (tip: use the -c flag to force collections to be auto-created).
* For each worksheet:
  * Make sure there is an "Identifier" column containing an ID which is unique to the whole workbook (tip: use sequential integers using auto-fill but make sure not to reuse) (tip: pass the name of a diferent Identifier column using -i)
  * Make sure there is a column "Omeka Type" with the name of an existing Item Type for every data row (tip: use -y flag to force item types to be auto-created).
  * Make sure there are Omeka metadata elements for each bit of metadata you'd like to import corresponding to the column headers on the worksheet, the script will attempt to find an element match



## Run the initial import

Once you have a spreadsheet, you can run the script and upload data to an Omeka instance. The first run will (should) create Omeka items, but it will not upload any files, or relate items to each other. To upload files from the local file system, or via download from a URL you will need to add some configuration to the mapping spreadsheet, which the script will automatically create the first time you run it.

At the end of the first run, the script will create a new spreadsheet with data about how the spreadsheet maps to Omeka. So if you ran `xlsx2omeka.py my-sheet.xlsx`, the script will create `my-sheet.xlsx.mapping.xlsx`, containing the following sheets:
* `Omeka Mapping` A sheet where you can add or tweak mappings between column names and Omeka fields - if you use names from the Dublin Core set or create new ones on the server they will auto-map, but you may prefer to leave your original data intact and enter mappings in this sheet.
*  `ID Mapping` A sheet relating the IDs you supplied to Omeka IDs - **do not touch this**
*  `Download` A sheet that keeps track of a cache of downloaded files **you should not need to touch this**
*  `Multiple Uploads` A sheet that allows you to specify that a particular collection should be uploaded multiple time, for testing purposes. TODO: Document this. **Only touch this if you are stress-testing Omeka**

## Configure file uploads and item-relations

To add files:
* To upload files from the file system, in the `Omeka Mapping` sheet of the mapping spreadsheet, put `yes` in the `File` column for the field in question.
* To upload files via a URL, in the `Omeka Mapping` sheet of the mapping spreadsheet, put `yes` in the `Download` column for the field in question.

To relate items to each other:
*   Make sure the spreadsheet you are using has relations whithin it.
  For example, if you have a `People` sheet and a `Books` sheet, you could relate books to people by:
  * Add a column `Creator` to the books sheet
  * For each book, put the Identifier of a person into the `Creator` field (at this stage it doesn not handle multiple IDs).
  * Run the script once to create the mapping sheet
  * Add a relation to the `Omeka Mapping` sheet.
 ```
| Omeka Element | Column   | Collection | Omeka Element Set | Related         |
| Creator       | Creator  | Books      | Dublin Core       | dcterms:Creator |
```
## Second or subsequent runs
Once you have made changes to the mapping spreadsheet, subsequent runs should over-write the items created in previous runs, as long as you don't delete items from Omeka, or remove data from the `ID Mapping` sheet.

* Save and close the mapping spreadsheet if you have made any changes
* Re run the script.

## Add or change metadata mapping


# Problems, FAQ

## Items from my spreadsheet won't upload

Check that for each row.
* There is an ID - either in the `Identifier` column or another column you specified using the `-i` flag.
* There is an Omeka Type and the Omeka Type exists as an Item Type in your Omeka isntances (or use the `-y` flag to auto-create)

## Some items are coming through without a title but there is a `Title` column in my spreadsheet.
Check that there is no space before or after Title in the column-header - sometimes spurious spaces get created by Excel when importing CSV files.

## Some files won't upload

Check the Omeka confiuration allows upload of that file type, and check that the file is within the upload limits you configured on the server see above.



