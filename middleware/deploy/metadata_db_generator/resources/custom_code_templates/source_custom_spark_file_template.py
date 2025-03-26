# other parts of DIFW can be imported and used, but be aware that the interface or location of DIFW code can change
# ========================================================
# PUT YOUR CUSTOM LIBRARIES IMPORTS HERE
# ========================================================


# this is the only mandatory function you have to have in your custom code
# the full interface is:
# def main(job_configuration, table_configuration,
#          custom_parameters, component_instance, logger):
# all parameters are passed as named arguments, so if your custom component does not need all
# the arguments, just remove them and use **kwargs at the end
def main(job_configuration, table_configuration, custom_parameters, component_instance, logger, **kwargs):
    logger.info("Start custom spark source loader")
    logger.info(repr(job_configuration))
    logger.info(repr(table_configuration))
    logger.info(repr(custom_parameters))
    # ========================================================
    # PASS YOUR CUSTOM CODE HERE
    # ========================================================
    # have to return Spark dataframe
    return None
