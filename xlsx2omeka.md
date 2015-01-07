# What is this?

This is a work-in-progress script to upload an excel spreadsheet (.xlsx) of data with one or more worksheets to one or more Omeka collections. To structure your spreadsheet:

* Name each worksheet/tab with the name of a collection to which you want to upload (tip: use the -c flag to force collections to be auto-created).
* For each worksheet:
  * Make sure there is an "Identifier" column containing an ID which is unique to the whole workbook (tip: use sequential integers using auto-fill but make sure not to reuse) (tip: pass the name of a diferent Identifier column using -i)
  * Make sure there is a column "Omeka Type" with the name of an existing Item Type for every data row (tip: these can not be auto-created at this stage, so create it manually in the admin interface if needed)

For usage, type:

    python xlsx2omeka.py input-file.xlsx -h

* Put the adress of the server and your API key in ~/.omeka.config, e.g.:
```
{
   "api_url":"http://130.220.210.60/api",
   "key":"apparentlyrandomcharacters"
}
```

* Or add them on the commandline using the -u and -k flags.

What it does:

*  For each worksheet in the .xlsx file upload data to a collection with the same name.
   *  To be able to upload content, the sheet must have:
      *  A column calld Omeka Type (the item type to upload to)
      *  A column with a unique ID (pass this in to the script using -i - defaults to Identifier) 

The script will create a new spreadsheet called input-file.xlsx.mapping.xlsx: this contains:

* A sheet relating the IDs you supplied to Omeka IDs
* A sheet where you can add mappings between column names and Omeka fields - if you use names from the Dublin Core set or create new ones on the server they will auto-map, but you may prefer to leave your original data intact and enter mappings in this sheet.

To create collections automatically if they're not already there.

