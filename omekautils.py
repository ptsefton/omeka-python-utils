from os.path import expanduser
import json
import logging
import sys

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



# ===================================================================
# Logging
# ===================================================================
def create_file_logger(loggername, filename, mode='a', encoding=None, delay=False):
    # Create the required handler
    handler = logging.FileHandler(filename, mode, encoding, delay)
    handler.setLevel(logging.INFO)
    handler.setFormatter(__create_formatter())
    
    #create (and return) a new logger using the handler.
    return __create_logger(loggername, handler)
# end create_file_logger(loggername, filename, mode='a', encoding=None, delay=False)


def create_stream_logger(loggername, stream=sys.stdout):
    # Create the required handler
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)
    handler.setFormatter(__create_formatter())
    
    #create (and return) a new logger using the handler.
    return __create_logger(loggername, handler)
# end create_stream_logger(loggername, stream=sys.stdout)


def create_null_logger(loggername):
    # Create the required handler
    handler = logging.NullHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(__create_formatter())
    
    #create (and return) a new logger using the handler.
    return __create_logger(loggername, handler)
# end create_null_logger(loggername)


# Private methods for Logging
# -------------------------------------------------------------------

def __create_logger(loggername, handler):
    logger = logging.getLogger(loggername)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


def __create_formatter():
    return logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# end Logging
# ===================================================================
