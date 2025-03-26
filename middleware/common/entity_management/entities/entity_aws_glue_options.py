from middleware.common.entity_management.entities.entity_object import EntityObject


class EntityAwsGlueOptions(EntityObject):
    """
    Class of aws glue options entity
    """

    def __init__(self, number_of_workers: int = None, worker_type: str = None, autoscaling: bool = None,
                 spark_configuration: dict = None, java_system_properties: dict = None,
                 spark_sql_configuration: dict = None, max_tags_count: int = None, subnet_id: str = None,
                 resources_bucket: str = None, data_bucket: str = None, security_groups: list = None):
        self._number_of_workers = number_of_workers
        self._worker_type = worker_type
        self._autoscaling = autoscaling
        self._spark_configuration = spark_configuration
        self._java_system_properties = java_system_properties
        self._spark_sql_configuration = spark_sql_configuration
        self._max_tags_count = max_tags_count
        self._subnet_id = subnet_id
        self._resources_bucket = resources_bucket
        self._data_bucket = data_bucket
        self._security_groups = security_groups

    @property
    def number_of_workers(self) -> int:
        """
        Get number_of_workers.

        :return: number_of_workers
        """
        return self._number_of_workers

    def set_number_of_workers(self, number_of_workers):
        """
        Set new value of number_of_workers

        :param number_of_workers: new value number_of_workers
        """
        self._number_of_workers = number_of_workers

    @property
    def worker_type(self) -> str:
        """
        Get worker_type.

        :return: worker_type
        """
        return self._worker_type

    def set_worker_type(self, worker_type):
        """
        Set new value of worker_type

        :param worker_type: new value worker_type
        """
        self._worker_type = worker_type

    @property
    def autoscaling(self) -> bool:
        """
        Get autoscaling

        :return: autoscaling
        """
        return self._autoscaling

    def set_autoscaling(self, autoscaling):
        """
        Set new value of autoscaling

        :param autoscaling: new value autoscaling
        """
        self._autoscaling = autoscaling

    @property
    def spark_configuration(self) -> dict:
        """
        Get spark_configuration.

        :return: spark_configuration
        """
        return self._spark_configuration

    def set_spark_configuration(self, spark_configuration):
        """
        Set new value of spark_configuration

        :param spark_configuration: new value spark_configuration
        """
        self._spark_configuration = spark_configuration

    @property
    def java_system_properties(self) -> dict:
        """
        Get java_system_properties.

        :return: java_system_properties
        """
        return self._java_system_properties

    def set_java_system_properties(self, java_system_properties):
        """
        Set new value of java_system_properties

        :param java_system_properties: new value java_system_properties
        """
        self._java_system_properties = java_system_properties

    @property
    def spark_sql_configuration(self) -> dict:
        """
        Get project spark_sql_configuration.

        :return: spark_sql_configuration
        """
        return self._spark_sql_configuration

    def set_spark_sql_configuration(self, spark_sql_configuration):
        """
        Set new value of spark_sql_configuration

        :param spark_sql_configuration: new value spark_sql_configuration
        """
        self._spark_sql_configuration = spark_sql_configuration

    @property
    def max_tags_count(self) -> int:
        """
        Get max_tags_count.

        :return: max_tags_count
        """
        return self._max_tags_count

    def set_max_tags_count(self, max_tags_count):
        """
        Set new value of max_tags_count

        :param max_tags_count: new value max_tags_count
        """
        self._max_tags_count = max_tags_count

    @property
    def subnet_id(self) -> str:
        """
        Get subnet_id.

        :return: subnet_id
        """
        return self._subnet_id

    @property
    def resources_bucket(self) -> str:
        """
        Get resources_bucket.

        :return: resources_bucket
        """
        return self._resources_bucket

    @property
    def data_bucket(self) -> str:
        """
        Get data_bucket.

        :return: data_bucket
        """
        return self._data_bucket

    @property
    def security_groups(self) -> str:
        """
        Get security_groups.

        :return: security_groups
        """
        return self._security_groups if self._security_groups else []

    @staticmethod
    def from_json_dict(aws_glue_options: dict):
        """
        Create class instance from model/dict/request
        """
        return EntityAwsGlueOptions(
            number_of_workers=aws_glue_options.get("numberOfWorkers"),
            worker_type=aws_glue_options.get("workerType"),
            autoscaling=aws_glue_options.get("autoscaling"),
            spark_configuration=aws_glue_options.get("sparkConfiguration", {}),
            spark_sql_configuration=aws_glue_options.get("sparkSqlConfiguration", {}),
            java_system_properties=aws_glue_options.get("javaSystemProperties", {}),
            max_tags_count=aws_glue_options.get("maxTagsCount"),
            subnet_id=aws_glue_options.get("subnetId"),
            resources_bucket=aws_glue_options.get("resourcesBucket"),
            data_bucket=aws_glue_options.get("dataBucket"),
            security_groups=aws_glue_options.get("securityGroups", [])
        )

    def to_json_dict(self):
        """
        return json definition of EntityAwsGlueOptions

        :return: json object of EntityAwsGlueOptions
        """
        json_dict = {}
        if self.number_of_workers:
            json_dict["numberOfWorkers"] = self.number_of_workers
        if self.worker_type:
            json_dict["workerType"] = self.worker_type
        if self.autoscaling is not None:
            json_dict["autoscaling"] = self.autoscaling
        if self.spark_configuration:
            json_dict["sparkConfiguration"] = self.spark_configuration
        if self.java_system_properties:
            json_dict["javaSystemProperties"] = self.java_system_properties
        if self.spark_sql_configuration:
            json_dict["sparkSqlConfiguration"] = self.spark_sql_configuration
        if self.max_tags_count:
            json_dict["maxTagsCount"] = self.max_tags_count
        if self.subnet_id:
            json_dict["subnetId"] = self.subnet_id
        if self.resources_bucket:
            json_dict["resourcesBucket"] = self.resources_bucket
        if self.data_bucket:
            json_dict["dataBucket"] = self.data_bucket
        if self.security_groups:
            json_dict["securityGroups"] = self.security_groups
        return json_dict
