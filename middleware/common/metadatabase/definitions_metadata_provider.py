from functools import lru_cache

from sqlalchemy import and_, text

from middleware.common.metadatabase.clients.meta_database_client import MetaDatabaseClient
from middleware.common.metadatabase.model.difw_metadb_model import DifwCoreVersions, ComponentTypes, \
    PermissionActionTypes, Enumerators
from middleware.common.metadatabase.model.types.component_type_categories_enum import ComponentTypeCategoriesEnum


class DefinitionsMetadataProvider(MetaDatabaseClient):
    """
    Database client which served actions related with metadata
    """

    def __init__(self, logger, secret_manager_connection, lambda_secrets_manager):
        super().__init__(logger, secret_manager_connection, lambda_secrets_manager)

    def add_framework_version(self, framework_version: str, user_id: str, is_latest: bool = True):
        """
        Creates secrets in MetaDB.

        :param framework_version:
        :param is_latest:
        :param user_id:
        :return:
        """
        self.insert_record(
            DifwCoreVersions(
                DIFW_CORE_VERSION=framework_version,
                IS_ENABLED=True,
                IS_LATEST=is_latest),
            user_id)

    def update_framework_version(self, framework_version: DifwCoreVersions, user_id: str):
        """
        Get latest FRAMEWORK VERSION
        :return:
        """
        self.update_record(framework_version, user_id)

    def insert_or_update_component_type(self, component_type: ComponentTypes, user_id: str):
        """
        Create or update component type object
        :param component_type: object to add or update
        :param user_id

        :return: created or updated record registered in session
        """
        return self.insert_or_update_record(component_type, user_id)

    def insert_or_update_permission_action_type(self, permission_action_type: PermissionActionTypes, user_id: str):
        """
        Create or update permission action type object
        :param permission_action_type: object to add or update
        :param user_id

        :return: created or updated record registered in session
        """
        return self.insert_or_update_record(permission_action_type, user_id)

    def get_latest_framework_version(self):
        """
        Get latest FRAMEWORK VERSION
        :return:
        """
        self.logger.info("Going to retrieve latest FW version")
        # pylint: disable=singleton-comparison
        core_version = DifwCoreVersions.get_many(self.session, and_(DifwCoreVersions.IS_LATEST == True))
        if len(core_version) > 1:
            raise Exception(
                "There is more than 2 records in table FRAMEWORK_VERSION with the latest flag equal to true")
        if core_version:
            return core_version[0]
        return None

    def get_components_type_by_category(self, user_id: str, component_category: ComponentTypeCategoriesEnum,
                                        difw_core_version: str):
        """
        Gets component type

        :param component_category:
        :param difw_core_version:
        :param user_id: logon user isid
        :return:
        """
        self.logger.info(
            f"User {user_id} going to get component types of category {component_category} "
            f"and core version {difw_core_version}")
        # adding filter on component category field only if it is sent from request , if not filter the query
        # only on basis of difw core version to get all the types of components that are valid for the inputted difw
        # core version
        # last param in get_many is for ordering, we are passing it arguments in as list
        if component_category is not None:
            return ComponentTypes.get_many(self.session,
                                           and_(ComponentTypes.COMPONENT_TYPE_CATEGORY == component_category,
                                                ComponentTypes.DIFW_CORE_VERSION == difw_core_version),
                                           [ComponentTypes.COMPONENT_TYPE_NAME])
        return ComponentTypes.get_many(self.session, and_(ComponentTypes.DIFW_CORE_VERSION == difw_core_version),
                                       [ComponentTypes.COMPONENT_TYPE_NAME])

    def get_component_type(self, user_id: str, component_category: ComponentTypeCategoriesEnum, component_type: str,
                           difw_core_version: str):
        """
        Gets component type

        :param component_category:
        :param component_type:
        :param difw_core_version:
        :param user_id: logon user isid
        :return:
        """
        self.logger.info(
            f"User {user_id} going to get component type of category {component_category} , type {component_type}"
            f"and core version {difw_core_version}")
        return ComponentTypes(COMPONENT_TYPE_NAME=component_type, COMPONENT_TYPE_CATEGORY=component_category,
                              DIFW_CORE_VERSION=difw_core_version).get_unique(self.session)

    @lru_cache
    def get_all_permission_action_types(self, user_id: str):
        """
        Get all permission action types

        :param user_id: logon user isid
        :return:
        """
        self.logger.info(f"User {user_id} going to get all permission action types")
        return PermissionActionTypes.get_many(self.session)

    @lru_cache
    def get_all_framework_versions(self, user_id: str):
        """
        Get all framework_versions

        :param user_id: logon user isid
        :return: list of framework versions
        """
        self.logger.info(f"User {user_id} going to get all framework versions which are enabled")
        # pylint: disable=singleton-comparison
        return DifwCoreVersions.get_many(self.session, and_(DifwCoreVersions.IS_ENABLED == True))

    def get_enumerator_values(self, enumerator_category: str, user_id: str):
        """
        Get enumerator options based on passed enumerator type name
        :param enumerator_category: enum category of which we want to collect values of from DB
        :param user_id: logon user isid
        :return: stringed list of enum values
        """
        self.logger.info(f"User {user_id} going to get enumerator values for enumerator category {enumerator_category}")
        return Enumerators.get_many(self.session, and_(Enumerators.ENUMERATOR_CATEGORY == enumerator_category))

    def insert_or_update_enumerator_entry(self, enumerator: Enumerators, user_id: str):
        """
        Create or update component type object, as of now this method is used only while running the generation of DB
        :param enumerator: object to add or update
        :param user_id:

        :return: created or updated record registered in session
        """
        return self.insert_or_update_record(enumerator, user_id)

    def get_pipelines_object_metadata(self, user_id: str, group_id: str, project_id: str) -> list[dict]:
        """
        Get pipeline objects metadata
        Each objects metadata is dag trigger operator with proper dag id and proper secret key and access key

        @param user_id:
        @param group_id:
        @param project_id:

        @return: list of dictionaries as a result from procedure pipelines_object_metadata
        """
        result = []
        fetched_rows = self.session.execute(
            text(f"select * from pipelines_object_metadata('{user_id}', '{group_id}', '{project_id}')")).fetchall()
        for row in fetched_rows:
            # pylint: disable=protected-access
            result.append(dict(row._mapping))
        self.session.close()
        return result
