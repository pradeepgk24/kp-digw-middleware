# pylint: skip-file
import concurrent.futures
import tempfile
import uuid
import os
import yaml
from datetime import datetime

from common.helpers.exception import NotFoundError
from middleware.common.configuration.model_converter.workflow_model_to_configuration_converter import (
    WorkflowModelToConfigurationConverter,
)
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_object_run import EntityObjectRun
from middleware.common.entity_management.entities.entity_workflow import EntityWorkflow
from middleware.common.entity_management.entities.entity_workflow_advanced_options import EntityWorkflowAdvancedOptions
from middleware.common.entity_management.objects.owner_filter_enum import OwnerFilterEnum
from middleware.common.entity_management.objects.project_filter_enum import ProjectFilterEnum
from middleware.common.helpers.datetime_formater import from_datetime_to_str
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from middleware.common.metadatabase.workflows_metadata_provider import WorkflowsMetadataProvider
from middleware.api.common.helpers import SortAndPaginate, paginate_entries
from middleware.common.helpers.exception import AuthorizationError, NoDataError, BadRequest, EntityConflictError
from middleware.common.security.action_type import ActionType
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from common.secrets.secrets import register_secret_type
from middleware.common.entity_management.objects_management import ObjectsManagement
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.helpers.dataset_repo_utils import DatasetRepoUtils


