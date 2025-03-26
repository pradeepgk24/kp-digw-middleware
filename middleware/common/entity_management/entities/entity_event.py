from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import Events
from middleware.common.entity_management.entities.entity_sub_event import EntitySubEvent
from middleware.common.helpers.datetime_formater import from_datetime_to_str

from datetime import datetime


class EntityEvent(EntityObject):
    """
    Entity Events
    """

    def __init__(self, event_id: str, type: str = None, input: str = None,
                 output: str = None, started_at: datetime = None, finished_at: datetime = None,
                 created_by: str = None, project_id: str = None, group_id: str = None, is_active: bool = None,
                 status: str = None, status_code: int = None, sub_events: [EntitySubEvent] = None):
        self._event_id = event_id
        self._type = type
        self._input = input
        self._output = output
        self._started_at = started_at
        self._finished_at = finished_at
        self._created_by = created_by
        self._project_id = project_id
        self._group_id = group_id
        self._is_active = is_active
        self._status = status
        self._status_code = status_code
        self._sub_events = sub_events

    @property
    def event_id(self):
        """
        Get event_id.

        @return: event_id
        """
        return self._event_id

    @property
    def type(self):
        """
        Get type.

        @return: type
        """
        return self._type

    @property
    def total_sub_events(self):
        """
        Get total_sub_events.

        @return: total_sub_events
        """
        return len(self.sub_events)

    @property
    def input(self):
        """
        Get input.

        @return: input
        """
        return self._input

    @property
    def output(self):
        """
        Get output.

        @return: output
        """
        return self._output

    @output.setter
    def output(self, output):
        """
        Set new value of output.

        @param: output
        @return new value for output

        """
        self._output = output

    @property
    def started_at(self):
        """
        Get started_at.

        @return: started_at
        """
        return self._started_at

    @property
    def finished_at(self):
        """
        Get finished_at.

        @return: finished_at
        """
        return self._finished_at

    @finished_at.setter
    def finished_at(self, finished_at):
        """
        Set new value of finished_at.

        @param: finished_at
        @return new value for finished_at

        """
        self._finished_at = finished_at

    @property
    def created_by(self):
        """
        Get created_by.

        @return: created_by
        """
        return self._created_by

    @property
    def project_id(self):
        """
        Get project_id.

        @return: project_id
        """
        return self._project_id

    @property
    def group_id(self):
        """
        Get group_id.

        @return: group_id
        """
        return self._group_id

    @property
    def is_active(self):
        """
        Get is_active.

        @return: is_active
        """
        return self._is_active

    @is_active.setter
    def is_active(self, is_active):
        """
        Set new value of is_active.

        @param: is_active
        @return new value for is_active

        """
        self._is_active = is_active

    @property
    def status(self):
        """
        Get status.

        @return: status
        """
        return self._status

    @status.setter
    def status(self, status):
        """
        Set new value of status.

        @param: status
        @return new value for status

        """
        self._status = status

    @property
    def status_code(self):
        """
        Get status_code.

        @return: status_code
        """
        return self._status_code

    @status_code.setter
    def status_code(self, status_code):
        """
        Set new value of status_code.

        @param: status_code
        @return new value for status_code

        """
        self._status_code = status_code

    @property
    def sub_events(self):
        """
        Get sub_events.

        @return: sub_events
        """
        if self._sub_events is None:
            self._sub_events = []
        return self._sub_events

    @sub_events.setter
    def sub_events(self, sub_events):
        """
        Set new value of sub_events.

        @param: sub_events
        @return new value for sub_events

        """
        self._sub_events = sub_events

    def to_json_dict(self):
        """
        Return JSON definition of EntityEvent. Input attribute is not passed back to API GW.

        @return: JSON object of EntityEvent
        """
        return {
            'eventId': self.event_id,
            'type': self.type,
            'totalSubEvents': self.total_sub_events,
            'input': None,
            'output': self.output,
            'startedAt': from_datetime_to_str(self.started_at),
            'finishedAt': from_datetime_to_str(self.finished_at),
            'createdBy': self.created_by,
            'projectId': self.project_id,
            'groupId': self.group_id,
            'isActive': self.is_active,
            'status': self.status,
            'statusCode': self.status_code,
            "subEvents": [EntitySubEvent.to_json_dict(sub_event) for sub_event in self.sub_events]
        }

    def to_metadb_object(self):
        """
        Convert to metadb related objects.

        @return: Events
        """
        event = Events(EVENT_ID=self.event_id, TYPE=self.type,
                       INPUT=self.input, OUTPUT=self.output, STARTED_AT=self.started_at,
                       FINISHED_AT=self.finished_at, CREATED_BY=self.created_by, PROJECT_ID=self.project_id,
                       GROUP_ID=self.group_id, IS_ACTIVE=self.is_active, STATUS=self.status,
                       STATUS_CODE=self.status_code)
        return event

    @staticmethod
    def from_metadb_object(db_object: Events = None):
        """
        Convert db object to entity object.

        @param: db_object
        """
        if db_object is None:
            return None
        return EntityEvent(event_id=db_object.EVENT_ID, type=db_object.TYPE, input=db_object.INPUT,
                           output=db_object.OUTPUT, started_at=db_object.STARTED_AT, finished_at=db_object.FINISHED_AT,
                           created_by=db_object.CREATED_BY, project_id=db_object.PROJECT_ID,
                           group_id=db_object.GROUP_ID, is_active=db_object.IS_ACTIVE, status=db_object.STATUS,
                           status_code=db_object.STATUS_CODE)

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of entity objects.

        @param db_objects.
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntityEvent.from_metadb_object(db_object))
        return result
