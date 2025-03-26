import concurrent.futures
import os
import tempfile
import uuid

import yaml

from common.secrets.secrets import register_secret_type
from common.helpers.exception import NotFoundError
from middleware.api.common.helpers import paginate_entries
from middleware.api.common.helpers import SortAndPaginate
from middleware.common.configuration.model_converter.pipeline_model_to_configuration_converter import (
    PipelineModelToConfigurationConverter,
)
from middleware.common.configuration.model_converter.pipeline_runtime_model_to_configuration_converter import (
    PipelineRuntimeModelToConfigurationConverter,
)
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline
from middleware.common.entity_management.entities.entity_object_run import EntityObjectRun
from middleware.common.entity_management.entities.entity_pipeline_steps import EntityPipelineSteps
from middleware.common.entity_management.events_management import EventsManagement
from middleware.common.entity_management.objects.owner_filter_enum import OwnerFilterEnum
from middleware.common.entity_management.objects.project_filter_enum import ProjectFilterEnum
from middleware.common.helpers.exception import AuthorizationError, EntityConflictError, BadRequest, NoDataError
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from middleware.common.metadatabase.pipelines_metadata_provider import PipelinesMetadataProvider
from middleware.common.security.action_type import ActionType
from middleware.common.entity_management.objects_management import ObjectsManagement
from middleware.common.helpers.dataset_repo_utils import DatasetRepoUtils
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum


