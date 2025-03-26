from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import SubEvents
from middleware.common.helpers.datetime_formatter import from_datetime_to_str

from datetime import datetime


class EntitySubEvent(EntityObject):
    """
    Entity SubEvent
    """

    def __init__(self, event_id: str, sequence_number: int, type: str = None, input: str = None, output: str = None,
                 started_at: datetime = None, finished_at: datetime = None, is_active: bool = None, status: str = None):
        self._event_id = event_id
        self._sequence_number = sequence_number
        self._type = type
        self._input = input
        self._output = output
        self._started_at = started_at
        self._finished_at = finished_at
        self._is_active = is_active
        self._status = status

    @property
    def event_id(self):
        """
        Get event_id.

        @return: event_id
        """
        return self._event_id

    @property
    def sequence_number(self):
        """
        Get sequence_number.

        @return: sequence_number
        """
        return self._sequence_number

    @property
    def type(self):
        """
        Get type.

        @return: type
        """
        return self._type

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
    def finished_at(self, value):
        """
        Finished at setter
        """
        self._finished_at = value

    @property
    def is_active(self):
        """
        Get is_active.

        @return: is_active
        """
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        """
        Is active setter
        """
        self._is_active = value

    @property
    def status(self):
        """
        Get status.

        :return: status
        """
        return self._status

    @status.setter
    def status(self, value):
        """
        Status setter
        """
        self._status = value

    def to_json_dict(self):
        """
        Return JSON definition of EntitySubEvent.

        @return: JSON object of EntitySubEvent
        """
        return {
            'eventId': self.event_id,
            'sequenceNumber': self.sequence_number,
            'type': self.type,
            'input': None,
            'output': self.output,
            'startedAt': from_datetime_to_str(self.started_at),
            'finishedAt': from_datetime_to_str(self.finished_at),
            'isActive': self.is_active,
            'status': self.status
        }

    def to_metadb_object(self):
        """
        Convert to metadb related objects.

        @return: SubEvents
        """
        return SubEvents(EVENT_ID=self.event_id, SEQUENCE_NUMBER=self.sequence_number, TYPE=self.type,
                         INPUT=self.input, OUTPUT=self.output, STARTED_AT=self.started_at,
                         FINISHED_AT=self.finished_at, IS_ACTIVE=self.is_active, STATUS=self.status)

    @staticmethod
    def from_metadb_object(db_object: SubEvents):
        """
        Convert db object to entity object.

        @param db_object: SubEvents object from metadb
        @return: EntitySubEvent object
        """
        if db_object is None:
            return None
        return EntitySubEvent(event_id=db_object.EVENT_ID, sequence_number=db_object.SEQUENCE_NUMBER,
                              type=db_object.TYPE, input=db_object.INPUT, output=db_object.OUTPUT,
                              started_at=db_object.STARTED_AT, finished_at=db_object.FINISHED_AT,
                              is_active=db_object.IS_ACTIVE, status=db_object.STATUS)

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of entity objects.

        @param db_objects: List of db objects
        @return: List of entity objects
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntitySubEvent.from_metadb_object(db_object))
        return result




