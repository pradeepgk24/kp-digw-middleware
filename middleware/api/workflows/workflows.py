# pylint: skip-file
import json

import yaml
from croniter import croniter

from middleware.api.common.helpers import get_env_or_header_value, SortAndPaginate, convert_to_bool
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_workflow import EntityWorkflow
from middleware.common.entity_management.objects.owner_filter_enum import OwnerFilterEnum
from middleware.common.entity_management.objects.project_filter_enum import ProjectFilterEnum
from middleware.common.entity_management.workflows_management import WorkflowsManagement
from middleware.api.common.http_method_utils import create_error_response
from middleware.common.helpers.datetime_formater import from_str_to_datetime
from middleware.common.helpers.exception import BadRequest, NoDataError


class WorkflowsLambda(AWSLambdaEventHandler):
    """
    Lambda class for Workflows API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.workflow_management = WorkflowsManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)

    def _invoke_get_workflow_detail(self):
        """
        Invoke method call get workflow detail

        @return: API response of get workflow detail
        """
        self.logger.info("Calling _invoke_get_workflow_detail")
        workflow_name = self.event.path_parameters.get("workflowName")
        orchestrator_info = True if self.event.query_string_parameters.get("orchestratorInfo",
                                                                           None) is None else convert_to_bool(
            self.event.query_string_parameters.get("orchestratorInfo"))
        response_object = self.workflow_management.get_workflow_detail(workflow_name=workflow_name,
                                                                       orchestrator_info=orchestrator_info,
                                                                       framework_version=self.event.headers.get(
                                                                           'difw-core-version'
                                                                       ))
        return {'statusCode': 200, 'body': json.dumps(response_object.to_json_dict())}

    def _invoke_get_workflow_details(self):
        """
        Invoke method call get workflow details

        @return: API response of get workflow details
        """
        self.logger.info("Calling _invoke_get_workflows_details")
        sort_and_paginate = SortAndPaginate(self.event.query_string_parameters)
        orchestrator_info = True if self.event.query_string_parameters.get("orchestratorInfo",
                                                                           None) is None else convert_to_bool(
            self.event.query_string_parameters.get("orchestratorInfo"))

        # Validate project filter
        try:
            project_filter = ProjectFilterEnum.from_str(self.event.query_string_parameters.get('project', None))
        except AttributeError as exc:
            raise BadRequest(f"Project filter has to be one of {ProjectFilterEnum.get_values()}") from exc

        # Validate owner filter
        try:
            owner_filter = OwnerFilterEnum.from_str(self.event.query_string_parameters.get('owner', None))
        except AttributeError as exc:
            raise BadRequest(f"Owner filter has to be one of {OwnerFilterEnum.get_values()}") from exc

        workflows, total_count = self.workflow_management.get_workflow_details(
            limited_view=convert_to_bool(self.event.query_string_parameters.get('limitedView', False)),
            workflow_name=self.event.query_string_parameters.get('workflowName', None),
            is_enabled=convert_to_bool(self.event.query_string_parameters.get('isEnabled')),
            owner=owner_filter,
            sort_and_paginate=sort_and_paginate,
            orchestrator_info=orchestrator_info,
            project_filter=project_filter,
        )
        return {'statusCode': 200, 'body': json.dumps(
            self.create_list_response(workflows, sort_and_paginate, total_count))}

    def _invoke_get_workflow_runs(self):
        """
        Invoke method call get workflow runs

        @return: API response of get workflow templates
        """
        self.logger.info("Calling _invoke_get_workflow_runs")
        workflow_runs = self.workflow_management.get_workflow_runs(
            workflow_name=self.event.path_parameters.get('workflowName', None),
            max_result=int(self.event.query_string_parameters.get('maxResult', 30))
        )
        if not workflow_runs:
            raise NoDataError(
                f"There are not workflow runs for workflow {self.event.path_parameters.get('workflowName', None)}")
        return {'statusCode': 200,
                'body': json.dumps({"items": [workflow_run.to_json_dict() for workflow_run in workflow_runs]})}

    def _invoke_get_tasks_of_workflow_runs(self):
        """
        Invoke method to get workflow tasks of runs

        :return: API response
        """
        self.logger.info("Calling _invoke_get_tasks_of_workflow_runs")
        workflow_tasks = self.workflow_management.get_tasks_of_object_runs(
            workflow_name=self.event.path_parameters.get('workflowName', None),
            dag_run_id=self.event.path_parameters.get('runId', None)
        )
        if not workflow_tasks:
            raise NoDataError(
                f"There are not workflow tasks for workflow {self.event.path_parameters.get('workflowName', None)}")
        return {'statusCode': 200,
                'body': json.dumps({"items": [workflow_task.to_json_dict() for workflow_task in workflow_tasks]})}

    def _invoke_get_workflow_task_log(self):
        """
        Invoke method to get task of log

        :return: API response
        """
        self.logger.info("Calling _invoke_get_workflow_task_log")
        logs = self.workflow_management.get_logs_of_task(
            workflow_name=self.event.path_parameters.get('workflowName', None),
            dag_run_id=self.event.path_parameters.get('runId', None),
            task_id=self.event.path_parameters.get('taskId', None),
            try_number=int(self.event.path_parameters.get('tryNumber', 1))
        )
        if not logs:
            raise NoDataError(
                f"There are not logs for workflow {self.event.path_parameters.get('workflowName', None)}"
                f" and run {self.event.path_parameters.get('runId', None)}")
        return {'statusCode': 200, 'body': logs}

    def _invoke_create_workflow(self):
        """
        Invoke method call create workflow

        @return: API response of create workflow
        """
        self.logger.info("Calling _invoke_create_workflow")
        inserted_workflow = self.workflow_management.create_workflow(
            EntityWorkflow.from_json_dict(self.event.json_body)
        )
        state_message = "created as draft" if inserted_workflow.is_draft else "fully created"
        return {'statusCode': 201, 'body': json.dumps(
            {"result": "Created",
             "workflowName": inserted_workflow.workflow_name,
             "details": f"Workflow with name {inserted_workflow.workflow_name} was {state_message}"}
        )}

    def _invoke_update_workflow(self):
        """
        Invoke method call update workflow

        @return: API response of update workflow
        """
        self.logger.info("Calling _invoke_update_workflow")
        json_body = self.event.json_body
        # enhance by name of the workflow
        json_body["workflowName"] = self.event.path_parameters["workflowName"]
        entity_workflow = EntityWorkflow.from_json_dict(json_body)
        updated_workflow = self.workflow_management.update_workflow(entity_workflow)
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "Updated",
             "workflowName": updated_workflow.workflow_name,
             "details": f"Workflow with name {updated_workflow.workflow_name} was updated"}
        )}

    def _invoke_delete_workflow(self):
        """
        Invoke method call delete workflow

        @return: API response of delete workflow
        """
        self.logger.info("Calling _invoke_delete_workflow")
        workflow_name = self.event.path_parameters["workflowName"]
        self.workflow_management.delete_workflow(workflow_name)
        return {'statusCode': 200, 'body': json.dumps({"result": "Deleted", "workflowName": workflow_name,
                                                       "details": f"Workflow with name {workflow_name} was deleted"})}

    def _invoke_partial_update_workflow(self):
        """
        Invoke method call to partial update of workflow

        @return: API response to partial update workflow
        """
        self.logger.info("Calling _invoke_partial_update_workflow")
        data: dict = self.event.json_body
        is_enabled = convert_to_bool(data.get('isEnabled'))
        scheduling = data.get('scheduling')
        workflow_name = self.event.path_parameters.get('workflowName', None)
        if scheduling:
            schedule = scheduling.get("schedule", None)
            # check if cron expression and not None is valid
            if schedule and not croniter.is_valid(schedule):
                raise BadRequest("Invalid cron expression for scheduling, please revalidate")
            # in case schedule was None or '', pass it in as None
            self.workflow_management.update_schedule(workflow_name, schedule if schedule else None)

        if 'acl' in data:
            acls = data.get('acl', [])
            self.workflow_management.update_workflow_acl(
                workflow_name,
                [EntityACL.from_json_dict_object_acl(acl_model) for acl_model in acls])

        if is_enabled is not None:
            self.workflow_management.update_workflow_enable_flag(workflow_name, is_enabled)

        return {'statusCode': 200, 'body': json.dumps(
            {"result": "Updated",
             "workflowName": workflow_name,
             "details": f"Workflow with name {workflow_name} was partially updated"}
        )}

    def _invoke_convert_model_to_config(self):
        """
        Invoke method call conversion from model to configuration

        @return: API response
        """
        self.logger.info("Calling _invoke_convert_model_to_config")
        yaml_configuration, workflow_name = self.workflow_management.convert_model_to_yaml(
            EntityWorkflow.from_json_dict(self.event.json_body)
        )
        return {'statusCode': 200, 'body': json.dumps(
            {"workflowName": workflow_name,
             "yamlConfiguration": yaml.dump(yaml_configuration)}
        )}

    def _invoke_export_workflow_to_repo(self):
        """
        Invoke method  to exporting workflow to gitHub repository

        @return: API response
        """
        self.logger.info("Calling _invoke_export_workflow_to_repo")
        workflow_name = self.event.path_parameters.get("workflowName")
        self.workflow_management.export_workflow_to_github_repository(
            workflow_name=workflow_name,
            workflow_version=self.event.json_body.get("workflowVersion", "1.0.0"),
            dataset_repo_location=self.event.json_body.get("datasetRepositoryLocation", "datasets"),
            github_branch=self.event.json_body.get("branchToStore")
        )
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "exported",
             "workflowName": workflow_name,
             "details": f"workflow with name {workflow_name} was exported into project github repository"}
        )}

    def _invoke_start_workflow(self):
        """
        Invoke method to start workflow

        @return: API response
        """
        self.logger.info("Calling _invoke_start_workflow")
        workflow_name = self.event.path_parameters.get("workflowName")
        logical_date = from_str_to_datetime(self.event.json_body.get("logicalDate"))
        self.workflow_management.start_workflow(
            workflow_name=workflow_name,
            logical_date=logical_date
        )
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "Started",
             "workflowName": workflow_name,
             "details": f"Workflow with name {workflow_name} started"}
        )}

    def _invoke_stop_workflow(self):
        """
        Invoke method to stop workflow

        @return: API response
        """
        self.logger.info("Calling _invoke_stop_workflow")
        workflow_name = self.event.path_parameters.get("workflowName")
        state = self.event.json_body.get("state")
        if state not in ("success", "failed"):
            raise BadRequest("Supported state into which the workflow should be stopped has to be success or failed,"
                             f" passed state is {state}")
        self.workflow_management.stop_workflow(
            workflow_name=workflow_name,
            state=state
        )
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "Stopped",
             "workflowName": workflow_name,
             "details": f"Runs which were running for workflow with name {workflow_name},"
                        f" were stopped and runs were marked as {state}"}
        )}

    def _invoke_check_workflow_existence(self):
        """
        Invoke method call check workflow existence

        @return: API response of check workflow existence
        """
        self.logger.info("Calling _invoke_check_workflow_existence")
        workflow_name = self.event.path_parameters.get("workflowName")
        self.workflow_management.check_workflow_existence(workflow_name)
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "Exists",
             "workflowName": workflow_name,
             "details": f"Workflow with name {workflow_name} exists"}
        )}

    def _invoke_get_airflow_orchestrator_info(self):
        """
        Invoke method call get airflow orchestration info for stringed list of workflow names

        @return: API response of get airflow status
        """
        self.logger.info("Calling _invoke_get_airflow_orchestration_info")
        workflow_names = SortAndPaginate.clean_and_relist_listed_strings(
            self.event.query_string_parameters.get("workflowNames"))
        response = self.workflow_management.get_airflow_information(workflow_names)
        return {'statusCode': 200, 'body': json.dumps({
            'items': [ct.to_json_dict_orchestrator_info() for ct in response]}
        )}

    # pylint: disable=too-many-return-statements,too-many-branches
    def invoke(self):
        """
        Invoke lambda function logic

        @return:
        """
        # ********************************** GET WORKFLOW AIRFLOW STATUSES CALL **********************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/workflows/orchestratorInfo"):
            return self._invoke_get_airflow_orchestrator_info()
        # *********************************** GET WORKFLOW DETAIL CALL *************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/workflows/{workflowName}"):
            return self._invoke_get_workflow_detail()
        # ********************************** GET WORKFLOW DETAILS CALL *************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/workflows"):
            return self._invoke_get_workflow_details()
        # *************************************** GET WORKFLOW RUNS ****************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/workflows/{workflowName}/runs"):
            return self._invoke_get_workflow_runs()
        # *************************************** GET TASKS OF RUNS ****************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith(
                "/workflows/{workflowName}/runs/{runId}/tasks"):
            return self._invoke_get_tasks_of_workflow_runs()
        # *************************************** GET LOGS OF TASKS ****************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith(
                "/workflows/{workflowName}/runs/{runId}/tasks/{taskId}/logs/{tryNumber}"):
            return self._invoke_get_workflow_task_log()
        # ******************************** GET WORKFLOW EXISTENCE CALL ***************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/workflows/{workflowName}/exists"):
            return self._invoke_check_workflow_existence()
        # ************************************** CREATE WORKFLOW CALL **************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/workflows"):
            return self._invoke_create_workflow()
        # ************************************** UPDATE WORKFLOW CALL **************************************************
        if self.event.http_method == "PUT" and self.event.resource.endswith("/workflows/{workflowName}"):
            return self._invoke_update_workflow()
        # ********************************** PARTIAL UPDATE WORKFLOW CALL **********************************************
        if self.event.http_method == "PATCH" and self.event.resource.endswith("/workflows/{workflowName}"):
            return self._invoke_partial_update_workflow()
        # **************************************** MODEL CONVERSION CALL ***********************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/workflows/model/convert"):
            return self._invoke_convert_model_to_config()
        # ******************************** EXPORT WORKFLOW TO REPOSITORY CALL ******************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/workflows/{workflowName}/exportToRepo"):
            return self._invoke_export_workflow_to_repo()
        # ***************************************** START WORKFLOW CALL ************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/workflows/{workflowName}/start"):
            return self._invoke_start_workflow()
        # ***************************************** STOP WORKFLOW CALL ************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/workflows/{workflowName}/stop"):
            return self._invoke_stop_workflow()
        # ************************************** DELETE WORKFLOW CALL **************************************************
        if self.event.http_method == "DELETE" and self.event.resource.endswith("/workflows/{workflowName}"):
            return self._invoke_delete_workflow()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct workflows method was chosen")
