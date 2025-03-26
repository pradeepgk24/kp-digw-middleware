import json

from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_airflow_options import EntityAirflowOptions


class EntityWorkflowAdvancedOptions(EntityObject):
    """
    Entity Workflow Advanced Options
    """

    def __init__(self, entity_airflow_options: EntityAirflowOptions = None):
        self._entity_airflow_options = entity_airflow_options

    @property
    def entity_airflow_options(self) -> EntityAirflowOptions:
        """
        get entity_airflow_options

        return entity_airflow_options
        """
        if self._entity_airflow_options is None:
            self._entity_airflow_options = EntityAirflowOptions()
        return self._entity_airflow_options

    def to_json_dict(self):
        """
        Return a JSON representation of Entity pipeline advanced options
        """
        if self.entity_airflow_options:
            return {
                "airflowSettings": self.entity_airflow_options.to_json_dict() if self.entity_airflow_options else {}
            }
        return None

    @staticmethod
    def from_json_dict(advance_options: dict):
        """
        Return instance of EntityWorkflowAdvancedOptions created from json dict

        :param advance_options: dict representation of advanced options
        """
        entity_airflow_options = None
        if "airflowSettings" in advance_options:
            entity_airflow_options = EntityAirflowOptions.from_json_dict(advance_options["airflowSettings"])
        return EntityWorkflowAdvancedOptions(
            entity_airflow_options=entity_airflow_options
        )

    @staticmethod
    def from_str_dict(advance_options: str):
        """
        Return instance of EntityWorkflowAdvancedOptions created from str rep of json

        :param advance_options: str representation of advanced options
        """
        return EntityWorkflowAdvancedOptions.from_json_dict(json.loads(advance_options))