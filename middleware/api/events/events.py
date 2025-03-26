import json
import uuid

from middleware.common.entity_management.events_management import EventsManagement
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.helpers import get_env_or_header_value, convert_to_bool
from middleware.api.common.http_method_utils import create_error_response
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent


class EventsLambda(AWSLambdaEventHandler):
    """
    Lambda class for Events API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.events_management = EventsManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)

    def _invoke_get_event(self):
        """
        Invoke method call get event

        @return: API response of get event
        """
        self.logger.info("Calling _invoke_get_event")
        event_id = self.event.path_parameters["eventId"]
        get_sub_events = convert_to_bool(self.event.query_string_parameters.get('getSubEvents', True))
        response_object = self.events_management.get_event(event_id=event_id,
                                                           get_sub_events=get_sub_events)
        return {'statusCode': 200, 'body': json.dumps(response_object.to_json_dict())}

    def _invoke_create_event(self):
        """
        Invoke method call create event

        @return: API response of create event
        """
        self.logger.info("Calling _invoke_create_event")
        # eventType is mandatory parameter in api gateway definition, when not present, error from api gateway
        # is raised and lambda is never triggered
        event_type = self.event.query_string_parameters["eventType"]
        event = self.events_management.create_or_update_event_entity(
            request_id=str(uuid.uuid4()), event_type=event_type, json_body=self.event.json_body, check_permission=True)
        return {'statusCode': 201, 'body': json.dumps({"status": "created",
                                                       "eventId": event.event_id,
                                                       "details": f"Event of event type {event_type} was successfully"
                                                                  f" created with event id {event.event_id}"})}

    def invoke(self):
        """
        Invoke lambda function logic

        @return:
        """
        # ******************************** GET EVENT DETAIL CALL *****************************************
        if self.event.http_method == "GET" and self.event.resource.endswith(
                "/events/{eventId}"):
            return self._invoke_get_event()
        # ******************************** CREATE EVENT DETAIL CALL *****************************************
        if self.event.http_method == "POST" and self.event.resource.endswith(
                "/events"):
            return self._invoke_create_event()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct events method was chosen")
