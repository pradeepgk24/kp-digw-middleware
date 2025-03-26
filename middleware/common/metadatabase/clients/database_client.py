import logging
from common.secrets.secrets_manger import SecretsManager

class DatabaseClient:
    """
    General DB client
    """

    def __init__(self, logger, secret_manager_connection, lambda_secrets_manager: SecretsManager):
        self._secret_manager_connection = secret_manager_connection
        self._lambda_secrets_manager = lambda_secrets_manager
        self.logger = logging.getLogger(__name__) if not logger else logger


