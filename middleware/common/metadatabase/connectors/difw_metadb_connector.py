from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from common.secrets.secrets_manger import SecretsManager

from middleware.common.metadatabase.connectors.db_connector import DBConnector


class DifwMetadbConnector(DBConnector):
    """
    Database client for DIFW metadb
    """

    def __init__(self, logger):
        super().__init__(logger)
        self._connector_engine = None

    def init_connection_engine(self, secret_manager_connection, lambda_secrets_manager: SecretsManager):
        """
        Creates the DB connection to DIFW meta DB using sqlalchemy

        :param secret_manager_connection: secret manager name where DIFW meta DB credentials are stored
        :param lambda_secrets_manager: lambda secret manager
        :return: new DIFW meta DB connection
        """
        metadata_connection = lambda_secrets_manager.get_secret_string_data(secret_manager_connection)
        if metadata_connection is None:
            raise Exception(f"There is no SM with name {secret_manager_connection} with DB credentials")
        self._validate_secret_manager_values(metadata_connection, secret_manager_connection)
        self.logger.info(
            f"Going to connect to DIFW meta DB using sql alchemy"
            f"{metadata_connection['host']}:{metadata_connection['port']}/{metadata_connection['database']}... ")

        conn_string = f"postgresql+psycopg2://{metadata_connection['user']}:{metadata_connection['password']}@" \
                      f"{metadata_connection['host']}:{metadata_connection['port']}/{metadata_connection['database']}"
        # in case of development purpose, add parameter echo=True
        self._connector_engine = create_engine(conn_string)
        return self._connector_engine

    def create_new_session(self):
        """
        Create new DB session
        """
        return scoped_session(sessionmaker(bind=self._connector_engine))


    @property
    def connector_engine(self):
        """
        Get connector engine
        """
        return self._connector_engine
