from middleware.common.entity_management.entities.entity_object import EntityObject


class EntityDatabricksOptions(EntityObject):
    """
    Class of databricks options entity
    """

    def __init__(self, dbx_acl: [dict] = None, dbx_acl_user: [dict] = None, dbx_acl_group: [dict] = None,
                 job_cluster_options: dict = None, all_purpose_cluster_id: str = None,
                 all_purpose_cluster_name: str = None, all_purpose_cluster_validate: bool = False,
                 data_bucket: str = None, resources_bucket: str = None, security_api_token_secret_name: str = None,
                 security_api_token_secret_key: str = None, cluster_options_format: str = None,
                 max_tags_count: int = None):
        self._dbx_acl = dbx_acl
        self._dbx_acl_user = dbx_acl_user
        self._dbx_acl_group = dbx_acl_group
        self._job_cluster_options = job_cluster_options
        self._all_purpose_cluster_id = all_purpose_cluster_id
        self._all_purpose_cluster_name = all_purpose_cluster_name
        self._all_purpose_cluster_validate = all_purpose_cluster_validate
        self._data_bucket = data_bucket
        self._resources_bucket = resources_bucket
        self._security_api_token_secret_name = security_api_token_secret_name
        self._security_api_token_secret_key = security_api_token_secret_key
        self._cluster_options_format = cluster_options_format
        self._max_tags_count = max_tags_count

    @property
    def dbx_acl(self) -> [dict]:
        """
        Get dbx_acl.

        :return: dbx_acl
        """
        if not self._dbx_acl:
            return []
        return self._dbx_acl

    def set_dbx_acl(self, dbx_acl):
        """
        Set new value of dbx_acl

        :param dbx_acl: new value dbx_acl
        """
        self._dbx_acl = dbx_acl

    @property
    def dbx_acl_user(self) -> [dict]:
        """
        Get dbx_acl_user.

        :return: dbx_acl_user
        """
        if not self._dbx_acl_user:
            return []
        return self._dbx_acl_user

    def set_dbx_acl_user(self, dbx_acl_user):
        """
        Set new value of dbx_acl_user

        :param dbx_acl_user: new value dbx_acl_user
        """
        self._dbx_acl_user = dbx_acl_user

    @property
    def dbx_acl_group(self) -> [dict]:
        """
        Get dbx_acl_group.

        :return: dbx_acl_group
        """
        if not self._dbx_acl_group:
            return []
        return self._dbx_acl_group

    def set_dbx_acl_group(self, dbx_acl_group):
        """
        Set new value of dbx_acl_group

        :param dbx_acl_group: new value dbx_acl_group
        """
        self._dbx_acl_group = dbx_acl_group

    @property
    def job_cluster_options(self):
        """
        Get job_cluster_options. Can be dict or string,
        it is dict if the declaration was json, is string if the declaration was coming from yaml

        :return: job_cluster_options
        """
        return self._job_cluster_options

    def set_job_cluster_options(self, job_cluster_options):
        """
        Set new value of job_cluster_options

        :param job_cluster_options: new value job_cluster_options
        """
        self._job_cluster_options = job_cluster_options

    @property
    def all_purpose_cluster_id(self) -> str:
        """
        Get all_purpose_cluster_id.

        :return: all_purpose_cluster_id
        """
        return self._all_purpose_cluster_id

    def set_all_purpose_cluster_id(self, all_purpose_cluster_id):
        """
        Set new value of all_purpose_cluster_id

        :param all_purpose_cluster_id: new value all_purpose_cluster_id
        """
        self._all_purpose_cluster_id = all_purpose_cluster_id

    @property
    def all_purpose_cluster_name(self) -> str:
        """
        Get all_purpose_cluster_name.

        :return: all_purpose_cluster_name
        """
        return self._all_purpose_cluster_name

    def set_all_purpose_cluster_name(self, all_purpose_cluster_name):
        """
        Set new value of all_purpose_cluster_name

        :param all_purpose_cluster_name: new value all_purpose_cluster_name
        """
        self._all_purpose_cluster_name = all_purpose_cluster_name

    @property
    def all_purpose_cluster_validate(self) -> bool:
        """
        Get all_purpose_cluster_validate.

        :return: all_purpose_cluster_validate
        """
        return self._all_purpose_cluster_validate

    def set_all_purpose_cluster_validate(self, all_purpose_cluster_validate):
        """
        Set new value of all_purpose_cluster_validate

        :param all_purpose_cluster_validate: new value all_purpose_cluster_validate
        """
        self._all_purpose_cluster_validate = all_purpose_cluster_validate

    @property
    def data_bucket(self) -> str:
        """
        Get data_bucket.

        :return: data_bucket
        """
        return self._data_bucket

    @property
    def resources_bucket(self) -> str:
        """
        Get resources_bucket.

        :return: resources_bucket
        """
        return self._resources_bucket

    @property
    def security_api_token_secret_name(self) -> str:
        """
        Get security_api_token_secret_name.

        :return: security_api_token_secret_name
        """
        return self._security_api_token_secret_name

    @property
    def security_api_token_secret_key(self) -> str:
        """
        Get security_api_token_secret_key.

        :return: security_api_token_secret_key
        """
        return self._security_api_token_secret_key

    @property
    def cluster_options_format(self) -> str:
        """
        Get cluster_options_format.

        :return: cluster_options_format
        """
        return self._cluster_options_format

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


    @staticmethod
    def from_json_dict(aws_dbx_options: dict):
        """
        Create class instance from model/dict/request
        """
        # need to keep all given acl in the dbx advanced options
        # aclGroup and alcUser will be passed in from UI
        # base acl is there for compatibility with old versions
        return EntityDatabricksOptions(
            dbx_acl=aws_dbx_options.get("acl"),
            dbx_acl_user=aws_dbx_options.get("aclUser"),
            dbx_acl_group=aws_dbx_options.get("aclGroup"),
            job_cluster_options=aws_dbx_options.get("jobCluster", {}).get("clusterOptions", {}),
            all_purpose_cluster_id=aws_dbx_options.get("allPurposeCluster", {}).get("clusterId"),
            all_purpose_cluster_name=aws_dbx_options.get("allPurposeCluster", {}).get("clusterName"),
            all_purpose_cluster_validate=aws_dbx_options.get("allPurposeCluster", {}).get("validateCluster", False),
            data_bucket=aws_dbx_options.get("awsS3DataBucket"),
            resources_bucket=aws_dbx_options.get("awsS3ResourcesBucket"),
            security_api_token_secret_name=aws_dbx_options.get("securityApiToken", {}).get("secretName"),
            security_api_token_secret_key=aws_dbx_options.get("securityApiToken", {}).get("secretKey"),
            cluster_options_format=aws_dbx_options.get("jobCluster", {}).get('clusterOptionsFormat'),
            max_tags_count=aws_dbx_options.get("maxTagsCount"),
        )

    def to_json_dict(self) -> dict:
        """
        return json definition of EntityDatabricksOptions

        :return: json object of EntityDatabricksOptions
        """
        json_dict = {}
        if self.max_tags_count:
            json_dict["maxTagsCount"] = self.max_tags_count
        if self.dbx_acl:
            json_dict["acl"] = self.dbx_acl
        if self.dbx_acl_user:
            json_dict["aclUser"] = self.dbx_acl_user
        if self.dbx_acl_group:
            json_dict["aclGroup"] = self.dbx_acl_group
        if self.job_cluster_options:
            json_dict["jobCluster"] = {}
            json_dict["jobCluster"]["clusterOptionsFormat"] = self.cluster_options_format
            json_dict["jobCluster"].update({"clusterOptions": self.job_cluster_options})
        if self.all_purpose_cluster_name or self.all_purpose_cluster_id:
            json_dict["allPurposeCluster"] = {
                "clusterId": self.all_purpose_cluster_id,
                "clusterName": self.all_purpose_cluster_name,
                "validateCluster": self.all_purpose_cluster_validate
            }
        if self.data_bucket:
            json_dict["awsS3DataBucket"] = self.data_bucket
        if self.resources_bucket:
            json_dict["awsS3ResourcesBucket"] = self.resources_bucket
        if self.security_api_token_secret_name and self.security_api_token_secret_key:
            json_dict["securityApiToken"] = {
                "secretName": self.security_api_token_secret_name,
                "secretKey": self.security_api_token_secret_key
            }
        return json_dict

