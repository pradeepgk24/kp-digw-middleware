from middleware.common.entity_management.entities.entity_object import EntityObject


class EntityAwsAccountStorage(EntityObject):
    """
    Entity AWS Account storage
    """

    def __init__(self, assume_role: str = None, service_user_access_key_sn: str = None,
                 service_user_access_key_sk: str = None, service_user_secret_key_sn: str = None,
                 service_user_secret_key_sk: str = None):
        self._assume_role = assume_role
        self._service_user_access_key_sn = service_user_access_key_sn
        self._service_user_access_key_sk = service_user_access_key_sk
        self._service_user_secret_key_sn = service_user_secret_key_sn
        self._service_user_secret_key_sk = service_user_secret_key_sk

    @property
    def service_user_access_key_sn(self) -> str:
        """
        Get service_user_access_key_sn.

        :return: service_user_access_key_sn
        """
        return self._service_user_access_key_sn

    def set_service_user_access_key_sn(self, service_user_access_key_sn):
        """
        Set new value of service_user_access_key_sn

        :param service_user_access_key_sn: new value of service_user_access_key_sn
        """
        self._service_user_access_key_sn = service_user_access_key_sn

    @property
    def service_user_access_key_sk(self) -> str:
        """
        Get service_user_access_key_sk.

        :return: service_user_access_key_sk
        """
        return self._service_user_access_key_sk

    def set_service_user_access_key_sk(self, service_user_access_key_sk):
        """
        Set new value of service_user_access_key_sk

        :param service_user_access_key_sk: new value of service_user_access_key_sk
        """
        self._service_user_access_key_sk = service_user_access_key_sk

    @property
    def service_user_secret_key_sn(self) -> str:
        """
        Get service_user_secret_key_sn.

        :return: service_user_secret_key_sn
        """
        return self._service_user_secret_key_sn

    def set_service_user_secret_key_sn(self, service_user_secret_key_sn):
        """
        Set new value of service_user_secret_key_sn

        :param service_user_secret_key_sn: new value service_user_secret_key_sn
        """
        self._service_user_secret_key_sn = service_user_secret_key_sn

    @property
    def service_user_secret_key_sk(self) -> str:
        """
        Get service_user_secret_key_sk.

        :return: service_user_secret_key_sk
        """
        return self._service_user_secret_key_sk

    def set_service_user_secret_key_sk(self, service_user_secret_key_sk):
        """
        Set new value of service_user_secret_key_sk

        :param service_user_secret_key_sk: new value service_user_secret_key_sk
        """
        self._service_user_secret_key_sk = service_user_secret_key_sk

    @property
    def assume_role(self) -> str:
        """
        Get assume_role.

        :return: assume_role
        """
        return self._assume_role

    def set_assume_role(self, assume_role):
        """
        Set new value of assume_role

        :param assume_role: new value assume_role
        """
        self._assume_role = assume_role

    @staticmethod
    def from_json_dict(aws_account_storage: dict):
        """
        Create class instance from model/dict/request
        """
        return EntityAwsAccountStorage(
            service_user_access_key_sn=aws_account_storage.get("awsServiceUser", {}).get("accessKey", {}).get(
                "secretName"),
            service_user_access_key_sk=aws_account_storage.get("awsServiceUser", {}).get("accessKey", {}).get(
                "secretKey"),
            service_user_secret_key_sn=aws_account_storage.get("awsServiceUser", {}).get("secretKey", {}).get(
                "secretName"),
            service_user_secret_key_sk=aws_account_storage.get("awsServiceUser", {}).get("secretKey", {}).get(
                "secretKey"),
            assume_role=aws_account_storage.get("awsAssumedRole")
        )

    def to_json_dict(self):
        """
        return json definition of EntityAwsAccountStorage

        :return: json object of EntityAwsAccountStorage
        """
        json_dict = {}
        # as it is possible that only one may be populated during creation in drafted status we use or
        if self.service_user_access_key_sn or self.service_user_secret_key_sn:
            json_dict["awsServiceUser"] = {
                "accessKey": {
                    "secretName": self.service_user_access_key_sn,
                    "secretKey": self.service_user_access_key_sk
                },
                "secretKey": {
                    "secretName": self.service_user_secret_key_sn,
                    "secretKey": self.service_user_secret_key_sk
                }
            }
        if self.assume_role:
            json_dict["awsAssumedRole"] = self.assume_role
        return json_dict
