# What is this?

This is a work-in-progress script to upload a spreadsheet of data with one or more worksheets to one or more Omeka collections.

Some quick notes, to be turned into a how-to later.

usage

python xlsx2omeka.py http://address.of.omeka input-file.xlsx omeka-key -i Identifier -t Title


What it does:

*  For each worksheet in the .xlsx file, see if there's an Omeka collection with the same name, if there is it will try to upload the content. To be able to upload content, the sheet must have:
   *  A column calld Omeka Type (the item type to upload to)
   *  A column with a unique ID (pass this in to the script using -i - defaults to Identifier) 

The script will create a new spreadsheet called input-file.xlsx.mapping.xlsx: this contains:

* A sheet relating the IDs you supplied to Omeka IDs
* A sheet where you can add mappings between column names and Omeka fields - if you use names from the Dublin Core set or create new ones on the server they will auto-map, but you may prefer to leave your original data intact and enter mappings in this sheet. More on how soon.

