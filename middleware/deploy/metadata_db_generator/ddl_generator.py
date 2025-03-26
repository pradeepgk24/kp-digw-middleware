from middleware.deploy.metadata_db_generator.db_component_generator import DBComponentGenerator
from middleware.common.metadatabase.connectors.difw_metadb_connector import DifwMetadbConnector
from middleware.common.metadatabase.model.difw_metadb_model import Base, BaseTableModel


class DDLGenerator(DBComponentGenerator):
    """
    Class for generation of tables and whole DB structure
    """

    def __init__(self, args):
        super().__init__(args)
        self.db_connector = DifwMetadbConnector(self.logger)

    def generate(self, *args):
        """
        Main generate method
        :return:
        """
        self.logger.info("Going to regenerate DB structures")
        self._create_schema(
            self.metadb_configuration.get("dbSecretManagerCredentialStorage", "difw-metadb-ui-credentials"),
            self.args.recreate_database)

    def _create_schema(self, secret_manager_connection: str, recreate_database: bool):
        self.db_connector.init_connection_engine(secret_manager_connection, self.api_sm_client)
        if recreate_database:
            BaseTableModel.drop_tables_if_not_exists(self.db_connector.connector_engine)
        Base.metadata.create_all(self.db_connector.connector_engine)