class WorkflowsManagement(ObjectsManagement):
    """
    Workflows Management.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._workflows_metadata_provider = None
        # setup tokens
        aws_access_key, aws_secret_key, aws_session_token = (
            self.project_settings_management.get_project_aws_account_access_info()
        )
        self.set_aws_tokens(aws_access_key, aws_secret_key, aws_session_token)
        self.project_settings_management.project_id = self.project_id
        # register secret manager to work with secrets within Yaml
        register_secret_type()

    @property
    def workflows_metadata_provider(self):
        """
        workflows metadata provider
        """
        if self._workflows_metadata_provider is None:
            self._workflows_metadata_provider = WorkflowsMetadataProvider(
                self.logger, self.metadatabase_connection, self.lambda_secrets_manager
            )
        return self._workflows_metadata_provider

    @property
    def model_converter(self) -> WorkflowModelToConfigurationConverter:
        """
        Model converter property
        """
        if not self._model_converter:
            self._model_converter = WorkflowModelToConfigurationConverter(self.logger, self.secret_management)
        return self._model_converter

    def _enrich_workflow_with_airflow_details(self, entity_workflow: EntityWorkflow):
        """
        Enrich entity workflow with details from airflow.

        @param entity_workflow: EntityWorkflow object to enrich
        """
        if entity_workflow.is_draft:
            entity_workflow.set_status("drafted")
        elif entity_workflow.dag_id:
            self.logger.info(
                f"The workflow {entity_workflow.workflow_name} "
                f"exists in Airflow, info from Airflow will be retrieved."
            )
            # obtain airflow details of pipeline based on dag and its project owner
            next_dag_run, start_date, last_runtime, status = self._get_object_airflow_details(
                entity_workflow.dag_id, entity_workflow.get_project_owner
            )
            entity_workflow.set_status(status)
            entity_workflow.set_last_run(start_date)
            entity_workflow.set_last_runtime(last_runtime)
            entity_workflow.set_next_run(next_dag_run)
        # edge case which shows that the workflow is not well-defined - not drafted and missing dag
        else:
            self.logger.info(
                f"Pipeline with name {entity_workflow.workflow_name}" f" is not drafted and does not have dag id."
            )
            # we could raise error, but when called via concurrent.futures this error will not be propagated
            # it is better to show user, that there is issue with the workflow
            entity_workflow.set_status("corrupted")

    def get_workflow_detail(
            self,
            workflow_name: str,
            workflow_version: str = "1.0.0",
            framework_version: str = "2.8.0-SNAPSHOT",
            orchestrator_info: bool = False,
    ) -> EntityWorkflow:
        """
        Get workflow details

        @param: workflow_name: name of workflow
        @param: workflow_version: version of workflow
        @param: orchestrator_info: flag indicates if orchestration info is needed
        """
        self.logger.info(f"Start method get_workflow_detail with workflow_name={workflow_name}")
        self.logger.info(f"User {self.user_isid} starts method get_workflow_detail with workflow_name={workflow_name}")
        if workflow_name == "default_workflow":
            return self.get_workflow_default_project_values(framework_version)
        retrieved_workflow = self._get_workflow_raise_error_if_not_exists(
            workflow_name, workflow_version, raise_bad_request_if_drafted=False
        )
        if (
                self.auth_validator.validate(
                    ActionType.READ_WORKFLOW, {"workflowName": workflow_name}, acl_relation_list=retrieved_workflow.acl
                )
                == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                f"has no permission to read workflow with name {workflow_name}"
            )

        if orchestrator_info:
            self._enrich_workflow_with_airflow_details(retrieved_workflow)
        return retrieved_workflow

    def get_workflow_details(self, workflow_name: str = None, is_enabled: bool = None, owner: OwnerFilterEnum = None,
                             limited_view: bool = False, sort_and_paginate: SortAndPaginate = None,
                             orchestrator_info: bool = True, project_filter: ProjectFilterEnum = None,
                             ) -> ([EntityWorkflow], int):
        """
        Get workflow details

        @param workflow_name: name of workflow
        @param is_enabled: flag indicates if workflow is enabled or disabled
        @param owner: owner of workflow
        @param limited_view
        @param sort_and_paginate
        @param orchestrator_info: flag if we should get airflow information
        @param project_filter: filter for project visibility

        @return - list of EntityWorkflows and total number of entries in DB
        """
        self.logger.info(f"Start method get_workflow_details")
        workflows = EntityWorkflow.from_metadb_objects(
            self.workflows_metadata_provider.get_workflows(user_id=self.user_isid,
                                                           subject_ids=self.selected_subject_ids,
                                                           workflow_name=workflow_name, is_enabled=is_enabled,
                                                           owner=self.user_isid if owner ==
                                                                                   OwnerFilterEnum.current else None,
                                                           sort_and_paginate=sort_and_paginate,
                                                           project_id=self.project_id
                                                           if project_filter == ProjectFilterEnum.current else None
                                                           ))
        accessible_workflows = []
        for workflow in workflows:
            if (
                    self.auth_validator.validate(
                        ActionType.READ_WORKFLOW, {"workflowName": workflow.workflow_name},
                        acl_relation_list=workflow.acl
                    )
                    == PermissionEffectsEnum.deny
            ):
                continue
            accessible_workflows.append(workflow)
        if not accessible_workflows:
            raise NoDataError(
                f"There are no existing workflows, which are accessible for user {self.user_isid}"
                f" within group {self.group_id} and project {self.project_id} based on given filters"
            )

        total_count = len(accessible_workflows)
        accessible_workflows_paginated = paginate_entries(accessible_workflows, sort_and_paginate)
        if orchestrator_info:
            for workflow in accessible_workflows_paginated:
                self._enrich_workflow_with_airflow_details(workflow)
        workflow_result_list = [workflow.to_json_dict(limited_view) for workflow in accessible_workflows_paginated]

        return workflow_result_list, total_count

    def get_workflow_runs(self, workflow_name: str, max_result: int) -> [EntityObjectRun]:
        """
        Get workflow run  details

        @param: workflow_name: name of workflow
        @param: max_result:

        @return: list of workflow runs
        """
        self.logger.info(f"Start method get_workflow_runs with workflow_name={workflow_name}")
        workflow = self._get_workflow_raise_error_if_not_exists(workflow_name, raise_bad_request_if_drafted=False)
        # call Airflow api to get the run details
        return self.get_objects_runs(
            dag_id=workflow.dag_id, max_result=max_result, project_id=workflow.get_project_owner
        )

    def get_tasks_of_object_runs(self, workflow_name: str, dag_run_id: str) -> [EntityObjectRun]:
        """
        Get tasks of runs of workflows

        @param workflow_name: name of workflow
        @param dag_run_id: run id of dag

        @return: list of EntityObjectTaskOfRun
        """
        self.logger.info(
            f"Start method get_tasks_of_object_runs for workflow_name={workflow_name} and dag_run_id={dag_run_id}"
        )
        workflow = self._get_workflow_raise_error_if_not_exists(workflow_name, raise_bad_request_if_drafted=False)
        return self.get_tasks_of_object_runs_from_api(
            dag_id=workflow.dag_id, dag_run_id=dag_run_id, project_id=workflow.get_project_owner
        )

    def get_logs_of_task(self, workflow_name: str, dag_run_id: str, task_id: str, try_number: int) -> str:
        """
        Get logs of workflow task

        @param workflow_name: name of workflow
        @param dag_run_id: run id of dag
        @param task_id: task id
        @param try_number: try number

        @return: logs
        """
        self.logger.info(
            f"Start method get_logs_of_task for workflow_name={workflow_name}, dag_run_id={dag_run_id}, "
            f"task_id={task_id}, try_number={try_number}"
        )
        workflow = self._get_workflow_raise_error_if_not_exists(workflow_name, raise_bad_request_if_drafted=False)
        return self.get_logs_of_task_from_api(
            dag_id=workflow.dag_id,
            dag_run_id=dag_run_id,
            task_id=task_id,
            try_number=try_number,
            project_id=workflow.get_project_owner,
        )

    def create_workflow(self, entity_workflow: EntityWorkflow) -> EntityWorkflow:
        """
        Create workflow

        @param: entity_workflow: workflow entity to create
        @return: entity workflow
        """
        self.logger.info(f"Start method create_workflow")
        if self.auth_validator.validate(ActionType.CREATE_WORKFLOW, {}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                "has no permission to create workflow"
            )

        self.logger.info("User is authorized and can continue with creation of workflow")
        self.logger.info(f"Going to create workflow with name {entity_workflow.workflow_name}")

        if self.workflows_metadata_provider.exists_workflow(
                entity_workflow.workflow_name, entity_workflow.workflow_version
        ):
            raise EntityConflictError(
                f"Workflow with name {entity_workflow.workflow_name} "
                f"and version {entity_workflow.workflow_version} exists"
            )
        return self._upsert_workflow(entity_workflow=entity_workflow, is_update=False)

    def update_workflow(self, entity_workflow: EntityWorkflow) -> EntityWorkflow:
        """
        Update workflow

        @param: workflow: workflow entity to update
        @return: name of updated workflow
        """
        self.logger.info("Start method update_workflow")
        self._check_update_of_workflow(entity_workflow.workflow_name, entity_workflow.workflow_version)
        # upsert workflow now
        return self._upsert_workflow(entity_workflow=entity_workflow, is_update=True)

    def _check_update_of_workflow(self, workflow_name, workflow_version):
        """
        Check if update of workflow is possible. Within the method is checking:
        1. If workflow exists
        2. ACL
        3. Permission to update workflow within acl
        4. If the current project is owner of the workflow, if it is not, we are raising error

        @param workflow_name: name of workflow to update
        @param workflow_version: version of workflow

        @return: workflow ACL
        """
        if not self.workflows_metadata_provider.exists_workflow(workflow_name, workflow_version):
            raise NoDataError(f"Workflow with name {workflow_name} and version {workflow_version} does not exist")
        # first retrieve ACLs to check permissions of this workflow
        workflow_acls = EntityACL.from_metadb_object_objects_acls(
            self.workflows_metadata_provider.get_workflow_acl(workflow_name, user_id=self.user_isid)
        )
        if (
                self.auth_validator.validate(
                    ActionType.UPDATE_WORKFLOW, {"workflowName": workflow_name}, acl_relation_list=workflow_acls
                )
                == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                "has no permission to update workflow"
            )
        # filter pipeline acls with current project id and owner relation type
        # if the return is empty list, current project is not owner one and as such we can not edit
        if not EntityACL.filter_entity_acls(
                entity_acl_objects=workflow_acls,
                relation_type=ObjectsACLRelationTypesEnum.owner,
                subjects_ids=[self.project_id],
        ):
            raise BadRequest("Currently you are in non-owner project. To update, switch to owner project.")

        return workflow_acls

    @staticmethod
    def is_workflow_drafted(workflow: EntityWorkflow) -> bool:
        """
        Check if workflow is drafted
        @param workflow: workflow object
        @return: True if workflow is drafted, False otherwise
        """
        return workflow.is_draft or (workflow.status and "drafted" in workflow.status.lower())

    def _upsert_workflow(self, entity_workflow: EntityWorkflow, is_update=False):
        """
        Upsert workflow. Upsertion include actions in resources and actions in db

        @param entity_workflow: Workflow entity to update
        @param is_update: Flag indicates if workflow needs to be update or not
        """

        if not entity_workflow.dag_id:
            # disable by default. also it is disabled within model configuration converter
            # if there is no is_paused_upon_creation in pipeline, we disable it by default, airflow disables it too
            entity_workflow.set_is_enabled(
                not entity_workflow.advanced_options.entity_airflow_options.dag_instance_parameters.get(
                    "is_paused_upon_creation", True
                )
            )

        self.logger.info("Generate workflow definition,...")
        if not self.is_workflow_drafted(entity_workflow):
            # convert configuration file first
            workflow_definition, _ = self.convert_model_to_yaml(entity_workflow)

            # check existence of the airflow pool or create it
            self.check_or_create_airflow_pool(
                airflow_advanced_settings=entity_workflow.advanced_options.entity_airflow_options
            )

            tmp_folder = "/tmp"
            tmp_folder_prefix = uuid.uuid4().hex
            workflow_name = entity_workflow.workflow_name
            environment = self.project_settings_management.get_project_environment()
            # create temporary workspace in /tmp folder of aws lambda container
            with tempfile.TemporaryDirectory(prefix=tmp_folder_prefix, dir=tmp_folder) as tmpdir:
                self.logger.info("Generate yaml configuration,...")
                # create configuration file
                self.create_yaml_configuration_file(workflow_name, tmpdir, workflow_definition)

                self.logger.info("Run airflow generator,...")

                airflow_link, dag_name = self.process_orchestration(
                    **{
                        "tmpdir": tmpdir,
                        "dataset_name": workflow_name,
                        "environment": environment,
                        "framework_version": entity_workflow.framework_version,
                    }
                )
                entity_workflow.set_airflow_link(airflow_link)
                entity_workflow.set_dag_id(dag_name)

        if not is_update:
            # we need to remove component id from components, as they will be placed into component tables
            # with new unique ID
            entity_workflow.clean_step_identifiers()
            # add owner into workflow
            entity_workflow.acl.extend(self.create_objects_owner_acls())
        else:
            # obtain old acls and keep only owners from them, all shared will be dropped and replaced with new
            workflow_acls = EntityACL.from_metadb_object_objects_acls(
                self.workflows_metadata_provider.get_workflow_acl(entity_workflow.workflow_name, user_id=self.user_isid)
            )
            # we need to obtain previous owners and shared_template acls, as we do need to add them to the acl
            owners = EntityACL.filter_entity_acls(workflow_acls, ObjectsACLRelationTypesEnum.owner)
            # add owners into the pipeline entity
            entity_workflow.acl.extend(owners)
            # delete the old workflow
            self.delete_workflow(
                workflow_name=entity_workflow.workflow_name, check_permission=False, commit=False, update=True
            )

        # going to be draft therefore it is disabled by default
        if self.is_workflow_drafted(entity_workflow):
            entity_workflow.set_is_enabled(False)
            # but it can run before
            if entity_workflow.dag_id:
                # disable airflow dag
                self.get_and_resolve_airflow_api_client(project_id=self.project_id).pause_or_unpause_dag(
                    dag_id=entity_workflow.dag_id, pause_flag=True
                )

        db_object, db_object_components = entity_workflow.to_metadb_object()
        self.workflows_metadata_provider.insert_or_update_workflow(
            db_object, db_object_components, is_update=is_update, user_id=self.user_isid
        )
        return entity_workflow

    def delete_workflow(
            self, workflow_name: str, check_permission: bool = True, commit: bool = True, update: bool = False
    ):
        """
        Delete workflow
        @param workflow_name: name of workflow to delete
        @param check_permission: should check the permission
        @param commit: should commit
        @param update: if update true dont delete dag info
        """
        self.logger.info(f"Start method delete_workflow with workflow_name={workflow_name}")
        # check first if workflow exist
        workflow_entity = self._get_workflow_raise_error_if_not_exists(
            workflow_name, raise_bad_request_if_drafted=False
        )
        # check rights of user
        if check_permission:
            if (
                    self.auth_validator.validate(
                        ActionType.DELETE_WORKFLOW, {"workflowName": workflow_name},
                        acl_relation_list=workflow_entity.acl
                    )
                    == PermissionEffectsEnum.deny
            ):
                raise AuthorizationError(
                    f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                    f"has no permission to delete workflow with name {workflow_name}"
                )
        # validate if you are deleting from project that is owner, if not raise error
        if workflow_entity.get_project_owner != self.project_id:
            raise BadRequest("Currently you are in non-owner project. To delete, switch to owner project.")
        # check if workflow is drafted, if it is drafted then do not call airflow dag as dag wouldnt exist for drafted
        # workflows
        if not self.is_workflow_drafted(workflow_entity) and not update:
            self.delete_object_from_airflow(workflow_entity.dag_id)
        # Make an DB call to delete the data in DB
        return self.workflows_metadata_provider.delete_workflow(
            workflow_name=workflow_name, user_id=self.user_isid, commit=commit
        )

    def update_schedule(self, workflow_name: str, schedule_cron: str, workflow_version: str = "1.0.0"):
        """
        Update schedule

        @param: workflow_name: name of workflow to update
        @param: schedule_cron: cron to update for schedule or "None"
        @param: workflow_version: version of workflow
        """
        self.logger.info(
            f"Start method update_schedule. Schedule cron = {schedule_cron}. workflow name={workflow_name}"
        )
        # check if the given workflow exists in DB, if not then raise 404.
        self._check_update_of_workflow(workflow_name, workflow_version)
        # change it in configuration provider
        self.update_key_in_configuration_provider(
            object_name=workflow_name, key_to_rewrite="schedule", new_value=schedule_cron
        )
        # update schedule in DB
        self.workflows_metadata_provider.update_schedule(
            workflow_name, schedule_cron, self.user_isid, workflow_version, ObjectTypesEnum.workflow
        )

    def update_workflow_acl(self, workflow_name: str, workflow_acls: [EntityACL], workflow_version: str = "1.0.0"):
        """
        Update acl of workflow

        @param: workflow_name: name of workflow to update
        @param: workflow_acls: list of acl to update
        """
        self.logger.info(f"Start method update_workflow_acl. ACLs = {workflow_acls}. workflow name={workflow_name}")
        # check if the given workflow exists in DB, if not then raise 404.
        self._check_update_of_workflow(workflow_name, workflow_version)
        self.workflows_metadata_provider.update_workflow_assigned_acl_list(
            workflow_name=workflow_name, acls=workflow_acls, workflow_version=workflow_version, user_id=self.user_isid
        )

    def update_workflow_enable_flag(self, workflow_name: str, enable_flag: bool, workflow_version: str = "1.0.0"):
        """
        Update enablement/disablement of workflow

        @param: workflow_name: name of workflow to update
        @param: enable_flag: enable flag
        """
        self.logger.info(
            f"Start method update_workflow_enable_flag. Enablement flag={enable_flag}. workflow name={workflow_name}"
        )
        # check if the given workflow exists in DB , if not then raise 404.
        self._check_update_of_workflow(workflow_name, workflow_version)
        dag_name = self.workflows_metadata_provider.get_workflow_dag_name(
            workflow_name, workflow_version, self.user_isid
        )
        # change it in Airflow
        # enable = True mean that is_paused = False
        self.get_and_resolve_airflow_api_client(project_id=self.project_id).pause_or_unpause_dag(
            dag_name, not enable_flag
        )
        # update enable flag in DB
        self.workflows_metadata_provider.update_workflow_enable_flag(
            workflow_name, self.user_isid, workflow_version, enable_flag
        )

    def convert_model_to_yaml(self, entity_workflow: EntityWorkflow) -> (dict, str):
        """
        Convert workflow to yaml configuration

        @param: entity_workflow: model to convert to yaml
        @return: a pair of dict as represent yaml configuration and str as re-presenter of workflow name
        """
        self.logger.info("Start method convert_model_to_yaml")
        platform_configuration = {
            ProjectAccountTypesEnum.aws: self.aws_account_settings,
            ProjectAccountTypesEnum.airflow: self.airflow_account_settings,
        }
        return (
            self.model_converter.convert_model_to_yaml_config(
                input_entity=entity_workflow,
                workflow_name=entity_workflow.workflow_name,
                platform_configuration=platform_configuration,
                region=self.aws_region,
            ),
            entity_workflow.workflow_name,
        )

    def start_workflow(self, workflow_name: str, logical_date: datetime = None):
        """
        Start workflow

        @param: workflow_name: name of workflow to start
        @param: logical_date: logical date
        """
        self.logger.info(f"Start method start_workflow. workflow name={workflow_name}\n" f"logical date={logical_date}")
        # check if workflow exists, retrieve it from DB
        workflow = self._get_workflow_raise_error_if_not_exists(workflow_name, raise_bad_request_if_drafted=False)
        if (
                self.auth_validator.validate(
                    ActionType.EXECUTE_WORKFLOW, {"workflowName": workflow_name}, acl_relation_list=workflow.acl
                )
                == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                f"has no permission to execute workflow with name {workflow_name}"
            )
        if self.is_workflow_drafted(workflow):
            raise BadRequest(
                f"Forbidden Action: Workflow with name {workflow_name} is currently in draft mode "
                f"and cannot be triggered"
            )
        # trigger the DAG with
        self.logger.info(f"Going to start workflow {workflow_name}")
        run_conf_data = {}
        # in case, if logical date is not None, then add it to request body
        if logical_date:
            run_conf_data = {"logical_date": from_datetime_to_str(logical_date)}
        try:
            return self.get_and_resolve_airflow_api_client(project_id=workflow.get_project_owner).trigger_dag_run(
                dag_id=workflow.dag_id, run_conf_data=run_conf_data
            )
        except NotFoundError as exc:
            raise NoDataError(f"Dag {workflow.dag_id} for workflow with name {workflow_name} does not exist") from exc

    def stop_workflow(self, workflow_name: str, state: str):
        """
        Stop workflow

        @param: workflow_name: name of workflow to stop
        @param: state into which the workflow will be stopped
        """
        self.logger.info(f"Start method stop_workflow for workflow with name {workflow_name}")
        workflow = self._get_workflow_raise_error_if_not_exists(workflow_name, raise_bad_request_if_drafted=False)
        if (
                self.auth_validator.validate(
                    ActionType.EXECUTE_WORKFLOW, {"workflowName": workflow_name}, acl_relation_list=workflow.acl
                )
                == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                f"has no permission to execute workflow with name {workflow_name}"
            )
        if self.is_workflow_drafted(workflow):
            raise BadRequest(
                f"Forbidden Action: Workflow with name {workflow_name} is currently in draft mode and"
                f" cannot be stopped as it could not be run"
            )
        try:
            # get all running dag runs
            workflow_runs = self.get_and_resolve_airflow_api_client(project_id=workflow.get_project_owner).get_dag_runs(
                dag_id=workflow.dag_id, order_by="-execution_date", get_running=True
            )
        except Exception as exc:
            raise NoDataError(f"Dag {workflow.dag_id} for workflow with name {workflow_name} does not exist") from exc
        # raise error if there are no running
        if workflow_runs and not workflow_runs.dag_runs:
            raise BadRequest(
                f"Workflow with name {workflow_name} does not have any running dag runs," f" which can be stopped"
            )
        # cycle through running dag runs and stop them
        for dag_run in workflow_runs.dag_runs:
            try:
                self.get_and_resolve_airflow_api_client(project_id=workflow.get_project_owner).stop_dag_run(
                    dag_id=workflow.dag_id, dag_run_id=dag_run.get("dag_run_id"), state=state
                )
            except Exception as exc:
                raise NoDataError(
                    f"Dag {workflow.dag_id} with dag run id {dag_run.get('dag_run_id')}"
                    f" for workflow with name {workflow_name} does not exist"
                ) from exc

    def export_workflow_to_github_repository(
            self, workflow_name: str, workflow_version: str, dataset_repo_location: str, github_branch: str
    ):
        """
        Export workflow to GitHub repository

        @param: workflow_name: name of workflow to export
        @param: workflow_version: version of workflow
        @param: dataset_repo_location: folder location in GitHub repository, where workflow will be exported
        @param: github_branch: Branch in GitHub repository, where workflow will be exported

        """
        self.logger.info(f"Start method export_workflow_to_github_repository. "
                         f"workflow name={workflow_name}\n"
                         f"Dataset repository location={dataset_repo_location}\n"
                         f"workflow version={workflow_version}\n"
                         f"Github branch={github_branch}\n")

        # check read permissions and get pipeline model
        workflow_model = self.get_workflow_detail(workflow_name, workflow_version)
        tmp_folder = "/tmp"
        tmp_folder_prefix = uuid.uuid4().hex
        file_name = "dataset_definition.yaml"
        pom_file_name = "pom.xml"

        # convert the model to yaml
        yaml_definition, _ = self.convert_model_to_yaml(workflow_model)
        project_general_settings = self.project_settings_management.get_project_general_settings()
        project_group_id = project_general_settings.project_group_id

        # Generate pom content
        pom_file_definition = self.generate_dataset_pom_file(workflow_name, project_group_id)

        # get project github settings
        github_settings = self.project_settings_management. \
            get_project_account_settings(ProjectAccountTypesEnum.github, check_permission=False).to_json_dict()

        if not github_branch:
            github_branch = github_settings.get("defaultBranch")
        if not github_branch:
            raise BadRequest("Branch name is not present. You need to either configure default branch in "
                             "github settings or send it in request")
        # create temporary workspace in /tmp folder of aws lambda container
        with tempfile.TemporaryDirectory(prefix=tmp_folder_prefix, dir=tmp_folder) as tmpdir:
            # create workflow configuration file
            conf_path = f'{tmpdir}{os.path.sep}{workflow_name}{os.path.sep}conf'
            os.makedirs(conf_path, exist_ok=True)
            with open(f"{conf_path}{os.path.sep}{file_name}", 'w', encoding='utf-8') as dataset_file:
                dataset_file.write(f"dataset_name: {workflow_name}\n")
                dataset_file.write(yaml.dump(yaml_definition))

            # create pom file.
            with open(f"{tmpdir}{os.path.sep}{workflow_name}{os.path.sep}{pom_file_name}", 'w',
                      encoding='utf-8') as pom_file_name:
                pom_file_name.write(pom_file_definition)

            # upload  the config and pom files to given git branch
            return DatasetRepoUtils(github_settings=github_settings, secret_management=self.secret_management,
                                    logger=self.logger, workspace=tmpdir,
                                    folder_to_store=dataset_repo_location,
                                    branch_name=github_branch).upload_dataset_file_to_repo(workflow_name)

    def get_airflow_information(self, workflow_names: []):
        """
        Obtain airflow information from API
        @param workflow_names: list of names of workflows
        method for obtaining airflow status and last run information for list of workflows
        as the workflow list is passed in as list of already accessible workflows for user,
        we do not have to check their existence or validate user rights, however we will check,
        that none of the workflow got deleted in between the calls - there would be None in the list,
        this is edge case, however with multiple users on FE it is possible it will happen
        """
        self.logger.info(
            f"User {self.user_isid} starts method get_airflow_status" f" with workflow_names={workflow_names}"
        )
        workflow_list_from_db = [
            EntityWorkflow.from_metadb_object(self.workflows_metadata_provider.get_workflow(workflow_name))
            for workflow_name in workflow_names
        ]
        # we need to check, if any in None is returned from DB, it is possible somebody got time to delete it in between
        workflow_list = [workflow_from_db for workflow_from_db in workflow_list_from_db if workflow_from_db is not None]

        workflows_to_enrich = []
        workflows_results = []
        for workflow in workflow_list:
            if (
                    self.auth_validator.validate(
                        ActionType.READ_WORKFLOW, {"workflowName": workflow.workflow_name},
                        acl_relation_list=workflow.acl
                    )
                    == PermissionEffectsEnum.deny
            ):
                # if user has no rights to read the workflow, we set status to corrupted
                workflow.set_last_run(None)
                workflow.set_last_runtime(None)
                workflow.set_next_run(None)
                workflow.set_status("corrupted")

                workflows_results.append(workflow)
                continue

            workflows_to_enrich.append(workflow)

        workflows_results.extend(self.get_enrich_in_pool_airflow_information(workflows_to_enrich))

        return workflows_results

    def get_enrich_in_pool_airflow_information(self, retrieved_workflow: list):
        """
        Obtain airflow information from API
        @param retrieved_workflow: list of workflows from DB which we want to enrich
        as we are obtaining list
        """
        # if for some reason we are not getting anything, we return nothing back
        if not retrieved_workflow:
            return retrieved_workflow
        # in case we are requesting only one workflow name, there is no use for threadpool
        if len(retrieved_workflow) == 1:
            self._enrich_workflow_with_airflow_details(retrieved_workflow[0])
        else:
            # we use map to pass in the list of workflows for threading
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(self._enrich_workflow_with_airflow_details, retrieved_workflow)
        return retrieved_workflow

    def check_workflow_existence(self, workflow_name: str, workflow_version: str = "1.0.0") -> bool:
        """
        Check workflow existence, return True if workflow does exist, else raise NoDataError

        @param workflow_name: name of workflow
        @param workflow_version: version of workflow
        """
        self.logger.info(
            f"User {self.user_isid} starts method check_workflow_existence" f" with workflow_name={workflow_name}"
        )
        # for solving sonarqube issues the response mock directly raises error
        exists = self.workflows_metadata_provider.exists_workflow(workflow_name, workflow_version, self.user_isid)
        if not exists:
            raise NoDataError(f"Workflow with name {workflow_name} and version {workflow_version} does not exist")
        return True

    def _get_workflow_raise_error_if_not_exists(
            self, workflow_name: str, workflow_version: str = "1.0.0", raise_bad_request_if_drafted: bool = True
    ) -> EntityWorkflow:
        """
        Get workflow from DB and return NoDataError if not exists

        @param workflow_name:
        @param workflow_version:
        @param raise_bad_request_if_drafted: if true then raise bad request if founded workflow is drafted

        @return: retrieved instance of workflow
        """
        workflow = EntityWorkflow.from_metadb_object(
            self.workflows_metadata_provider.get_workflow(workflow_name, workflow_version=workflow_version)
        )
        if not workflow:
            raise NoDataError(f"Workflow with name {workflow_name} and version {workflow_version} does not exist")
        if raise_bad_request_if_drafted and workflow.is_draft:
            raise BadRequest(
                f"Workflow with name {workflow_name} and version {workflow_version} " f"is currently in draft mode"
            )
        return workflow

    def get_workflow_default_project_values(self, framework_version) -> EntityWorkflow:
        """
        Get default project values when workflow name = default_workflow. only airflow settings
        @param framework_version
        @return: returns entity workflow with default values of airflow settings based on project settings
        @rtype: EntityWorkflow
        """
        default_advanced_options = {"airflowSettings": {"dagInstanceParameters": {"is_paused_upon_creation": "False"}}}
        # get resource prefix  from project general settings.
        project_general_settings = self.project_settings_management.get_project_general_settings()
        default_resource_prefix_setting = (
            project_general_settings.resource_prefix
            if project_general_settings.resource_prefix
            else "data_ingest_{{dataset_name}}"
        )
        # get the default workflow project values.
        default_workflow_details = EntityWorkflow(
            workflow_name="Workflow_name",
            workflow_version="1.0.0",
            status="drafted",
            framework_version=framework_version,
            resource_prefix=default_resource_prefix_setting,
            enable_deffer_operators=False,
        )
        # get project settings for airflow
        default_advanced_options["airflowSettings"].update(
            self.project_settings_management.get_project_account_settings(
                ProjectAccountTypesEnum.airflow, check_permission=False
            ).account_details
        )
        default_workflow_details.set_advanced_options(
            EntityWorkflowAdvancedOptions.from_json_dict(default_advanced_options)
        )
        return default_workflow_details
