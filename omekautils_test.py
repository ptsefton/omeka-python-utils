from omekautils import create_file_logger, create_stream_logger, \
    create_null_logger


# Test methods for Logging
# -------------------------------------------------------------------
def __test_logging():
    fl = create_file_logger("test_file_logger", 'logtest.out')
    sl = create_stream_logger("test_stream_logger")
    nl = create_null_logger("test_null_logger")
    
    fl.info("This should go to the file")
    sl.info("This should go to the standard output")
    nl.info("This should go nowhere")


__test_logging()