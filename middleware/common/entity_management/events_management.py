import json
import datetime
from typing import List

from middleware.common.entity_management.entities.entity_event import EntityEvent
from middleware.common.entity_management.entities.entity_sub_event import EntitySubEvent
from middleware.common.helpers.exception import NoDataError, AuthorizationError
from middleware.common.entity_management.entity_management import EntityManagement
from middleware.common.metadatabase.events_metadata_provider import EventsMetadataProvider
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.security.action_type import ActionType


class EventsManagement(EntityManagement):
    """
    Events Management.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._events_metadata_provider = None

    @property
    def events_metadata_provider(self):
        """
        events metadata provider property.
        """
        if self._events_metadata_provider is None:
            self._events_metadata_provider = EventsMetadataProvider(self.logger,
                                                                    self.metadatabase_connection,
                                                                    self.lambda_secrets_manager)
        return self._events_metadata_provider

    def create_or_update_event(self, event: EntityEvent) -> EntityEvent:
        """
        Creates or updates event in metadata database.

        @param event: event to create
        """
        self.logger.info("Start method create_event")
        return EntityEvent.from_metadb_object(
            self.events_metadata_provider.insert_or_update_event(event.to_metadb_object(), self.user_isid))

    def update_event(self, event: EntityEvent) -> EntityEvent:
        """
        Updates event in metadata database.

        @param event: event to update
        """
        self.logger.info("Start method update_event")
        return EntityEvent.from_metadb_object(
            self.events_metadata_provider.update_event(event.to_metadb_object(), self.user_isid))

    def get_event(self, event_id: str, get_sub_events: bool) -> EntityEvent:
        """
        Gets event details on basis of given event id.

        @param: event_id: id of the async event
        @param: get_sub_events : flag that determines whether to retrieve the corresponding
        sub events related to given event id
        """
        self.logger.info(f"Start method get_event with event_id={event_id}")
        retrieved_event = EntityEvent.from_metadb_object(
            self.events_metadata_provider.get_event(event_id, self.user_isid))
        if retrieved_event and get_sub_events:
            retrieved_event.sub_events = self.get_all_sub_events(event_id)
            retrieved_event.sub_events_count = len(retrieved_event.sub_events)

        if not retrieved_event:
            raise NoDataError(f"Event with id {event_id} does not exists")

        return retrieved_event

    def get_all_sub_events(self, sub_event_id: str) -> List[EntitySubEvent]:
        """
        Gets all the sub events that are the defined for the request id, the
        sub events handling is in the events management, otherwise we would
        need to import sub events management here.

        @param: sub_event_id: id of the async event
        @return: list of sub events
        """
        self.logger.info(f"Going to retrieve all sub_events for event id - {sub_event_id}")
        return EntitySubEvent.from_metadb_objects(
            self.events_metadata_provider.get_sub_events(sub_event_id, self.user_isid))

    def create_or_update_event_entity(self, event_type: str, request_id: str, json_body: dict,
                                      status: str = "in_progress", check_permission: bool = False) -> EntityEvent:
        """
        Create or update event object
        @param event_type: event type
        @param request_id: request id
        @param json_body: json body
        @param status: status, is defaulted as in_progress
        @param check_permission: check permission, defaulted as False to not break async calls
        @return: None
        """
        if check_permission and self.auth_validator.validate(
                ActionType.CREATE_EVENT, {}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                "does not have permission to createEvent")
        event = EntityEvent(event_id=request_id,
                            type=event_type, input=json.dumps(json_body), output=None,
                            started_at=datetime.datetime.now(), finished_at=None,
                            status=status, status_code=0, created_by=self.user_isid,
                            project_id=self.project_id, group_id=self.group_id,
                            is_active=True)
        self.create_or_update_event(event)
        return event

    def update_event_entity(self, event: EntityEvent, status: str, status_code: int, output: dict = None,
                            is_active: bool = True) -> None:
        """
        Set event attributes
        @param event: event object
        @param status: status
        @param status_code: status code
        @param output: output
        @param is_active: is active
        @return: none
        """
        event.status = status
        event.finished_at = datetime.datetime.now()
        event.status_code = status_code
        event.output = output
        event.is_active = is_active
        self.update_event(event)

    def create_or_update_sub_event(self, sub_event: EntitySubEvent) -> EntitySubEvent:
        """
        Creates sub event in metadata database.

        @param sub_event: sub event to create
        """
        self.logger.info("Start method create_sub_event")
        return EntitySubEvent.from_metadb_object(
            self.events_metadata_provider.insert_or_update_sub_event(sub_event.to_metadb_object(), self.user_isid))

    def create_or_update_sub_event_entity(self, request_id: str, sequence_number: int, event_type: str,
                                          status: str, output: str = None) -> EntitySubEvent:
        """
        Create sub event object
        @param request_id: request id
        @param sequence_number: sequence number
        @param event_type: event type
        @param status: status
        @param output: output
        @return: EntitySubEvent object
        """
        sub_event = EntitySubEvent(event_id=request_id, sequence_number=sequence_number, type=event_type,
                                   input=None, output=output, started_at=datetime.datetime.now(),
                                   finished_at=datetime.datetime.now(), status=status)
        self.create_or_update_sub_event(sub_event)
        return sub_event