# pylint: disable=too-many-public-methods, too-many-instance-attributes, too-many-lines
class PipelinesManagement(ObjectsManagement):
    """
    Pipelines Management.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pipelines_metadata_provider = None
        self.event = None
        self.request_id = None
        self._events_management = None
        self.is_async = kwargs.get("is_async", False)
        # setup tokens
        aws_access_key, aws_secret_key, aws_session_token = (
            self.project_settings_management.get_project_aws_account_access_info()
        )
        self.set_aws_tokens(aws_access_key, aws_secret_key, aws_session_token)
        self.project_settings_management.project_id = self.project_id
        # register secret manager to work with secrets within Yaml
        register_secret_type()
        self._model_runtime_converter = None

    @property
    def events_management(self):
        """
        project settings management property
        """
        if self._events_management is None:
            self._events_management = EventsManagement(
                logger=self.logger,
                metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager,
                user_isid=self.user_isid,
                selected_subjects=self.selected_subjects,
            )
        return self._events_management

    @property
    def model_converter(self) -> PipelineModelToConfigurationConverter:
        """
        Model converter property
        """
        if not self._model_converter:
            self._model_converter = PipelineModelToConfigurationConverter(
                self.logger, self.secret_management, resolve_as_template=False
            )
        return self._model_converter

    @property
    def model_runtime_converter(self) -> PipelineRuntimeModelToConfigurationConverter:
        """
        Model runtime converter property, used to convert job section of the pipeline
        """
        if not self._model_runtime_converter:
            self._model_runtime_converter = PipelineRuntimeModelToConfigurationConverter(
                self.logger, self.secret_management
            )
        return self._model_runtime_converter

    @property
    def pipelines_metadata_provider(self):
        """
        Pipeline template metadata provider
        """
        if self._pipelines_metadata_provider is None:
            self._pipelines_metadata_provider = PipelinesMetadataProvider(
                self.logger, self.metadatabase_connection, self.lambda_secrets_manager
            )
        return self._pipelines_metadata_provider

    def _enrich_pipeline_with_airflow_details(self, pipeline: EntityPipeline):
        """
        Enrich entity pipeline with details from airflow.

        @param pipeline: EntityPipeline object to enrich
        """
        if self.is_pipeline_drafted(pipeline):
            pipeline.set_status("drafted")
        elif pipeline.dag_id:
            self.logger.info(
                f"The pipeline {pipeline.pipeline_name} " f"exists in Airflow, info from Airflow will be retrieved."
            )
            # obtain airflow details of pipeline based on dag and its project owner
            next_dag_run, start_date, last_runtime, status = self._get_object_airflow_details(
                pipeline.dag_id, pipeline.get_project_owner
            )
            pipeline.set_status(status)
            pipeline.set_last_run(start_date)
            pipeline.set_last_runtime(last_runtime)
            pipeline.set_next_run(next_dag_run)
        # edge case which shows that the pipeline is not well-defined - not drafted and missing dag
        else:
            self.logger.info(f"Pipeline with name {pipeline.pipeline_name} is not drafted and does not have dag id.")
            # we could raise error, but when called via concurrent.futures this error will not be propagated
            # it is better to show user, that there is issue with the workflow
            pipeline.set_status("corrupted")

    def get_pipeline_detail(
            self, pipeline_name: str, pipeline_version: str = "1.0.0", orchestrator_info: bool = False
    ) -> EntityPipeline:
        """
        Get pipeline details

        @param pipeline_name: name of pipeline
        @param pipeline_version: version of pipeline
        @param orchestrator_info:
        """
        self.logger.info(f"User {self.user_isid} starts method get_pipeline_detail with pipeline_name={pipeline_name}")
        retrieved_pipeline = self._get_pipeline_raise_error_if_not_exists(
            pipeline_name, pipeline_version, raise_bad_request_if_drafted=False
        )
        if (
                self.auth_validator.validate(
                    ActionType.READ_PIPELINE, {"pipelineName": pipeline_name}, acl_relation_list=retrieved_pipeline.acl
                )
                == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                f"has no permission to read pipeline with name {pipeline_name}"
            )

        if orchestrator_info:
            self._enrich_pipeline_with_airflow_details(retrieved_pipeline)
        # enhance by first and last input and output connector

        first_input_connector, last_output_connector = self.get_first_and_last_steps_connectors(
            retrieved_pipeline.steps
        )
        retrieved_pipeline.set_first_and_last_connector_info(first_input_connector, last_output_connector)
        # calculate max tags counts for glue and databricks platform
        if retrieved_pipeline.platform == "glue":
            max_tags_allowed_for_glue = 10
            # we are not calculating tags from calculate tags limit as that would yield incorrect results.
            # so to yield the right results we need to subtract platform  max limit minus tags from retrieved pipeline
            # from DB which include model converter tags as well , the same applies for databricks platform.
            max_tags_count = max_tags_allowed_for_glue - len(retrieved_pipeline.tags)
            retrieved_pipeline.advanced_options.entity_glue_options.set_max_tags_count(max_tags_count)
        else:
            max_tags_allowed_for_dbx = 25
            max_tags_count = max_tags_allowed_for_dbx - len(retrieved_pipeline.tags)
            retrieved_pipeline.advanced_options.entity_dbx_options.set_max_tags_count(max_tags_count)
        return retrieved_pipeline

    def get_pipeline_details(self, limited_view: bool = False, pipeline_name: str = None,
                             is_enabled: bool = None, owner: OwnerFilterEnum = None, sort_and_paginate:
            SortAndPaginate = None, orchestrator_info: bool = True,
                             project_filter: ProjectFilterEnum = None) -> ([EntityPipeline], int):
        """
        Get pipeline details
        @param limited_view:
        @param pipeline_name: name of pipeline
        @param is_enabled: flag indicates if pipeline is enabled or disabled
        @param owner: owner of pipeline
        @param sort_and_paginate:
        @param orchestrator_info: flag if we should get airflow information
        @param project_filter:
        """

        pipelines = EntityPipeline.from_metadb_objects(
            self.pipelines_metadata_provider.get_pipelines(
                user_id=self.user_isid,
                subject_ids=self.selected_subject_ids,
                pipeline_name=pipeline_name,
                is_enabled=is_enabled,
                owner=self.user_isid if owner == OwnerFilterEnum.current else None,
                sort_and_paginate=sort_and_paginate,
                project_id=self.project_id if project_filter == ProjectFilterEnum.current else None,
            )
        )
        pipelines_result = []
        for pipeline in pipelines:
            if (
                    self.auth_validator.validate(
                        ActionType.READ_PIPELINE, {"pipelineName": pipeline.pipeline_name},
                        acl_relation_list=pipeline.acl
                    )
                    == PermissionEffectsEnum.deny
            ):
                continue
            pipelines_result.append(pipeline)
        if not pipelines_result:
            raise NoDataError(
                f"There are no existing pipelines, which are accessible for user {self.user_isid}"
                f" within group {self.group_id} and project {self.project_id} based on given filters"
            )

        total_count = len(pipelines_result)
        pipelines_result_paginated = paginate_entries(pipelines_result, sort_and_paginate)
        if orchestrator_info:
            for pipeline in pipelines_result_paginated:
                self._enrich_pipeline_with_airflow_details(pipeline)
        pipelines_result_list = [ct.to_json_dict(limited_view) for ct in pipelines_result_paginated]
        return pipelines_result_list, total_count

    def create_pipeline(self, entity_pipeline: EntityPipeline, request_id: str) -> EntityPipeline:
        """
        Create pipeline

        :param entity_pipeline: pipeline entity to create
        :param request_id: request id

        :return: name of created pipeline

        """
        self.logger.info("Start method create_pipeline")

        self.request_id = request_id

        if self.auth_validator.validate(ActionType.CREATE_PIPELINE, {}) == PermissionEffectsEnum.deny:
            # create sub event
            if self.is_async:
                self.events_management.create_or_update_sub_event_entity(
                    request_id=request_id, sequence_number=1, event_type="validation", status="failed"
                )

            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                "has no permission to create pipeline"
            )

        self.logger.info("User is authorized and can continue with creation of pipeline")

        if self.pipelines_metadata_provider.exists_pipeline(
                entity_pipeline.pipeline_name, entity_pipeline.pipeline_version
        ):
            # create the sub event
            if self.is_async:
                self.events_management.create_or_update_sub_event_entity(
                    request_id=request_id, sequence_number=1, event_type="validation", status="failed"
                )

            raise EntityConflictError(
                f"Pipeline with name {entity_pipeline.pipeline_name} "
                f"and version {entity_pipeline.pipeline_version} exists"
            )
        # upsert pipeline now
        return self._upsert_pipeline(entity_pipeline=entity_pipeline, is_update=False)

    def update_pipeline(self, entity_pipeline: EntityPipeline, request_id: str) -> EntityPipeline:
        """
        Create pipeline

        :param entity_pipeline: pipeline entity to update
        :param request_id: request id
        :return: name of updated pipeline

        """
        self.logger.info("Start method update_pipeline")
        self.request_id = request_id
        # check pipeline acls
        self._check_update_of_pipeline(entity_pipeline.pipeline_name, entity_pipeline.pipeline_version)
        # upsert pipeline now
        return self._upsert_pipeline(entity_pipeline=entity_pipeline, is_update=True)

    def update_pipeline_acl(self, pipeline_name: str, pipeline_acls: [EntityACL], pipeline_version: str = "1.0.0"):
        """
        Update acl of pipeline

        @param pipeline_name: name of pipeline to update
        @param pipeline_version: version of pipeline
        @param pipeline_acls: list of acl to update
        """
        self.logger.info(f"Start method update_pipeline_acl. ACLs = {pipeline_acls}. Pipeline name={pipeline_name}")
        # check if the given pipeline template exists in DB before updating , if not then raise 404.
        self._check_update_of_pipeline(pipeline_name, pipeline_version)
        return self.pipelines_metadata_provider.update_pipeline_assigned_acl_list(
            pipeline_name=pipeline_name, acls=pipeline_acls, pipeline_version=pipeline_version, user_id=self.user_isid
        )

    def update_schedule(self, pipeline_name: str, schedule_cron: str, pipeline_version: str = "1.0.0"):
        """
        Update schedule

        @param pipeline_name: name of pipeline to update
        @param schedule_cron: cron to update for schedule or "None"
        @param pipeline_version: version of pipeline to update
        """
        self.logger.info(
            f"Start method update_schedule. Schedule cron = {schedule_cron}. Pipeline name={pipeline_name}"
        )
        # check if the given pipeline template exists in DB before updating , if not then raise 404.
        self._check_update_of_pipeline(pipeline_name, pipeline_version)
        # change it in configuration provider
        self.update_key_in_configuration_provider(
            object_name=pipeline_name, key_to_rewrite="schedule", new_value=schedule_cron
        )
        # update schedule in DB
        self.pipelines_metadata_provider.update_schedule(
            pipeline_name, schedule_cron, self.user_isid, pipeline_version, ObjectTypesEnum.pipeline
        )

    def update_pipeline_enable_flag(self, pipeline_name: str, enable_flag: bool, pipeline_version: str = "1.0.0"):
        """
        Update enablement/disablement of pipeline

        @param pipeline_name: name of pipeline to update
        @param pipeline_version: version of pipeline to update
        @param enable_flag: enable flag
        """
        self.logger.info(
            f"Start method update_pipeline_enable_flag. Enablement flag={enable_flag}. Pipeline name={pipeline_name}"
        )
        # check if the given pipeline template exists in DB before updating , if not then raise 404.
        self._check_update_of_pipeline(pipeline_name, pipeline_version)
        dag_name = self.pipelines_metadata_provider.get_pipeline_dag_name(
            pipeline_name, pipeline_version, self.user_isid
        )

        # change it in Airflow
        # enable = True mean that is_paused = False
        self.get_and_resolve_airflow_api_client(project_id=self.project_id).pause_or_unpause_dag(
            dag_name, not enable_flag
        )
        # update enable flag
        self.pipelines_metadata_provider.update_pipeline_enable_flag(
            pipeline_name, self.user_isid, pipeline_version, enable_flag
        )

    def _check_update_of_pipeline(self, pipeline_name, pipeline_version) -> [EntityACL]:
        """
        Check if update of pipeline is possible. Within the method is checking:
        1. If pipeline exists
        2. ACL
        3. Permission to update pipeline
        4. If the current project is owner of the pipeline, if it is not, we are raising error

        @param pipeline_name: name of pipeline to update
        @param pipeline_version: version of pipeline

        @return: pipeline ACL
        """
        if not self.pipelines_metadata_provider.exists_pipeline(pipeline_name, pipeline_version):
            if self.is_async:
                self.events_management.create_or_update_sub_event_entity(
                    request_id=self.request_id, sequence_number=1, event_type="validation", status="failed"
                )
            raise NoDataError(f"Pipeline with name {pipeline_name} and version {pipeline_version} does not exist")
        # first retrieve ACLs to check permissions of this pipeline
        pipeline_acls = EntityACL.from_metadb_object_objects_acls(
            self.pipelines_metadata_provider.get_pipeline_acl(pipeline_name, user_id=self.user_isid)
        )

        if (
                self.auth_validator.validate(
                    ActionType.UPDATE_PIPELINE, {"pipelineName": pipeline_name}, acl_relation_list=pipeline_acls
                )
                == PermissionEffectsEnum.deny
        ):
            # create sub event
            if self.is_async:
                self.events_management.create_or_update_sub_event_entity(
                    request_id=self.request_id, sequence_number=1, event_type="validation", status="failed"
                )
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                "has no permission to update pipeline"
            )
        # if you are updating from project that is not owner, error is raised
        if not EntityACL.filter_entity_acls(
                entity_acl_objects=pipeline_acls,
                relation_type=ObjectsACLRelationTypesEnum.owner,
                subjects_ids=[self.project_id],
        ):
            raise BadRequest("Currently you are in non-owner project. To update, switch to owner project.")
        return pipeline_acls

    # pylint: disable=too-many-locals, too-many-statements, too-many-branches
    def _upsert_pipeline(self, entity_pipeline: EntityPipeline, is_update=False):
        """
        Upsert pipeline. Upsertion include actions in resources and actions in db

        @param entity_pipeline: pipeline entity to update
        """
        if not entity_pipeline.dag_id:
            # disable by default. also it is disabled within model configuration converter
            # if there is no is_paused_upon_creation in pipeline, we disable it by default, airflow disables it too
            entity_pipeline.set_is_enabled(
                not entity_pipeline.advanced_options.entity_airflow_options.dag_instance_parameters.get(
                    "is_paused_upon_creation", True
                )
            )

        self.logger.info("Generate pipeline definition,...")
        # The current working directory is needed, the current working directory
        # is changed to the temporary directory created with context manager.
        # After the deletion of the temporary directory we need to restore
        # the cwd. This is due to the call to os.getcwd() which would fail
        # in case of cwd is set to deleted directory
        cwd = os.getcwd()
        if not self.is_pipeline_drafted(entity_pipeline):
            if self.is_async:
                self.events_management.create_or_update_sub_event_entity(
                    request_id=self.request_id, sequence_number=2, event_type="yaml_generation", status="in_progress"
                )
            pipeline_definition, _ = self.convert_model_to_yaml(entity_pipeline)
            if self.is_async:
                self.events_management.create_or_update_sub_event_entity(
                    request_id=self.request_id,
                    sequence_number=2,
                    event_type="yaml_generation",
                    status="success",
                    output=yaml.dump(pipeline_definition),
                )

            if self.is_async:
                self.events_management.create_or_update_sub_event_entity(
                    request_id=self.request_id,
                    sequence_number=3,
                    event_type="airflow_pools_creation",
                    status="in_progress",
                )
            # check existence of the airflow pool or create it
            self.check_or_create_airflow_pool(
                airflow_advanced_settings=entity_pipeline.advanced_options.entity_airflow_options
            )
            if self.is_async:
                self.events_management.create_or_update_sub_event_entity(
                    request_id=self.request_id,
                    sequence_number=3,
                    event_type="airflow_pools_creation",
                    status="success",
                    output="Airflow pool was already existing or" "was created",
                )
            tmp_folder = "/tmp"
            tmp_folder_prefix = uuid.uuid4().hex
            source_code_folder = "/var/task"
            pipeline_name = entity_pipeline.pipeline_name
            environment = self.project_settings_management.get_project_environment()
            # create temporary workspace in /tmp folder of aws lambda container
            try:
                with tempfile.TemporaryDirectory(prefix=tmp_folder_prefix, dir=tmp_folder) as tmpdir:

                    if self.is_async:
                        self.events_management.create_or_update_sub_event_entity(
                            request_id=self.request_id,
                            sequence_number=4,
                            event_type="resource_generation",
                            status="in_progress",
                        )

                    self.logger.info("Generate yaml configuration,...")
                    # create configuration file
                    self.create_yaml_configuration_file(pipeline_name, tmpdir, pipeline_definition)

                    # run resource generator first
                    self.run_resource_generator(
                        **{
                            "tmpdir": tmpdir,
                            "dataset_name": pipeline_name,
                            "source_code_folder": source_code_folder,
                            "object_version": entity_pipeline.pipeline_version,
                            "framework_version": entity_pipeline.framework_version,
                            "environment": environment,
                        }
                    )
                    if self.is_async:
                        self.events_management.create_or_update_sub_event_entity(
                            request_id=self.request_id,
                            sequence_number=4,
                            event_type="resource_generation",
                            status="success",
                        )
                    self.logger.info("Run airflow generator,...")
                    if self.is_async:
                        self.events_management.create_or_update_sub_event_entity(
                            request_id=self.request_id,
                            sequence_number=5,
                            event_type="dag_generation",
                            status="in_progress",
                        )
                    airflow_link, dag_name = self.process_orchestration(
                        **{
                            "tmpdir": tmpdir,
                            "dataset_name": pipeline_name,
                            "framework_version": entity_pipeline.framework_version,
                            "environment": environment,
                        }
                    )
                    if self.is_async:
                        self.events_management.create_or_update_sub_event_entity(
                            request_id=self.request_id, sequence_number=5, event_type="dag_generation", status="success"
                        )

                    entity_pipeline.set_airflow_link(airflow_link)
                    entity_pipeline.set_dag_id(dag_name)
            except:
                os.chdir(cwd)
                raise
        # reset the path as the temp file is removed
        os.chdir(cwd)
        if not is_update:
            # we need to remove component id from components, as they will be placed into component tables
            # with new unique ID
            entity_pipeline.clean_step_identifiers()
            # add owner into pipeline
            entity_pipeline.acl.extend(self.create_objects_owner_acls())
        else:
            # obtain old acls and keep only owners from them, all shared will be dropped and replaced with new
            pipeline_acls = EntityACL.from_metadb_object_objects_acls(
                self.pipelines_metadata_provider.get_pipeline_acl(entity_pipeline.pipeline_name, user_id=self.user_isid)
            )
            # we need to obtain previous owners and shared_template acls, as we do need to add them to the acl
            owners = EntityACL.filter_entity_acls(pipeline_acls, ObjectsACLRelationTypesEnum.owner)
            # add owners into the pipeline entity
            entity_pipeline.acl.extend(owners)

            # delete te old pipeline
            self.delete_pipeline(
                pipeline_name=entity_pipeline.pipeline_name, check_permission=False, commit=False, update=True
            )

        # going to be draft therefore it is disabled by default
        if self.is_pipeline_drafted(entity_pipeline):
            entity_pipeline.set_is_enabled(False)
            # but it can run before
            if entity_pipeline.dag_id:
                # disable airflow dag
                self.get_and_resolve_airflow_api_client(project_id=self.project_id).pause_or_unpause_dag(
                    dag_id=entity_pipeline.dag_id, pause_flag=True
                )

        # resolve runtime steps
        entity_pipeline.set_runtime_steps(self._resolve_runtime_steps_attributes(entity_pipeline))

        # save pipeline to meta db
        save_meta_data_seq = 2 if self.is_pipeline_drafted(entity_pipeline) else 6
        if self.is_async:
            self.events_management.create_or_update_sub_event_entity(
                request_id=self.request_id,
                sequence_number=save_meta_data_seq,
                event_type="saving_metadata",
                status="in_progress",
            )
        db_object, db_object_components = entity_pipeline.to_metadb_object()
        self.pipelines_metadata_provider.insert_or_update_pipeline(
            db_object, db_object_components, is_update, self.user_isid
        )
        if self.is_async:
            self.events_management.create_or_update_sub_event_entity(
                request_id=self.request_id,
                sequence_number=save_meta_data_seq,
                event_type="saving_metadata",
                status="success",
            )
        return entity_pipeline

    def _resolve_runtime_steps_attributes(self, entity_pipeline: EntityPipeline) -> [dict]:
        """
        check if pipeline contains any runtime attributes. If yes then create list of steps which contains such
        attribute

        @param entity_pipeline:
        @return: List of steps and runtime attributes in dict form
        """
        self.logger.info(f"Going to resolve runtime attributes for pipeline {entity_pipeline.pipeline_name}")
        runtime_steps = []
        for entity_pipeline_step in entity_pipeline.steps:
            runtime_step = {
                "componentName": entity_pipeline_step.component_name,
                "componentId": entity_pipeline_step.component_id,
                "model": {
                    "componentCategory": entity_pipeline_step.definition.get("componentCategory"),
                    "componentType": entity_pipeline_step.definition.get("componentType"),
                    "difwStepType": entity_pipeline_step.definition.get("difwStepType"),
                    "difwStepCategory": entity_pipeline_step.definition.get("difwStepCategory"),
                    "attributes": [],
                },
            }
            for step_attribute in entity_pipeline_step.definition.get("attributes", []):
                if step_attribute.get("isRuntime", False):
                    runtime_step["model"]["attributes"].append(step_attribute)
            # if there are any runtime attributes, then add it as runtime steps
            if runtime_step["model"]["attributes"]:
                runtime_steps.append(runtime_step)
        return runtime_steps

    def convert_model_to_yaml(self, pipeline: EntityPipeline) -> (dict, str):
        """
        Convert pipeline to yaml configuration

        @param pipeline: model to convert to yaml
        @return: pair of dict as represent yaml configuration and str as representer of pipeline name
        """
        self.logger.info("Start method convert_model_to_yaml")
        platform_configuration = {
            ProjectAccountTypesEnum.aws: self.aws_account_settings,
            ProjectAccountTypesEnum.airflow: self.airflow_account_settings,
        }
        if pipeline.platform == "databricks":
            platform_configuration[ProjectAccountTypesEnum.databricks] = self.databricks_account_settings
        return (
            self.model_converter.convert_model_to_yaml_config(
                input_entity=pipeline,
                pipeline_name=pipeline.pipeline_name,
                platform_configuration=platform_configuration,
                region=self.aws_region,
            ),
            pipeline.pipeline_name,
        )

    def convert_yaml_to_model(
            self, pipeline_configuration: dict, pipeline_name: str, framework_version: str, environment: str = "dev"
    ) -> (EntityPipeline, dict, [str]):
        """
        Convert yaml configuration to pipeline model

        @param pipeline_configuration: yaml configuration of pipeline
        @param pipeline_name: name of pipeline. If not fill. The pipeline name will be taken from pipeline configuration
        @param framework_version: version of FW
        @param environment: environment
        @return:
            - pipeline model
            - list of secret
            - list of excluded attributes
        """
        self.logger.info("Start method convert_yaml_to_model")
        final_entity_pipeline_model, unprocessed_yaml_configuration, created_secrets = (
            self.configuration_converter.convert_yaml_config_to_model(
                pipeline_configuration, framework_version, "1.0.0", environment
            )
        )
        final_entity_pipeline_model.set_pipeline_name(pipeline_name)
        return final_entity_pipeline_model, unprocessed_yaml_configuration, created_secrets

    def get_pipeline_runs(self, pipeline_name: str, max_result: int) -> [EntityObjectRun]:
        """
        Get pipeline runs

        @param pipeline_name: name of pipeline
        @param max_result - param to control how many runs of airflow runs needs to be retrieved
        @return: list of pipeline runs
        """
        self.logger.info(f"Start method get_pipeline_runs with pipeline_name={pipeline_name}")
        pipeline = self._get_pipeline_raise_error_if_not_exists(pipeline_name, raise_bad_request_if_drafted=False)
        # call Airflow api to get the run details
        return self.get_objects_runs(
            dag_id=pipeline.dag_id, max_result=max_result, project_id=pipeline.get_project_owner
        )

    def get_tasks_of_object_runs(self, pipeline_name: str, dag_run_id: str) -> [EntityObjectRun]:
        """
        Get tasks of runs of pipelines

        @param pipeline_name: name of pipeline
        @param dag_run_id: run id of dag

        @return: list of EntityObjectTaskOfRun
        """
        self.logger.info(
            f"Start method get_tasks_of_object_runs for pipeline_name={pipeline_name} and dag_run_id={dag_run_id}"
        )
        pipeline = self._get_pipeline_raise_error_if_not_exists(pipeline_name, raise_bad_request_if_drafted=False)
        return self.get_tasks_of_object_runs_from_api(
            dag_id=pipeline.dag_id, dag_run_id=dag_run_id, project_id=pipeline.get_project_owner
        )

    def get_logs_of_task(self, pipeline_name: str, dag_run_id: str, task_id: str, try_number: int) -> str:
        """
        Get tasks of runs of pipelines

        @param pipeline_name: name of pipeline
        @param dag_run_id: run id of dag
        @param task_id: task id
        @param try_number: try number

        @return: logs
        """
        self.logger.info(
            f"Start method get_logs_of_task for pipeline_name={pipeline_name}, dag_run_id={dag_run_id}, "
            f"task_id={task_id}, try_number={try_number}"
        )
        pipeline = self._get_pipeline_raise_error_if_not_exists(pipeline_name, raise_bad_request_if_drafted=False)
        return self.get_logs_of_task_from_api(
            dag_id=pipeline.dag_id,
            dag_run_id=dag_run_id,
            task_id=task_id,
            try_number=try_number,
            project_id=pipeline.get_project_owner,
        )

    def start_pipeline(self, pipeline_name: str, logical_date: str, run_conf: []):
        """
        Start pipeline

        @param pipeline_name: name of pipeline to start
        @param logical_date: logical date
        @param run_conf: running configuration
        """
        self.logger.info(
            f"Start method start_pipeline. Pipeline name={pipeline_name}\n"
            f"logical date={logical_date}\n"
            f"run configuration={run_conf}"
        )
        # check if pipeline exists, retrieve it from DB
        pipeline = self._get_pipeline_raise_error_if_not_exists(pipeline_name, raise_bad_request_if_drafted=False)
        if (
                self.auth_validator.validate(
                    ActionType.EXECUTE_PIPELINE, {"pipelineName": pipeline_name}, acl_relation_list=pipeline.acl
                )
                == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                f"has no permission to execute pipeline with name {pipeline_name}"
            )
        # check if pipeline is drafted
        if self.is_pipeline_drafted(pipeline):
            raise BadRequest(
                f"Forbidden Action: pipeline with name {pipeline_name} is currently in draft mode "
                f"and cannot be triggered"
            )

        conf_inner_dictionary = {}
        # if run configuration is given in request, we need to reparse it in appropriate format, so we can send it to
        # airflow api
        if run_conf:
            # if run_conf is given, we need to convert the jobs section and replace the runtime with new values,
            # run_conf needs to have same amount of steps as is there in the pipeline, even if step is not having any
            # of the runtime params, it is still needed to be there in the request as we need to assign correct steps
            # each other
            pipeline_steps = [EntityPipelineSteps.from_json_dict(step, pipeline.framework_version) for step in run_conf]
            # call model runtime convertor, which is just for jobs section
            converted_step_config = self.model_runtime_converter.convert_model_to_yaml_config(
                input_entity=pipeline,
                pipeline_name=pipeline_name,
                region=self.aws_region,
                pipeline_steps=pipeline_steps,
            )
            conf_inner_dictionary = {"dynamic_runtime_params": converted_step_config}
        run_conf_data = {"conf": conf_inner_dictionary}
        # trigger the DAG with
        self.logger.info(f"Going to Start pipeline {pipeline_name}")
        # in case, if logical date is not None, then add it to request body
        if logical_date:
            run_conf_data.update({"logical_date": logical_date})
        try:
            return self.get_and_resolve_airflow_api_client(project_id=pipeline.get_project_owner).trigger_dag_run(
                dag_id=pipeline.dag_id, run_conf_data=run_conf_data
            )
        except NotFoundError as exc:
            raise NoDataError(f"Dag {pipeline.dag_id} for pipeline with name {pipeline_name} does not exist") from exc

    def stop_pipeline(self, pipeline_name: str, state: str):
        """
        Stop all pipeline runs which are currently running and set them to given state,
        State can be one of success,failed

        @param pipeline_name: name of pipeline to be stopped
        @param state: status of pipeline to be set to
        """
        self.logger.info(f"Start method stop_pipeline. Pipeline name={pipeline_name}")
        pipeline = self._get_pipeline_raise_error_if_not_exists(pipeline_name, raise_bad_request_if_drafted=False)
        if (
                self.auth_validator.validate(
                    ActionType.EXECUTE_PIPELINE, {"pipelineName": pipeline_name}, acl_relation_list=pipeline.acl
                )
                == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                f"has no permission to execute pipeline with name {pipeline_name}"
            )
        if self.is_pipeline_drafted(pipeline):
            raise BadRequest(
                f"Pipeline with name {pipeline_name} is currently in draft mode and"
                f" cannot be stopped as it could not be run"
            )
        try:
            # get all running dag runs
            pipeline_runs = self.get_and_resolve_airflow_api_client(project_id=pipeline.get_project_owner).get_dag_runs(
                dag_id=pipeline.dag_id, order_by="-execution_date", get_running=True
            )
        except Exception as exc:
            raise NoDataError(f"Dag {pipeline.dag_id} for pipeline with name {pipeline_name} does not exist") from exc
        if pipeline_runs and not pipeline_runs.dag_runs:
            raise BadRequest(
                f"Pipeline with name {pipeline_name} does not have any running dag runs," f" which can be stopped"
            )

        # cycle through running dag runs and stop them
        for dag_run in pipeline_runs.dag_runs:
            try:
                self.get_and_resolve_airflow_api_client(project_id=pipeline.get_project_owner).stop_dag_run(
                    dag_id=pipeline.dag_id, dag_run_id=dag_run.get("dag_run_id"), state=state
                )
            except Exception as exc:
                raise NoDataError(
                    f"Dag {pipeline.dag_id} with dag run id {dag_run.get('dag_run_id')}"
                    f" for pipeline with name {pipeline_name} does not exist"
                ) from exc

    def delete_pipeline(
            self, pipeline_name: str, check_permission: bool = True, commit: bool = True, update: bool = False
    ):
        """
        Delete pipeline
        @param pipeline_name: name of pipeline to delete
        @param check_permission: should check the permission
        @param commit: should commit
        @param update: if update true dont delete dag info
        """
        self.logger.info(f"Start method delete_pipeline with pipeline_name={pipeline_name}")
        # check first if pipeline exist
        pipeline = self._get_pipeline_raise_error_if_not_exists(pipeline_name, raise_bad_request_if_drafted=False)
        # check rights of user
        if check_permission:
            if (
                    self.auth_validator.validate(
                        ActionType.DELETE_PIPELINE, {"pipelineName": pipeline_name}, acl_relation_list=pipeline.acl
                    )
                    == PermissionEffectsEnum.deny
            ):
                raise AuthorizationError(
                    f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                    f"has no permission to delete pipeline with name {pipeline_name}"
                )

        # validate if you are deleting from project that is owner, if not raise error
        if pipeline.get_project_owner != self.project_id:
            raise BadRequest("Currently you are in non-owner project. To delete, switch to owner project.")
        # check if pipeline is drafted, if it is drafted then do not call airflow dag as dag wouldnt exist for drafted
        # pipelines
        if not self.is_pipeline_drafted(pipeline) and not update:
            self.delete_object_from_airflow(pipeline.dag_id)
        # Make an DB call to delete the data in DB
        return self.pipelines_metadata_provider.delete_pipeline(
            pipeline_name=pipeline_name, user_id=self.user_isid, commit=commit
        )

    def check_pipeline_existence(self, pipeline_name: str, pipeline_version: str = "1.0.0") -> bool:
        """
        Check pipeline existence, return True if pipeline does exists, else raises NoDataError

        @param pipeline_name: name of pipeline
        @param pipeline_version: version of pipeline
        """
        self.logger.info(
            f"User {self.user_isid} starts method check_pipeline_existence" f" with pipeline_name={pipeline_name}"
        )
        exists = self.pipelines_metadata_provider.exists_pipeline(pipeline_name, pipeline_version, self.user_isid)
        if not exists:
            raise NoDataError(f"Pipeline with name {pipeline_name} and version {pipeline_version} does not exist")
        return True

    def get_airflow_information(self, pipelines_names: []):
        """
        Obtain airflow information from API
        @param pipelines_names: list of names of pipeline
        method for obtaining airflow status and last run information for list of pipelines
        as the pipeline list is passed in as list of already accessible pipelines for user,
        we do not have to check their existence or validate user rights, however we will check,
        that none of the pipeline got deleted in between the calls - there would be None in the list,
        this is edge case, however with multiple users on FE it is possible it will happen
        """
        self.logger.info(
            f"User {self.user_isid} starts method get_airflow_status" f" with pipelines_names={pipelines_names}"
        )
        pipeline_list_from_db = [
            EntityPipeline.from_metadb_object(self.pipelines_metadata_provider.get_pipeline(pipeline_name))
            for pipeline_name in pipelines_names
        ]
        # we need to check, if any in None is returned from DB, it is possible somebody got time to delete it in between
        pipeline_list = [pipeline_from_db for pipeline_from_db in pipeline_list_from_db if pipeline_from_db is not None]

        pipelines_to_enrich = []
        pipeline_results = []
        for pipeline in pipeline_list:
            if (
                    self.auth_validator.validate(
                        ActionType.READ_PIPELINE, {"pipelineName": pipeline.pipeline_name},
                        acl_relation_list=pipeline.acl
                    )
                    == PermissionEffectsEnum.deny
            ):
                # if user has no rights to read pipeline, we set status to corrupted
                pipeline.set_last_run(None)
                pipeline.set_last_runtime(None)
                pipeline.set_next_run(None)
                pipeline.set_status("corrupted")

                pipeline_results.append(pipeline)
                continue

            pipelines_to_enrich.append(pipeline)

        pipeline_results.extend(self.get_enrich_in_pool_airflow_information(pipelines_to_enrich))

        return pipeline_results

    def get_enrich_in_pool_airflow_information(self, retrieved_pipeline: list):
        """
        Obtain airflow information from API
        @param retrieved_pipeline: list of pipeline from DB which we want to enrich
        as we are obtaining list
        """
        # if for some reason we are not getting anything, we return nothing back
        if not retrieved_pipeline:
            return retrieved_pipeline
        # in case we are requesting only one pipeline name, there is no use for threadpool
        if len(retrieved_pipeline) == 1:
            self._enrich_pipeline_with_airflow_details(retrieved_pipeline[0])
        else:
            # we use map to pass in the list of pipelines for threading
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(self._enrich_pipeline_with_airflow_details, retrieved_pipeline)
        return retrieved_pipeline

    def export_pipeline_to_github_repository(
            self, pipeline_name: str, pipeline_version: str, dataset_repo_location: str, github_branch: str
    ):
        """
        Export pipeline to GitHub repository

        @param pipeline_name: name of pipeline to stop
        @param pipeline_version: version of pipeline
        @param dataset_repo_location: folder location in Github repository, where pipeline will be exported
        @param github_branch: Branch in Github repository, where pipeline will be exported

        """
        self.logger.info(
            f"Start method export_pipeline_to_github_repository. "
            f"Pipeline name={pipeline_name}\n"
            f"Dataset repository location={dataset_repo_location}\n"
            f"Pipeline version={pipeline_version}\n"
            f"Github branch={github_branch}\n"
        )

        # check read permissions and get pipeline model
        pipeline_model = self.get_pipeline_detail(pipeline_name, pipeline_version)
        tmp_folder = "/tmp"
        tmp_folder_prefix = uuid.uuid4().hex
        file_name = "dataset_definition.yaml"
        pom_file_name = "pom.xml"

        # convert the model to yaml
        yaml_definition, _ = self.convert_model_to_yaml(pipeline_model)
        project_general_settings = self.project_settings_management.get_project_general_settings()
        project_group_id = project_general_settings.project_group_id

        # Generate pom content
        pom_file_definition = self.generate_dataset_pom_file(pipeline_name, project_group_id)

        # get project github settings
        github_settings = self.project_settings_management.get_project_account_settings(
            ProjectAccountTypesEnum.github, check_permission=False
        ).to_json_dict()

        if not github_branch:
            github_branch = github_settings.get("defaultBranch")
        if not github_branch:
            raise BadRequest(
                "Branch name is not present. You need to either configure default branch in "
                "github settings or send it in request"
            )

        # create temporary workspace in /tmp folder of aws lambda container
        with tempfile.TemporaryDirectory(prefix=tmp_folder_prefix, dir=tmp_folder) as tmpdir:
            # create pipeline configuration file
            conf_path = f"{tmpdir}{os.path.sep}{pipeline_name}{os.path.sep}conf"
            os.makedirs(conf_path, exist_ok=True)
            with open(f"{conf_path}{os.path.sep}{file_name}", "w", encoding="utf-8") as dataset_file:
                dataset_file.write(f"dataset_name: {pipeline_name}\n")
                dataset_file.write(yaml.dump(yaml_definition))

            # create pom file.
            with open(
                    f"{tmpdir}{os.path.sep}{pipeline_name}{os.path.sep}{pom_file_name}", "w", encoding="utf-8"
            ) as pom_file_name:
                pom_file_name.write(pom_file_definition)

            # upload  the config and pom files to given git branch
            return DatasetRepoUtils(
                github_settings=github_settings,
                secret_management=self.secret_management,
                logger=self.logger,
                workspace=tmpdir,
                folder_to_store=dataset_repo_location,
                branch_name=github_branch,
            ).upload_dataset_file_to_repo(pipeline_name)

    def _get_pipeline_raise_error_if_not_exists(
            self, pipeline_name: str, pipeline_version: str = "1.0.0", raise_bad_request_if_drafted: bool = True
    ) -> EntityPipeline:
        """
        Get pipeline from DB and return NoDataError if not exists

        @param pipeline_name:
        @param pipeline_version:
        @param raise_bad_request_if_drafted: if true then raise bad request if founded pipeline is drafted

        @return: retrieved instance of pipeline
        """
        pipeline = EntityPipeline.from_metadb_object(
            self.pipelines_metadata_provider.get_pipeline(pipeline_name, pipeline_version=pipeline_version)
        )
        if not pipeline:
            raise NoDataError(f"Pipeline with name {pipeline_name} and version {pipeline_version} does not exist")
        if raise_bad_request_if_drafted and self.is_pipeline_drafted(pipeline):
            raise BadRequest(
                f"pipeline with name {pipeline_name} and version {pipeline_version} is currently in draft mode"
            )
        return pipeline

    @staticmethod
    def is_pipeline_drafted(pipeline: EntityPipeline) -> bool:
        """
        Check if pipeline is drafted
        @param pipeline: pipeline object
        @return: True if pipeline is drafted, False otherwise
        """
        return pipeline.is_draft or (pipeline.status and "drafted" in pipeline.status.lower())
