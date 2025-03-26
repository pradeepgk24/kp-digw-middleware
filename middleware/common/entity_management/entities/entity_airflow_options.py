import json

from middleware.common.entity_management.entities.entity_airflow_pool import (
    EntityAirflowPool,
)
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.helpers.utils import convert_str_dict_to_correct_types


class EntityAirflowOptions(EntityObject):
    """
    Class of airflow options entity
    """

    def __init__(
            self,
            dag_instance_parameters: dict = None,
            dag_concurrency: int = None,
            airflow_pool_name: str = None,
            airflow_pool_slots: int = None,
            airflow_pools: [EntityAirflowPool] = None,
            aws_connection_name: str = None,
            airflow_tags: list = None,
    ):
        self._dag_instance_parameters = dag_instance_parameters
        self._dag_concurrency = dag_concurrency
        self._airflow_pool_name = airflow_pool_name
        self._airflow_pool_slots = airflow_pool_slots
        self._airflow_pools = airflow_pools
        self._aws_connection_name = aws_connection_name
        self._airflow_tags = airflow_tags

    @property
    def dag_instance_parameters(self) -> dict:
        """
        Get dag instance parameters.

        :return: dag instance parameters
        """
        if self._dag_instance_parameters is None:
            self._dag_instance_parameters = {}
        return self._dag_instance_parameters

    def set_dag_instance_parameters(self, dag_instance_parameters):
        """
        Set new value of dag_instance_parameters

        :param dag_instance_parameters: new value dag_instance_parameters
        """
        self._dag_instance_parameters = dag_instance_parameters

    @property
    def airflow_pool_name(self):
        """
        get airflow pool name

        :return airflow Pool
        """
        return self._airflow_pool_name

    def set_airflow_pool_name(self, airflow_pool_name):
        """
        Set new value of set airflow pool name

        :param airflow_pool_name: new value airflow pool
        """
        self._airflow_pool_name = airflow_pool_name

    @property
    def airflow_pool_slots(self):
        """
        get airflow pool slots

        :return airflow pool slots
        """
        return self._airflow_pool_slots

    def set_airflow_pool_slots(self, airflow_pool_slots):
        """
        Set new value of airflow pool slots

        :param airflow_pool_slots: new value airflow pool slot
        """
        self._airflow_pool_slots = airflow_pool_slots

    @property
    def dag_concurrency(self) -> int:
        """
        Get dag concurrency.

        :return: dag concurrency
        """
        return self._dag_concurrency

    def set_dag_concurrency(self, dag_concurrency):
        """
        Set new value of  dag_concurrency

        :param dag_concurrency: new value dag_concurrency
        """
        self._dag_concurrency = dag_concurrency

    @property
    def airflow_pools(self) -> [EntityAirflowPool]:
        """
        Get airflow_pools.

        :return: airflow_pools
        """
        if self._airflow_pools is None:
            return []
        return self._airflow_pools

    @property
    def aws_connection_name(self) -> str:
        """
        Get aws_connection_name.

        :return: aws_connection_name
        """
        return self._aws_connection_name if self._aws_connection_name else None

    @property
    def airflow_tags(self) -> [str]:
        """
        Get airflow_tags.

        :return: airflow_tags
        """
        if self._airflow_tags is None:
            return []
        return self._airflow_tags

    @staticmethod
    def from_json_dict(airflow_options: dict):
        """
        Create class instance from model/dict/request
        """
        if airflow_options.get("dagInstanceParameters"):
            dag_instance_params_casted = convert_str_dict_to_correct_types(
                airflow_options.get("dagInstanceParameters", {})
            )
        else:
            dag_instance_params_casted = {}
        return EntityAirflowOptions(
            dag_instance_parameters=dag_instance_params_casted,
            dag_concurrency=int(airflow_options.get("dagConcurrency"))
            if airflow_options.get("dagConcurrency")
            else None,
            airflow_pool_name=airflow_options.get("airflowPool", {}).get(
                "poolName", None
            ),
            airflow_pool_slots=airflow_options.get("airflowPool", {}).get(
                "poolSlots", None
            ),
            airflow_pools=[
                EntityAirflowPool.from_json_dict(pool)
                for pool in airflow_options.get("airflowPools", [])
            ],
            aws_connection_name=airflow_options.get("awsConnectionName"),
            airflow_tags=airflow_options.get("tags", []),
        )

    def to_json_dict(self) -> dict:
        """
        return json definition of EntityAirflowOptions

        :return: json object of EntityAirflowOptions
        """
        json_dict = {}
        if self.dag_instance_parameters:
            json_dict["dagInstanceParameters"] = self.dag_instance_parameters
        if self.dag_concurrency:
            json_dict["dagConcurrency"] = self.dag_concurrency
        if self.airflow_pool_name:
            json_dict["airflowPool"] = {"poolName": self.airflow_pool_name}
        if self.airflow_pool_slots:
            json_dict["airflowPool"].update({"poolSlots": self.airflow_pool_slots})
        if self.airflow_pools:
            json_dict["airflowPools"] = [
                pool.to_json_dict() for pool in self.airflow_pools
            ]
        if self.aws_connection_name:
            json_dict["awsConnectionName"] = self.aws_connection_name
        if self.airflow_tags:
            json_dict["tags"] = self.airflow_tags
        return json_dict

    @staticmethod
    def from_str_dict(airflow_options: str):
        """
        Return instance of EntityAirflowOptions created from str rep of json

        :param airflow_options: str representation of airflow_options
        """
        return EntityAirflowOptions.from_json_dict(json.loads(airflow_options))

