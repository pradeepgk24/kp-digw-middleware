from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.helpers.exception import NoDataError, AuthorizationError
from middleware.common.entity_management.entities.enitity_enumerator import EntityEnumerator
from middleware.common.entity_management.entities.entity_component_type import EntityComponentType
from middleware.common.entity_management.entities.entity_difw_core_versions import EntityDifwCoreVersions
from middleware.common.entity_management.entities.entity_permission_action_type import EntityPermissionActionType
from middleware.common.entity_management.entity_management import EntityManagement
from middleware.common.metadatabase.definitions_metadata_provider import DefinitionsMetadataProvider
from middleware.common.metadatabase.model.types.component_type_categories_enum import ComponentTypeCategoriesEnum
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.security.action_type import ActionType
from middleware.common.entity_management.entities.entity_acl import EntityACL


class DefinitionsMetadataManagement(EntityManagement):
    """
    Metadata management
    """

    # pylint: disable=too-many-arguments
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._definitions_metadata_provider = None
        self._secret_management = None

    @property
    def definitions_metadata_provider(self):
        """
        definitions_metadata_provider property
        """
        if self._definitions_metadata_provider is None:
            self._definitions_metadata_provider = DefinitionsMetadataProvider(self.logger,
                                                                              self.metadatabase_connection,
                                                                              self.lambda_secrets_manager)
        return self._definitions_metadata_provider

    @staticmethod
    def _filter_metadata_by_platform(metadata, platform: str = None):
        """
        Filter metadata by platform

        :param metadata:
        :param platform:
        @return: filtered metadata
        """
        if platform:
            metadata_result = []
            for metadata_item in metadata:
                # if platform is not defined in definition then by default it belongs to all platforms so default
                # platform dict will contains the target platform
                if platform in metadata_item.definition.get('platforms', {platform: {}}):
                    metadata_result.append(metadata_item)
            return metadata_result
        return metadata

    def get_component_types(self, platform: str, difw_core_version: str, component_category: str = None) -> \
            [EntityComponentType]:
        """
        Get component types

        :param component_category:
        :param platform:
        :param difw_core_version:

        @return: list of EntityComponentTypes
        """
        component_category = ComponentTypeCategoriesEnum.from_str(component_category)
        if component_category == ComponentTypeCategoriesEnum.pipeline_object:
            # there is no permission restrictions for pipeline objects. There are restrictions for pipeline itself
            return self._resolve_pipeline_objects_metadata(difw_core_version)
        # regular metadata from DB
        # this is list of component types, which user has permission to see
        allowed_component_types = []
        db_results = self.definitions_metadata_provider.get_components_type_by_category(
            self.user_isid, component_category, difw_core_version)
        raw_entity_component_types = EntityComponentType.from_metadb_objects(db_results)
        for entity_component_type in raw_entity_component_types:
            if self.auth_validator.validate(
                    ActionType.USE_COMPONENT,
                    {"componentTypeName": entity_component_type.component_type_name,
                     "componentCategory": entity_component_type.component_category.value}) == \
                    PermissionEffectsEnum.allow:
                # if there is any custom resolver of metadata then use it
                if hasattr(self, f"_custom_resolving_{entity_component_type.component_category.value}"
                                 f"_{entity_component_type.component_type_name}"):
                    entity_component_type = getattr(
                        self,
                        f"_custom_resolving_{entity_component_type.component_category.value}"
                        f"_{entity_component_type.component_type_name}")(
                        **{"component_metadata": entity_component_type})
                allowed_component_types.append(entity_component_type)
        return self._filter_metadata_by_platform(allowed_component_types, platform)

    # pylint: disable=import-outside-toplevel,cyclic-import
    def _custom_resolving_input_connector_local_file(
            self, component_metadata: EntityComponentType
    ) -> EntityComponentType:
        """
        Custom resolve of local file metadata

        @param component_metadata:local file metadata

        @return enhanced local file metadata of type EntityComponentType
        """
        # we are doing local import because of avoiding of circular import
        from middleware.common.entity_management.project_settings_management import ProjectSettingsManagement
        project_settings_management = ProjectSettingsManagement(
            logger=self.logger, metadatabase_connection=self.metadatabase_connection,
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)
        aws_account_settings = project_settings_management.get_project_account_settings(
            account_type=ProjectAccountTypesEnum.aws,
            check_permission=False,
            raise_not_found_error=False
        )
        if aws_account_settings:
            file_attribute_type = component_metadata.definition['attributes'][0]['type']
            if "s3Browsing" not in file_attribute_type:
                file_attribute_type["s3Browsing"] = {}
            file_attribute_type["s3Browsing"]["relatedS3BrowserAttrValue"] = \
                aws_account_settings.account_details['dataBucket']
        return component_metadata

    # disable intern import error to prevent cyclic dependencies
    # pylint: disable=import-outside-toplevel,cyclic-import
    def _resolve_pipeline_objects_metadata(self, difw_core_version: str) -> [EntityComponentType]:
        """
        Resolve pipeline objects metadata

        @param difw_core_version: version of core

        @return: list of EntityComponentType
        """
        # do the inner import to avoid cross dependency issue
        from middleware.common.entity_management.project_settings_management import ProjectSettingsManagement
        project_settings_management = ProjectSettingsManagement(
            logger=self.logger, metadatabase_connection=self.metadatabase_connection,
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)
        # load dag trigger operator from DB
        trigger_operator_template = self.get_component_type("airflow_component", "dag_trigger", difw_core_version)
        # to avoid the calling of multiple airflow API calls, then save the intermediate results into this variable
        connections_buffer = {}
        # get component type as a pipeline object from DB
        db_pipeline_objects_metadata = self.definitions_metadata_provider.get_pipelines_object_metadata(
            self.user_isid, self.group_id, self.project_id
        )
        trigger_operators_result = []
        for db_pipeline_object in db_pipeline_objects_metadata:
            # check if user has permission to run the pipeline (without run it does not make sense to sow the
            # pipeline in the list of pipelines for workflows
            pipeline_acls = []
            # first create ACLs to see if the user or project is owner of piepline and user has some default permissions
            # related with particular relation to pipeline
            for acl in db_pipeline_object["acls"]:
                pipeline_acls.append(
                    EntityACL(
                        EntitySubject(
                            subject_id=acl["SUBJECT_ID"],
                            subject_type=SubjectTypesEnum.from_str(acl["SUBJECT_TYPE"]),
                        ),
                        relation_type=ObjectsACLRelationTypesEnum.from_str(acl["RELATION_TYPE"])
                    )
                )
            if self.auth_validator.validate(
                    ActionType.EXECUTE_PIPELINE,
                    {"pipelineName": db_pipeline_object["pipeline_name"]},
                    acl_relation_list=pipeline_acls
            ) == PermissionEffectsEnum.allow:
                airflow_connection_id = f"difw_ui_http_airflow_{db_pipeline_object.get('project_owner_id')}"
                if not connections_buffer.get(airflow_connection_id):
                    # get Airflow api access
                    airflow_api_client = project_settings_management.get_shared_project_specific_airflow_api_client(
                        db_pipeline_object.get('project_owner_id')
                    )
                    airflow_connection = airflow_api_client.get_connection(
                        airflow_connection_id,
                        raise_no_data_error=False
                    )
                    # if connection is not there then create it
                    if not airflow_connection:
                        airflow_api_client.create_http_connection(
                            airflow_connection_id,
                            airflow_api_client.airflow_url,
                            airflow_api_client.username,
                            airflow_api_client.password
                        )
                    # mark that connection is exists or it is created
                    connections_buffer[airflow_connection_id] = True
                pipeline_object = trigger_operator_template.from_pipeline_object_metadata_db(
                    db_pipeline_object, airflow_connection_id
                )
                if pipeline_object:
                    trigger_operators_result.append(pipeline_object)
                else:
                    self.logger.warning(
                        f"Pipeline {db_pipeline_object['pipeline_name']} will not be added. "
                        f"DAG ID is not present there")

        return trigger_operators_result

    def get_component_type(self, component_category: str, component_type_name: str,
                           difw_core_version: str) -> EntityComponentType:
        """
        Get component type

        :param component_category:
        :param component_type_name:
        :param difw_core_version:

        @return: item of EntityComponentType
        """
        if self.auth_validator.validate(
                ActionType.USE_COMPONENT,
                {"componentTypeName": component_type_name, "componentCategory": component_category}) == \
                PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                f"has no permission to use component {component_type_name} under category {component_category}")
        component_type = EntityComponentType.from_metadb_object(
            self.definitions_metadata_provider.get_component_type(
                self.user_isid, ComponentTypeCategoriesEnum.from_str(component_category), component_type_name,
                difw_core_version))
        # if there is any custom resolver of metadata then use it
        if hasattr(self, f"_custom_resolving_{component_category}_{component_type_name}"):
            component_type = getattr(self, f"_custom_resolving_{component_category}_{component_type_name}")(
                **{"component_metadata": component_type})
        return component_type

    def get_permission_action_types(self):
        """
        Get the permission action type metadata

        @return:
        """
        permission_action_types = []
        db_results = self.definitions_metadata_provider.get_all_permission_action_types(self.user_isid)
        for db_result in db_results:
            permission_action_types.append(EntityPermissionActionType.from_metadb_object(db_result))
        return permission_action_types

    def get_framework_versions(self):
        """
        Get framework versions metadata

        @return: list of framework versions
        """
        framework_versions = []
        db_results = self.definitions_metadata_provider.get_all_framework_versions(self.user_isid)
        for db_result in db_results:
            framework_versions.append(EntityDifwCoreVersions.from_metadb_object(db_result))
        return framework_versions

    def get_enumerator_values(self, enumerator_category: str):
        """
        Get possible enumerator category values

        @return: list of possible enumerator values
        """
        enumerator_entities = EntityEnumerator.from_metadb_objects(
            self.definitions_metadata_provider.get_enumerator_values(enumerator_category, self.user_isid))
        if not enumerator_entities:
            raise NoDataError(f"Enumerator with category {enumerator_category} "
                              f"doesn't exist in MetaDB. Please check input.")
        # if DB returned data, we will return the list of entities to the api layer
        return enumerator_entities
