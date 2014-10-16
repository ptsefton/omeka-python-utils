from os.path import expanduser
import json
import unicodedata


def get_omeka_config(filename=None):
    if filename == None:
        filename = expanduser("~/.omeka.config")
    with open(filename) as json_data:
        d = json.load(json_data)
        json_data.close()

    if d is None:
        raise Exception("No omeka config found at " + filename)
    else:
        wanted = ['api_url', 'key']
        missing = []
        for item in wanted:
            if item not in d:
                missing.append(item)
        
        if len(missing) != 0:
            raise Exception("Missing items in omeka config file " + filename + ": " + ", ".join(missing))

    return d
    
