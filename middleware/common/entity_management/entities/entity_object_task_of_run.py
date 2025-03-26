# pylint: skip-file
from middleware.common.entity_management.entities.entity_object import EntityObject
from datetime import datetime

from middleware.common.helpers.datetime_formatter import from_datetime_to_str


class EntityObjectTaskOfRun(EntityObject):
    """
    Entity for catching task instances of runs of objects.
    """

    def __init__(self, task_id: str, start_date: datetime, duration: float, state: str, try_number: int):
        self._task_id = task_id
        self._start_date = start_date
        self._duration = duration
        self._state = state
        self._try_number = try_number

    @property
    def task_id(self) -> str:
        """
        get task_id

        @return task_id name
        """
        return self._task_id

    @property
    def start_date(self) -> datetime:
        """
        get start_date

        @return start_date name
        """
        return self._start_date

    @property
    def duration(self) -> float:
        """
        get duration

        @return duration
        """
        return self._duration

    @property
    def state(self) -> str:
        """
        get state

        @return state
        """
        return self._state

    @property
    def try_number(self) -> int:
        """
        get try_number

        @return try_number
        """
        return self._try_number

    def to_json_dict(self):
        """
        return json definition of Entity Pipeline run

        :return: json object of Entity Pipeline run
        """

        json_dict = {
            'taskId': self.task_id,
            'startDate': from_datetime_to_str(self.start_date),
            "duration": self.duration,
            "state": self.state,
            "tryNumber": self.try_number
        }
        return json_dict