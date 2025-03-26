from typing import Optional

from requests.auth import HTTPBasicAuth
from common.api_clients.common.api_client import ApiClient, ApiObjectModel
from common.helpers.exception import NotFoundError
from middleware.common.entity_management.secrets_management import SecretsManagement


class AirflowApiClient(ApiClient):
    """
    Api client for Airflow
    Some api calls are version dependent on the underlying airflow instance version - some fields in the objects
    may not be approachable between different versions of airflow. When adding new calls, keep this in mind and
    validate in the documentation https://airflow.apache.org/docs/apache-airflow/stable/,
    if any change of the logic may differentiate based on the value of property airflow_instance_version.
    """

    def __init__(
        self,
        project_airflow_settings: dict,
        logger,
        secret_management: SecretsManagement = None,
        username=None,
        password=None,
    ):
        self.project_airflow_api_settings_details = project_airflow_settings[
            "apiAccess"
        ]
        self.secret_management = secret_management
        self.logger = logger
        self.airflow_instance_version = self.project_airflow_api_settings_details.get(
            "airflowVersion"
        )
        self._username = username
        self._password = password
        self._auth = None
        self.validate_airflow_instance_version()

    # pylint: disable=no-self-use
    # disabled no=self-use because this is abstract and mandatory method. And airflow API does not need
    # any special parameters which are taken from 'self' instance
    def _create_request_header(self, headers: dict, url: str) -> dict:
        """
        Create request header

        @return: dict of headers properties
        """
        return {"Content-Type": "application/json"}

    def validate_airflow_instance_version(self):
        """
        Validate airflow instance version, log warning if version is not supported
        """
        if self.airflow_instance_version not in ["2.4.0", "2.9.0"]:
            self.logger.warning(
                f"Airflow instance version {self.airflow_instance_version} is not supported,"
                f" so api operations on the instance may face issues."
            )

    @property
    def username(self) -> str:
        """
        Get username property

        @return: username property
        """
        return self._username

    @property
    def password(self) -> str:
        """
        Get password property

        @return: password property
        """
        return self._password

    @property
    def airflow_url(self) -> str:
        """
        Get airflow_url property

        @return: airflow_url property
        """
        airflow_host = self.project_airflow_api_settings_details["airflowHost"]
        if not airflow_host.startswith("http"):
            airflow_host = f"https://{airflow_host}"
        return airflow_host

    @property
    def auth(self) -> HTTPBasicAuth:
        """
        Get auth for API call

        @return: api HTTPBasicAuth
        """
        if not self._auth:
            self._init_api_credentials()
            self._auth = HTTPBasicAuth(self.username, self.password)
        return self._auth

    def _init_api_credentials(self) -> (str, str):
        """Gets the api credentials from secrets manager"""

        if not self._password and not self._username:
            self._username = self.project_airflow_api_settings_details["apiUsername"]
            self._password = self.secret_management.get_secret(
                self.project_airflow_api_settings_details["apiUserPassword"][
                    "secretName"
                ],
                get_values=True,
                check_permission=False,
            ).items.get(
                self.project_airflow_api_settings_details["apiUserPassword"][
                    "secretKey"
                ]
            )
        return self._username, self._password

    def trigger_dag_run(self, dag_id: str, run_conf_data: str) -> ApiObjectModel:
        """
        trigger dag run

        @param dag_id:
        @param run_conf_data
        @return: response from API call
        """
        return self._call_api(
            f"{self.airflow_url}/api/v1/dags/{dag_id}/dagRuns",
            "post",
            auth=self.auth,
            request_data=run_conf_data,
        )

    def get_dag_runs(
        self,
        dag_id: str,
        limit: int = None,
        order_by: str = None,
        offset: str = None,
        get_running: bool = False,
    ) -> ApiObjectModel:
        """
        Get dag runs

        @param dag_id: id of the dag
        @param limit: limit of entries. The numbers of items to return.
        @param offset: offset of entries. The number of items to skip before starting to collect the result set.
        @param order_by: The name of the field to order the results by.
        @param get_running: if true, only those with state running will be returned
        Prefix a field name with - to reverse the sort order.
        @return: response from API call
        """
        # passing limit as None does not matter
        uri_parameters = {"limit": limit}
        if offset:
            uri_parameters["offset"] = offset
        if order_by:
            uri_parameters["order_by"] = order_by
        # if true - by passing state equal to running we will obtain only running dags
        if get_running:
            uri_parameters["state"] = ["running"]
        return self._call_api(
            f"{self.airflow_url}/api/v1/dags/{dag_id}/dagRuns",
            "get",
            auth=self.auth,
            uri_parameters=uri_parameters,
        )

    def get_task_instances(
        self, dag_id: str, dag_run_id: str, limit: int = 500, offset: int = None
    ) -> ApiObjectModel:
        """
        Get task instances of dag run

        @param dag_id: id of the dag
        @param dag_run_id: id of the dag run
        @param limit: limit of entries. The numbers of items to return.
        @param offset: offset of entries. The number of items to skip before starting to collect the result set.
        Prefix a field name with - to reverse the sort order.
        @return: response from API call
        """
        uri_parameters = {"limit": limit}
        if offset:
            uri_parameters["offset"] = offset
        return self._call_api(
            f"{self.airflow_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
            "get",
            auth=self.auth,
            uri_parameters=uri_parameters,
        )

    def get_task_instance_logs(
        self, dag_id: str, dag_run_id: str, task_id: str, try_number: int = 1
    ) -> str:
        """
        Get log of task instance within one run

        @param dag_id: id of the dag
        @param dag_run_id: id of the dag run
        @param task_id: id of the task
        @param try_number: try number of the log

        @return: response from API call
        """
        response = self._call_api(
            f"{self.airflow_url}/api/v1/dags/{dag_id}/dagRuns/"
            f"{dag_run_id}/taskInstances/{task_id}/logs/{try_number}",
            "get",
            auth=self.auth,
            response_callback=lambda res: res.text,
        )
        return response.result

    def get_dag(self, dag_id: str) -> ApiObjectModel:
        """
        Get basic information about a DAG

        @param dag_id:
        @return: response from API call
        """
        return self._call_api(
            f"{self.airflow_url}/api/v1/dags/{dag_id}", "get", auth=self.auth
        )

    def delete_dag(self, dag_id: str) -> ApiObjectModel:
        """
        Delete airflow dag

        @param dag_id:
        @return: response from API call
        """
        return self._call_api(
            f"{self.airflow_url}/api/v1/dags/{dag_id}",
            "delete",
            auth=self.auth,
            response_callback=lambda res: res,
        )

    def pause_or_unpause_dag(
        self, dag_id: str, pause_flag: bool = False
    ) -> ApiObjectModel:
        """
        pause/unpause airflow dag

        @param dag_id:
        @param pause_flag:
        @return: response from API call
        """
        return self._call_api(
            f"{self.airflow_url}/api/v1/dags/{dag_id}",
            "patch",
            auth=self.auth,
            request_data={"is_paused": pause_flag},
            uri_parameters={"update_mask": "is_paused"},
        )

    def update_dag_schedule(self, variable_name: str, schedule: str) -> ApiObjectModel:
        """
        updates the dag schedule

        @param variable_name:
        @param schedule:
        @return: response from API call
        """
        return self._call_api(
            f"{self.airflow_url}/api/v1/variables/{variable_name}",
            "patch",
            auth=self.auth,
            request_data={"key": variable_name, "value": schedule},
        )

    def remove_variable(self, variable_name: str) -> ApiObjectModel:
        """
        remove variable

        @param variable_name:
        @return: response from API call
        """
        try:
            return self._call_api(
                f"{self.airflow_url}/api/v1/variables/{variable_name}",
                "delete",
                auth=self.auth,
                response_callback=lambda res: res,
            )
        except NotFoundError:
            # if variable does not exist then ignore this and continue
            return None

    def stop_dag_run(self, dag_id: str, dag_run_id: str, state: str) -> ApiObjectModel:
        """
        Stop dag run and mark it as given state

        @param dag_id:
        @param dag_run_id:
        @param state:
        @return: response from API call
        """
        return self._call_api(
            f"{self.airflow_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}",
            "patch",
            auth=self.auth,
            request_data={"state": state},
        )

    def create_http_connection(
        self, connection_id: str, host: str, login: str, password: str
    ) -> Optional[ApiObjectModel]:
        """
        Create new http connection in airflow

        @param connection_id: id of connection
        @param host: host
        @param login: login
        @param password: password
        @return: response from API call
        """
        try:
            return self._call_api(
                f"{self.airflow_url}/api/v1/connections",
                "post",
                auth=self.auth,
                request_data={
                    "connection_id": connection_id,
                    "conn_type": "http",
                    "host": host,
                    "login": login,
                    "password": password,
                },
            )
        except ConnectionError as exception:
            if "status_code=403" in exception.args[0]:
                # do not raise exception
                # Permissions to update airflow pools might be limited on some airflow instances
                self.logger.error(
                    f"Could not create http connection {connection_id}. "
                    f"Due to missing permissions. Skipping creation of the connection_id."
                )
                self.logger.error(exception)
            else:
                raise
        return None

    def get_connection(
        self, connection_id: str, raise_no_data_error: bool = True
    ) -> ApiObjectModel:
        """
        Get connection

        @param connection_id: id of connection
        @param raise_no_data_error: flag indicate if raise error if connection does not exists

        @return: response from API call
        """
        try:
            return self._call_api(
                f"{self.airflow_url}/api/v1/connections/{connection_id}",
                "get",
                auth=self.auth,
            )
        except NotFoundError:
            if raise_no_data_error:
                raise
            return None

    def get_pool(self, pool_name: str, raise_error: bool = False) -> ApiObjectModel:
        """
        Get pool

        @param pool_name: name of pool
        @param raise_error: bool, if true raise error if pool does not exist
        @return: response from API call
        """
        try:
            return self._call_api(
                f"{self.airflow_url}/api/v1/pools/{pool_name}", "get", auth=self.auth
            )
        except NotFoundError as exc:
            self.logger.info(f"Pool with name {pool_name} does not exist.")
            if raise_error:
                raise NotFoundError(
                    f"Pool with name {pool_name} was not found in the corresponding airflow instance"
                ) from exc
        return None

    def create_pool(self, pool_name: str, pool_slots: int) -> ApiObjectModel:
        """
        Create pool

        @param pool_name: name of pool
        @param pool_slots: number of slots
        @return: response from API call
        """
        return self._call_api(
            f"{self.airflow_url}/api/v1/pools",
            "post",
            auth=self.auth,
            request_data={"name": pool_name, "slots": pool_slots},
        )