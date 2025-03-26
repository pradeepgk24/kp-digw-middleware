# pylint: skip-file
from middleware.common.entity_management.entities.entity_object import EntityObject
from datetime import datetime

from middleware.common.helpers.datetime_formatter import from_datetime_to_str


class EntityObjectRun(EntityObject):
    """
    Entity for catching runs of objects.
    """

    def __init__(self, start_date: datetime, run_id: str, end_date: datetime = None, logical_date: datetime = None,
                 state: str = None, run_type: str = None):
        self._start_date = start_date
        self._end_date = end_date
        self._logical_date = logical_date
        self._state = state
        self._run_type = run_type
        self._run_id = run_id

    @property
    def run_id(self):
        """
        get run_id

        return run_id

        """
        return self._run_id

    @property
    def start_date(self):
        """
        get start_date

        return start_date

        """
        return self._start_date

    @property
    def end_date(self):
        """
        get end_date

        return end_date

        """
        return self._end_date

    @property
    def logical_date(self):
        """
        get logical_date

        return logical_date

        """
        return self._logical_date

    @property
    def state(self):
        """
        get state

        return state

        """
        return self._state

    @property
    def run_type(self):
        """
        get run_type

        return run_type

        """
        return self._run_type

    def to_json_dict(self):
        """
        return json definition of Entity Object run

        :return: json object of Entity Object run
        """

        json_dict = {
            'startDate': from_datetime_to_str(self.start_date),
            'endDate': from_datetime_to_str(self.end_date),
            "logicalDate": from_datetime_to_str(self.logical_date),
            "state": self.state,
            "runType": self.run_type,
            "runId": self.run_id
        }
        return json_dict

