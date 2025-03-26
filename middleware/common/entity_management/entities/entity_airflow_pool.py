from middleware.api.common.helpers import convert_to_bool
from middleware.common.entity_management.entities.entity_object import EntityObject


class EntityAirflowPool(EntityObject):
    """
    Class of airflow pool entity
    """

    def __init__(self, name: str = None, slots: int = None,
                 default: bool = None):
        self._name = name
        self._slots = slots
        self._default = default

    @property
    def name(self) -> str:
        """
        Get name.

        @return: name
        """
        return self._name

    def set_name(self, name):
        """
        Set new value of name

        @param name: new value name
        """
        self._name = name

    @property
    def slots(self) -> int:
        """
        get slots

        @return slots
        """
        return self._slots

    def set_slots(self, slots):
        """
        Set new value of slots

        @param slots: new value slots
        """
        self._slots = slots

    @property
    def default(self) -> bool:
        """
        get default

        @return default
        """
        return self._default

    def set_default(self, default):
        """
        Set new value of default

        @param default: new value default
        """
        self._default = default

    @staticmethod
    def from_json_dict(airflow_pool: dict):
        """
        Create class instance from dict
        """
        return EntityAirflowPool(
            name=airflow_pool.get("name"),
            slots=int(airflow_pool.get("slots", 128)),
            default=convert_to_bool(airflow_pool.get("default", None))
        )

    def to_json_dict(self) -> dict:
        """
        return json definition of EntityAirflowPool

        @return: json object of EntityAirflowPool
        """
        json_dict = {}
        if self.name:
            json_dict["name"] = self.name
        if self.slots:
            json_dict["slots"] = self.slots
        if self.default is not None:
            json_dict["default"] = self.default
        return json_dict
