# pylint: skip-file
# pragma: no cover

from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import utils, correlation_paths
from aws_lambda_powertools.utilities.data_classes import event_source

from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.api.common.decorators import enable_cors, catch_uncaught_errors
from middleware.api.common.helpers import (
    get_middleware_logging_level,
    get_lambda_secrets_manager,
)
from middleware.api.security.security import PermissionsLambda

# Setup the root logger
lambda_function_logger = Logger(service="MetadataAPI", level=get_middleware_logging_level())
utils.copy_config_to_registered_loggers(source_logger=lambda_function_logger)

# Initialize secrets manager
lambda_secrets_manager = get_lambda_secrets_manager()

@enable_cors
@catch_uncaught_errors
@lambda_function_logger.inject_lambda_context(
    log_event=True,
    clear_state=True,
    correlation_id_path=correlation_paths.API_GATEWAY_REST,
)
@event_source(data_class=DIFWAPIGatewayProxyEvent)
def lambda_handler(event: DIFWAPIGatewayProxyEvent, context):
    """Function called by the AWS Lambda to run Permissions API"""
    return PermissionsLambda(
        event, context, lambda_function_logger, lambda_secrets_manager).run_lambda()