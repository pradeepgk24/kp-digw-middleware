# you can import standard libraries available in DIFW package
# ========================================================
# PUT YOUR STANDARD FW LIBRARIES IMPORTS HERE
# ========================================================
from pyspark.sql import DataFrame

# custom packages that are installed at runtime can be imported directly
# ========================================================
# PUT YOUR CUSTOM LIBRARIES IMPORTS HERE
# ========================================================


# this is the only mandatory function you have to have in your custom code
# the full interface is:
# def main(job_configuration, table_configuration,
#          custom_parameters, component_instance, logger, dataframe):
# all parameters are passed as named arguments, so if your custom component does not need all
# the arguments, just remove them and use **kwargs at the end
def main(job_configuration, table_configuration, custom_parameters, component_instance, logger, dataframe, **kwargs):
    logger.info('Start custom spark transformer')
    assert isinstance(dataframe, DataFrame)
    logger.info(repr(job_configuration))
    logger.info(repr(table_configuration))
    logger.info(repr(custom_parameters))
    # ========================================================
    # PASS YOUR CUSTOM CODE HERE
    # ========================================================
    # have to return Spark dataframe
    return None
