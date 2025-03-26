from middleware.common.configuration.model_converter.pipeline_model_to_configuration_converter import \
    PipelineModelToConfigurationConverter
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_advanced_options import EntityAdvancedOptions
from middleware.common.entity_management.objects_management import ObjectsManagement
from middleware.common.helpers.exception import AuthorizationError, EntityConflictError, NoDataError
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.pipeline_templates_metadata_provider import PipelineTemplateMetadataProvider
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.security.action_type import ActionType
from middleware.common.entity_management.entities.entity_pipeline_template import EntityPipelineTemplate
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from middleware.api.common.helpers import paginate_entries, SortAndPaginate


class PipelineTemplateManagement(ObjectsManagement):
    """
    Pipeline Template Management.

    """

    # pylint: disable=too-many-arguments
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pipeline_template_metadata_provider = None
        self.project_settings_management.project_id = self.project_id

    @property
    def model_converter(self) -> PipelineModelToConfigurationConverter:
        """
         model converter property
        """
        if not self._model_converter:
            self._model_converter = PipelineModelToConfigurationConverter(self.logger, self.secret_management,
                                                                          resolve_as_template=True)
        return self._model_converter

    @property
    def pipeline_template_metadata_provider(self):
        """
        Pipeline template metadata provider
        """
        if self._pipeline_template_metadata_provider is None:
            self._pipeline_template_metadata_provider = PipelineTemplateMetadataProvider(self.logger,
                                                                                         self.metadatabase_connection,
                                                                                         self.lambda_secrets_manager)
        return self._pipeline_template_metadata_provider

    def get_pipeline_template_default_project_values(self, pipeline_template_name, framework_version, object_version):
        """
        get default project values when pipeline template name = defaultProjectValues.

        @param pipeline_template_name
        @param framework_version
        @param object_version

        """
        # when pipeline template name is default Project Settings then we pick the accounts settings from project
        #  for platform type databricks we fetch the details rom MetaDB , for platform type glue we are
        # hard coding with some default configuration values.
        default_advanced_options = {
            "databricks": {},
            "glue": {
                "numberOfWorkers": 10,
                "workerType": "G.1X",
                "autoscaling": True,
                "sparkConfiguration": {},
                "javaSystemProperties": {},
                "sparkSqlConfiguration": {}
            },
            "airflowSettings": {
                "dagInstanceParameters": {
                    "is_paused_upon_creation": "False"
                }
            }
        }
        # calculate no of tags allowed while creating template or pipeline
        glue_max_tags_count, dbx_max_tags_count = self.calculate_available_tags_limit()
        default_advanced_options['glue']['maxTagsCount'] = glue_max_tags_count
        default_advanced_options['databricks']['maxTagsCount'] = dbx_max_tags_count
        # get resource prefix amd platform from project general settings.
        project_general_settings = self.project_settings_management.get_project_general_settings()
        # there is no need to check if project general setting is none or not .if project general settings are
        # not configured for a project then no data error (404) would be raised.
        # if project general setting is not None but still user forgets or misses to configure any property for
        # example lets say if user does not configure default platform then API would return error to avoid
        # that we are setting a default value for the properties that are not configured.
        # get default resource prefix value from project general settings.
        default_resource_prefix_setting = project_general_settings.resource_prefix \
            if project_general_settings.resource_prefix else 'data_ingest_{{dataset_name}}'

        # get default platform value from project general settings.
        default_platform_setting = project_general_settings.default_platform \
            if project_general_settings.default_platform else 'glue'

        # get all project settings of current project and add them to the pipeline template
        aws_settings = self.project_settings_management.get_project_account_settings(
            ProjectAccountTypesEnum.aws, check_permission=False).account_details

        # we are saving the same in both, the unnecessary records will be dropped as part of from_json_dict on bottom
        default_advanced_options['glue'].update(aws_settings)

        default_tags = {item["name"]: item["value"] for item in aws_settings.get('tags', [])}

        # get the default pipeline project values.
        default_pipeline_details = EntityPipelineTemplate(pipeline_template_name=pipeline_template_name,
                                                          pipeline_template_version=object_version,
                                                          platform=default_platform_setting,
                                                          status="drafted",
                                                          framework_version=framework_version,
                                                          resource_prefix=default_resource_prefix_setting,
                                                          enable_deferred_operators=False,
                                                          tags=default_tags)

        # get project settings for airflow
        default_advanced_options['airflowSettings'].update(
            self.project_settings_management.get_project_account_settings(
                ProjectAccountTypesEnum.airflow, check_permission=False).account_details)

        # get project settings for databricks account
        default_advanced_options['databricks'].update(self.project_settings_management.get_project_account_settings(
            ProjectAccountTypesEnum.databricks, check_permission=False).account_details)

        # append the default project settings for glue and databricks
        default_pipeline_details.set_advanced_options(EntityAdvancedOptions.from_json_dict(default_advanced_options))
        return default_pipeline_details

    def get_pipeline_template(self, pipeline_template_name: str, framework_version: str = None,
                              object_version: str = '1.0.0'):
        """
        get the details of the given pipeline template on basis of name and object versions

        @param pipeline_template_name:
        @param framework_version:
        @param object_version:

        """
        # call method to get default project values
        if pipeline_template_name == "defaultProjectValues":
            return self.get_pipeline_template_default_project_values(pipeline_template_name, framework_version,
                                                                     object_version)

        # Make an DB call to get the details for the requested pipeline template
        pipeline_template = EntityPipelineTemplate.from_metadb_object(
            self.pipeline_template_metadata_provider.get_pipeline_template(pipeline_template_name, object_version,
                                                                           self.user_isid))

        # if pipeline template with given name is not found in DB then raise 404.
        if not pipeline_template:
            raise NoDataError(f"Pipeline template with name {pipeline_template_name} does not exist")

        self.logger.info(f"Going to validate read pipeline template permissions for user - {self.user_isid}")
        if self.auth_validator.validate(ActionType.READ_PIPELINE_TEMPLATE,
                                        {"pipelineTemplateName": pipeline_template.pipeline_template_name},
                                        acl_relation_list=pipeline_template.acl) \
                == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"user {self.user_isid} under group {self.group_id} and {self.project_id} "
                f"has no permission to read pipeline template")

        # Fetch and set first and last connector types for the pipeline template flow
        first_input_connector, last_output_connector = self.get_first_and_last_steps_connectors(
            pipeline_template.steps)
        pipeline_template.set_first_and_last_connector_info(first_input_connector, last_output_connector)

        # calculate max tags counts for glue and databricks platform
        if pipeline_template.platform == "glue":
            max_tags_allowed_for_glue = 10
            # we are not calculating tags from calculate tags limit as that would yield incorrect results.
            # so to yield the right results we need to subtract platform  max limit minus tags from retrieved pipeline
            # from DB which include model converter tags as well , the same applies for databricks platform.
            max_tags_count = max_tags_allowed_for_glue - len(pipeline_template.tags)
            pipeline_template.advanced_options.entity_glue_options.set_max_tags_count(max_tags_count)
        else:
            max_tags_allowed_for_dbx = 25
            max_tags_count = max_tags_allowed_for_dbx - len(pipeline_template.tags)
            pipeline_template.advanced_options.entity_dbx_options.set_max_tags_count(max_tags_count)
        return pipeline_template

    def _get_pipeline_template(self, pipeline_template_name: str, object_version: str = '1.0.0'):
        """
        get the details of the given pipeline template on basis of name and object versions

        @param pipeline_template_name:
        @param object_version:

        """
        # Make an DB call to get the details for the requested pipeline template
        pipeline_template = EntityPipelineTemplate.from_metadb_object(
            self.pipeline_template_metadata_provider.get_pipeline_template(pipeline_template_name, object_version,
                                                                           self.user_isid))

        # if pipeline template with given name is not found in DB then raise 404.
        if not pipeline_template:
            raise NoDataError(f"Pipeline template with name {pipeline_template_name} does not exist")
        return pipeline_template

    def create_pipeline_template(self, entity_pipeline_template: EntityPipelineTemplate):
        """
        create pipeline template.

        @param entity_pipeline_template

        """
        self.logger.info(f"Going to validate create pipeline template permissions for {self.user_isid}")
        if self.auth_validator.validate(ActionType.CREATE_PIPELINE_TEMPLATE,
                                        {}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                f"has no permission to create pipeline template")

        if self.pipeline_template_metadata_provider.check_pipeline_template_exists(
                entity_pipeline_template.pipeline_template_name, ):
            raise EntityConflictError(
                f"Pipeline template with name {entity_pipeline_template.pipeline_template_name} exists")

        # add owners
        entity_pipeline_template.acl.extend(self.create_objects_owner_acls())

        # we need to remove component id from components, as they will be placed into component tables
        # with new unique ID
        entity_pipeline_template.clean_step_identifiers()

        # save pipeline template to meta db
        db_object, db_object_components = entity_pipeline_template.to_metadb_object()
        self.pipeline_template_metadata_provider.insert_or_update_pipeline_template(
            db_object, db_object_components, self.user_isid, is_update=False)

        return entity_pipeline_template.pipeline_template_name

    def update_pipeline_template(self, entity_pipeline_template: EntityPipelineTemplate):
        """
        update pipeline template.

        @param entity_pipeline_template

        """
        # check if the given pipeline template exists in DB before updating , if not then raise 404.
        pipeline_template_to_be_updated = self._get_pipeline_template(entity_pipeline_template.pipeline_template_name,
                                                                      entity_pipeline_template.entity_version)
        # we need to obtain previous owners and shared_template acls, as we do need to add them to the acl
        owners = EntityACL.filter_entity_acls(pipeline_template_to_be_updated.acl, ObjectsACLRelationTypesEnum.owner)
        shared_template = EntityACL.filter_entity_acls(pipeline_template_to_be_updated.acl,
                                                       ObjectsACLRelationTypesEnum.shared_template)
        # add owners, they are always there
        entity_pipeline_template.acl.extend(owners)
        # if there was any sharing as shared_pipeline add them too to the acls
        if shared_template:
            entity_pipeline_template.acl.extend(shared_template)
        self.logger.info(f"Going to validate update pipeline template permission for user - {self.user_isid}")
        if self.auth_validator.validate(ActionType.UPDATE_PIPELINE_TEMPLATE,
                                        {"pipelineTemplateName": pipeline_template_to_be_updated.pipeline_template_name
                                         }, acl_relation_list=pipeline_template_to_be_updated.acl) == \
                PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and {self.project_id} "
                f"has no permission to update pipeline template with name "
                f"{entity_pipeline_template.pipeline_template_name}")
        self.logger.info(f"Going to update pipeline template with name"
                         f"  {entity_pipeline_template.pipeline_template_name}")

        # update pipeline template to meta db
        db_object, db_object_components = entity_pipeline_template.to_metadb_object()
        self.pipeline_template_metadata_provider.insert_or_update_pipeline_template(
            db_object, db_object_components, self.user_isid, is_update=True)

        return entity_pipeline_template.pipeline_template_name

    def delete_pipeline_template(self, pipeline_template_name: str, object_version: str = "1.0.0"):
        """
        Delete pipeline template..

        @param pipeline_template_name:
        @param object_version:
        :return:
        """
        # check if the given pipeline template exists in DB before updating , if not then raise 404.
        pipeline_template_to_be_deleted = self._get_pipeline_template(pipeline_template_name, object_version)
        self.logger.info(f"Going to validate delete pipeline template permission for user - {self.user_isid}")
        if self.auth_validator.validate(ActionType.DELETE_PIPELINE_TEMPLATE,
                                        {"pipelineTemplateName": pipeline_template_to_be_deleted.pipeline_template_name
                                         }, acl_relation_list=pipeline_template_to_be_deleted.acl) == \
                PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id}"
                f" has no permission to delete pipeline template with name {pipeline_template_name}")
        self.logger.info(f"Going to delete pipeline template with name {pipeline_template_name}")
        return self.pipeline_template_metadata_provider.delete_pipeline_template(pipeline_template_name,
                                                                                 object_version,
                                                                                 self.user_isid)

    def modify_acl_for_pipeline_template(self, new_acls: list, pipeline_template_name: str):
        """
        modify pipeline template sharing acl

        @param new_acls - List of acls with relation_type shared_template to be updated into db
        @param pipeline_template_name - name of the pipeline template whose acl will be modified

        """
        # check if the given pipeline template exists in DB before updating , if not then raise 404.
        pipeline_template_to_be_updated = self._get_pipeline_template(pipeline_template_name)
        self.logger.info(
            f"Going to validate update pipeline template permission for user {self.user_isid} on pipeline template "
            f"name {pipeline_template_name}")
        if self.auth_validator.validate(ActionType.UPDATE_PIPELINE_TEMPLATE,
                                        {"pipelineTemplateName": pipeline_template_to_be_updated.pipeline_template_name
                                         }, acl_relation_list=pipeline_template_to_be_updated.acl) == \
                PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                f"has no permission to update pipeline template with name {pipeline_template_name}")
        # if we have
        return self.pipeline_template_metadata_provider.update_pipeline_template_assigned_acl_list(
            pipeline_template_name, new_acls, self.user_isid)

    # pylint disable=too-many-function-args
    def get_pipeline_templates(self, pipeline_template_name: str = None, sort_and_paginate: SortAndPaginate = None,
                               status: str = None, limited_view: bool = False):
        """
        Get pipeline templates

        @param pipeline_template_name: optional parameter , substring of display name of subject
        @param sort_and_paginate:
        @param status:
        @param limited_view:
        :return: list of pipeline templates
        """

        self.logger.info("Going to retrieve pipeline templates")

        # Get all pipelines templates from DB.
        pipeline_templates = EntityPipelineTemplate.from_metadb_objects(
            self.pipeline_template_metadata_provider.get_pipeline_templates(
                self.user_isid, pipeline_template_name, status, self.selected_subject_ids,
                sort_and_paginate))

        # if there are no templates then raise no data error
        if not pipeline_templates:
            raise NoDataError(f"There are not existing pipeline templates which are accessible "
                              f"for user {self.user_isid} within group {self.group_id} and project {self.project_id}")
        self.logger.info(f"Validating read permissions of user {self.user_isid}.")

        result_pipeline_templates = list()

        for pipeline_template in pipeline_templates:
            if self.auth_validator.validate(ActionType.READ_PIPELINE_TEMPLATE,
                                            {"pipelineTemplateName": pipeline_template.pipeline_template_name},
                                            acl_relation_list=pipeline_template.acl) \
                    == PermissionEffectsEnum.deny:
                continue
            # set first connector and last connector for pipeline template
            # before sitting ,first check if there are steps for the pipeline template that is being read since
            # drafted pipeline templates ay not have steps in that case we can simply skip setting connector
            # info if steps is None
            first_input_connector, last_output_connector = self.get_first_and_last_steps_connectors(
                pipeline_template.steps)
            pipeline_template.set_first_and_last_connector_info(first_input_connector, last_output_connector)
            result_pipeline_templates.append(pipeline_template)
        total_count = len(result_pipeline_templates)
        result_pipeline_templates = [ct.to_json_dict(limited_view) for ct in result_pipeline_templates]
        result_pipeline_templates = paginate_entries(result_pipeline_templates, sort_and_paginate)
        if not result_pipeline_templates:
            raise NoDataError(f"There are not existing pipeline templates which are accessible "
                              f"for user {self.user_isid} within group {self.group_id} and project {self.project_id}")
        return result_pipeline_templates, total_count

    def convert_model_to_yaml(self, pipeline_template: EntityPipelineTemplate) -> (dict, str):
        """
        Convert pipeline template to yaml configuration

        @param pipeline_template: model to convert to yaml
        :return: a pair of dict as represent yaml configuration and str as representor of pipeline name
        """
        self.logger.info("Start method convert_model_to_yaml")
        platform_configuration = {
            ProjectAccountTypesEnum.aws: self.aws_account_settings,
            ProjectAccountTypesEnum.airflow: self.airflow_account_settings
        }
        if pipeline_template.platform == "databricks":
            platform_configuration[ProjectAccountTypesEnum.databricks] = self.databricks_account_settings
        return self.model_converter.convert_model_to_yaml_config(input_entity=pipeline_template,
                                                                 pipeline_name=pipeline_template.pipeline_template_name,
                                                                 platform_configuration=platform_configuration,
                                                                 region=self.aws_region,
                                                                 is_template=True
                                                                 ), pipeline_template.pipeline_template_name

    def check_pipeline_template_existence(self, pipeline_template_name: str, object_version: str = '1.0.0'):
        """
        check the existence of pipeline template in DB

        @param pipeline_template_name:
        @param object_version:

        """
        self.logger.info(f"User {self.user_isid} starts method check_pipeline_template_existence"
                         f" with pipeline_template_name={pipeline_template_name}")
        exists = self.pipeline_template_metadata_provider.check_pipeline_template_exists(pipeline_template_name,
                                                                                         object_version, self.user_isid)
        if not exists:
            raise NoDataError(
                f"Pipeline template with name {pipeline_template_name} and version {object_version} does not exist")
        return True
