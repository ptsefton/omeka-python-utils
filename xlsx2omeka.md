# What is this?

This is a work-in-progress script to upload a spreadsheet of data with one or more worksheets to one or more Omeka collections.

Some quick notes, to be turned into a how-to later.

usage

python xlsx2omeka.py input-file.xlsx -i Identifier -t Title

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

