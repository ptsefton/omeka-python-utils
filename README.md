# Omeka commandline utilities

This repository is a collection of python-based commandline utilities for Omeka for use by technically adept users with basic systems administration, commandline and programming experience.

The initial version of this work was based on a fork of Caleb McDaniel's omekadd scripts and python API, but we have since made major changes to the API library and created new scripts. Thanks Caleb!

There are scripts here to:
* [http://www.uws.edu.au/ics/people/researchers/brett_bennett Upload a spreadsheet with multiple tabs (one per collection) to Omeka].
* Delete all items and collections from an Omeka repostiory: delete_all_items_and_collections.py (use with caution, obviously).
* Upload a directory of images to Omeka, creating one item per picture (upload_photos.py). NOTE: Depends on having exiftool installed as a binary)

