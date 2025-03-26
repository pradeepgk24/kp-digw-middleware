# pylint: skip-file
import json

from middleware.common.entity_management.entities.entity_aws_account_storage import EntityAwsAccountStorage
from middleware.common.entity_management.entities.entity_aws_glue_options import EntityAwsGlueOptions
from middleware.common.entity_management.entities.entity_databricks_options import EntityDatabricksOptions
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_airflow_options import EntityAirflowOptions


class EntityAdvancedOptions(EntityObject):
    """
    Entity Pipeline Advance Options
    """

    def __init__(self, entity_aws_account_storage: EntityAwsAccountStorage = None,
                 entity_glue_options: EntityAwsGlueOptions = None,
                 entity_dbx_options: EntityDatabricksOptions = None,
                 entity_airflow_options: EntityAirflowOptions = None):
        self._entity_aws_account_storage = entity_aws_account_storage
        self._entity_glue_options = entity_glue_options
        self._entity_dbx_options = entity_dbx_options
        self._entity_airflow_options = entity_airflow_options

    @property
    def entity_aws_account_storage(self) -> EntityAwsAccountStorage:
        """
        get entity_aws_account_storage

        return entity_aws_account_storage
        """
        if self._entity_aws_account_storage is None:
            self._entity_aws_account_storage = EntityAwsAccountStorage()
        return self._entity_aws_account_storage

    @property
    def entity_glue_options(self) -> EntityAwsGlueOptions:
        """
        get entity_glue_options

        return entity_glue_options
        """
        if self._entity_glue_options is None:
            self._entity_glue_options = EntityAwsGlueOptions()
        return self._entity_glue_options

    @property
    def entity_dbx_options(self) -> EntityDatabricksOptions:
        """
        get entity_dbx_options

        return entity_dbx_options
        """
        if self._entity_dbx_options is None:
            self._entity_dbx_options = EntityDatabricksOptions()
        return self._entity_dbx_options

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
        Return a JSON representation of Entity pipeline advance options
        """
        return {
            "databricks": self.entity_dbx_options.to_json_dict() if self.entity_dbx_options else {},
            "glue": self.entity_glue_options.to_json_dict() if self.entity_glue_options else {},
            "awsAccountStorage": self.entity_aws_account_storage.to_json_dict() if
            self.entity_aws_account_storage else {},
            "airflowSettings": self.entity_airflow_options.to_json_dict() if self.entity_airflow_options else {}
        }

    @staticmethod
    def from_json_dict(advance_options: dict):
        """
        Return instance of EntityAdvancedOptions created from json dict

        :param advance_options: dict representation of advance options
        """
        entity_aws_account_storage = None
        entity_dbx_options = None
        entity_glue_options = None
        entity_airflow_options = None
        if "awsAccountStorage" in advance_options:
            entity_aws_account_storage = EntityAwsAccountStorage.from_json_dict(advance_options["awsAccountStorage"])
        if "databricks" in advance_options:
            entity_dbx_options = EntityDatabricksOptions.from_json_dict(advance_options["databricks"])
        if "glue" in advance_options:
            entity_glue_options = EntityAwsGlueOptions.from_json_dict(advance_options["glue"])
        if "airflowSettings" in advance_options:
            entity_airflow_options = EntityAirflowOptions.from_json_dict(advance_options["airflowSettings"])
        return EntityAdvancedOptions(
            entity_aws_account_storage=entity_aws_account_storage,
            entity_dbx_options=entity_dbx_options,
            entity_glue_options=entity_glue_options,
            entity_airflow_options=entity_airflow_options
        )

    @staticmethod
    def from_str_dict(advance_options: str):
        """
        Return instance of EntityAdvancedOptions created from str rep of json

        :param advance_options: str representation of advance options
        """
        return EntityAdvancedOptions.from_json_dict(json.loads(advance_options))
