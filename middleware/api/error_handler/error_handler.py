from middleware.api.common.helpers import get_env_or_header_value
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.common.entity_management.events_management import EventsManagement
from middleware.common.helpers.exception import NoDataError


class ErrorHandlerLambda(AWSLambdaEventHandler):
    """
    Lambda class for Error Handling API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, response_payload, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.events_management = EventsManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)
        self.response_payload = response_payload

        self.payload_error_mapping = {
            "AuthTokenError": {
                "info": "Auth token error during API call",
                "status_code": 401
            },
            "NoDataError": {
                "info": "Data not found error during API call",
                "status_code": 404
            },
            "EntityConflictError": {
                "info": "Data with same identifiers already exists",
                "status_code": 409
            },
            "EntityDisabledError": {
                "info": "Subject is disabled",
                "status_code": 410
            },
            "BadRequest": {
                "info": "Bad request error during API call",
                "status_code": 400
            },
            "AuthorizationError": {
                "info": "Authorization error during API call",
                "status_code": 403
            },
            "FailedConnectionError": {
                "info": "Failed to establish connectivity during API call",
                "status_code": 401
            },
            "default": {
                "info": "Internal server error",
                "status_code": 500
            }
        }

    def _invoke_handle_error(self):
        """
        Invoke error handling logic

        :return: None
        """
        error_type = self.response_payload['errorType']
        request_id = self.event['requestContext']['extendedRequestId']
        stack_trace = self.response_payload['stackTrace']
        stack_trace.append(self.response_payload.get("errorMessage"))

        try:
            event = self.events_management.get_event(event_id=request_id, get_sub_events=False)
        except NoDataError:
            pipeline_event = "createPipeline" if self.event.path.endswith('/pipelines/async') else "updatePipeline"
            event = self.events_management.create_or_update_event_entity(
                event_type=pipeline_event,
                request_id=request_id,
                json_body={}
            )

        event_error_attributes = self.payload_error_mapping.get(error_type, self.payload_error_mapping['default'])
        self.logger.info(event_error_attributes['info'])
        self.events_management.update_event_entity(
            event=event,
            status="failed",
            status_code=event_error_attributes['status_code'],
            output=str(stack_trace),
            is_active=False
        )

    def invoke(self):
        """
        Invoke error handling lambda function logic

        :return: None
        """
        # **************************************** Post Error Handling *********************************************
        if self.event.resource.endswith("errorhandler"):
            self._invoke_handle_error()
        else:
            self.logger.warning(
                f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
