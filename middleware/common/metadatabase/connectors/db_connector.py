import logging
from abc import abstractmethod

from common.helpers.exception import ConfigurationError
from common.secrets.secrets_manger import SecretsManager


class DBConnector:
    """
    Database Base Class
    """

    def __init__(self, logger):
        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    @abstractmethod
    def init_connection_engine(self, secret_manager_connection, lambda_secrets_manager: SecretsManager):
        """
        Init new connection engine

        :param secret_manager_connection:
        :param lambda_secrets_manager:
        :return: N/A
        """

    @staticmethod
    def _validate_secret_manager_values(sm_values, secret_manager_name, key_prefix=""):
        """
        Validate if values from secret manager contains all keys which are needed for establishing of connection

        :param sm_values: dict of SM values
        :param secret_manager_name: name of secret manager where connection details are stored
        :param key_prefix: prefix for all keys
        :return: N/A
        """
        if not all([connection_param in sm_values for connection_param in
                    [f"{key_prefix}user", f"{key_prefix}host", f"{key_prefix}port", f"{key_prefix}password",
                     f"{key_prefix}database"]]):
            raise ConfigurationError(f"The secret manager '{secret_manager_name}' has to contains all of the "
                                     f"following keys: '{key_prefix}user', '{key_prefix}host', '{key_prefix}port', "
                                     f"'{key_prefix}password', '{key_prefix}database'")
