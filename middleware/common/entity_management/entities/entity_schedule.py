# pylint: skip-file
from datetime import datetime

from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.helpers.datetime_formater import from_datetime_to_str, from_str_to_datetime


class EntitySchedule(EntityObject):
    """
    Entity  Schedule
    """

    def __init__(self, schedule: str = None, initial_load_start_date: datetime = None,
                 lower_bound_start_date: datetime = None):
        self._schedule = schedule
        self._initial_load_start_date = initial_load_start_date
        self._lower_bound_start_date = lower_bound_start_date

    @property
    def schedule(self):
        """
        get schedule

        return schedule
        """
        return self._schedule

    def set_schedule(self, schedule):
        """
        Set schedule

        :param schedule: new value of schedule
        """
        self._schedule = schedule

    @property
    def initial_load_start_date(self):
        """
        get initial_load_start_date

        return initial_load_start_date
        """
        return self._initial_load_start_date

    def set_initial_load_start_date(self, initial_load_start_date):
        """
        Set initial_load_start_date

        :param initial_load_start_date: new value of initial_load_start_date
        """
        if isinstance(initial_load_start_date, str):
            initial_load_start_date = datetime.fromisoformat(initial_load_start_date)
        self._initial_load_start_date = initial_load_start_date

    @property
    def lower_bound_start_date(self):
        """
        get lower_bound_start_date

        return lower_bound_start_date
        """
        return self._lower_bound_start_date

    def set_lower_bound_start_date(self, lower_bound_start_date):
        """
        Set lower_bound_start_date

        :param lower_bound_start_date: new value of initial_load_start_date
        """
        if isinstance(lower_bound_start_date, str):
            lower_bound_start_date = datetime.fromisoformat(lower_bound_start_date)
        self._lower_bound_start_date = lower_bound_start_date

    @staticmethod
    def from_json_dict(scheduling_model):
        """
        Create class instance from model/dict/request
        """
        if not scheduling_model:
            return None
        initial_start_date = scheduling_model.get('initialLoadStartDate')
        lower_bound_start_date = scheduling_model.get('lowerBoundStartDate')
        return EntitySchedule(schedule=scheduling_model['schedule'],
                              initial_load_start_date=from_str_to_datetime(initial_start_date),
                              lower_bound_start_date=from_str_to_datetime(lower_bound_start_date))

    def to_json_dict(self):
        """
        Return a JSON representation of Entity  Schedule
        """
        return {
            "schedule": self.schedule,
            "initialLoadStartDate": from_datetime_to_str(self.initial_load_start_date),
            "lowerBoundStartDate": from_datetime_to_str(self.lower_bound_start_date)
        }
