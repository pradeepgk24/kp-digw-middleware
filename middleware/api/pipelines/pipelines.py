import json
import yaml
from croniter import croniter
from middleware.api.common.helpers import get_env_or_header_value, SortAndPaginate, convert_to_bool, \
    is_valid_yaml_or_json, validate_worker_count
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline
from middleware.common.entity_management.objects.project_filter_enum import ProjectFilterEnum
from middleware.common.entity_management.objects.owner_filter_enum import OwnerFilterEnum
from middleware.common.entity_management.pipelines_management import PipelinesManagement
from middleware.api.common.http_method_utils import create_error_response
from middleware.common.helpers.exception import BadRequest, NoDataError, ConfigurationModelConvertorError
from middleware.common.helpers.json_secret_encoder import JsonSecretEncoder


class PipelinesLambda(AWSLambdaEventHandler):
    """
    Lambda class for Pipeline API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager, is_async=False):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.pipelines_management = PipelinesManagement(
            logger=self.logger,
            metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger
            ),
            lambda_secrets_manager=self.lambda_secrets_manager,
            user_isid=self.user_isid,
            selected_subjects=self.selected_subjects,
            is_async=is_async
        )
        self.is_async = is_async

    def _invoke_get_pipeline_detail(self):
        """
        Invoke method call get pipeline detail

        :return: API response of get pipeline detail
        """
        self.logger.info("Calling _invoke_get_pipeline_detail")
        pipeline_name = self.event.path_parameters.get("pipelineName")
        orchestrator_info = True if self.event.query_string_parameters.get("orchestratorInfo",
                                                                           None) is None else convert_to_bool(
            self.event.query_string_parameters.get("orchestratorInfo"))
        response_object = self.pipelines_management.get_pipeline_detail(pipeline_name=pipeline_name,
                                                                        orchestrator_info=orchestrator_info)
        return {'statusCode': 200, 'body': json.dumps(response_object.to_json_dict())}

    def _invoke_get_pipeline_details(self):
        """
        Invoke method call get pipeline details

        :return: API response of get pipeline templates
        """
        self.logger.info("Calling _invoke_get_pipeline_details")
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

        pipelines, total_count = self.pipelines_management.get_pipeline_details(
            limited_view=convert_to_bool(self.event.query_string_parameters.get('limitedView', False)),
            pipeline_name=self.event.query_string_parameters.get('pipelineName', None),
            is_enabled=convert_to_bool(self.event.query_string_parameters.get('isEnabled')),
            owner=owner_filter,
            sort_and_paginate=sort_and_paginate,
            orchestrator_info=orchestrator_info,
            project_filter=project_filter,
        )

        return {'statusCode': 200, 'body': json.dumps(
            self.create_list_response(pipelines, sort_and_paginate, total_count))}

    def _invoke_get_pipeline_runs(self):
        """
        Invoke method to get pipeline runs

        :return: API response of get pipeline runs
        """
        self.logger.info("Calling _invoke_get_pipeline_runs")
        pipeline_runs = self.pipelines_management.get_pipeline_runs(
            pipeline_name=self.event.path_parameters.get('pipelineName', None),
            max_result=int(self.event.query_string_parameters.get('maxResult', 30))
        )
        if not pipeline_runs:
            raise NoDataError(
                f"There are not pipeline runs for pipeline {self.event.path_parameters.get('pipelineName', None)}")
        return {'statusCode': 200,
                'body': json.dumps({"items": [pipeline_run.to_json_dict() for pipeline_run in pipeline_runs]})}

    def _invoke_get_tasks_of_pipeline_runs(self):
        """
        Invoke method to get pipeline tasks of runs

        :return: API response
        """
        self.logger.info("Calling _invoke_get_tasks_of_pipeline_runs")
        pipeline_tasks = self.pipelines_management.get_tasks_of_object_runs(
            pipeline_name=self.event.path_parameters.get('pipelineName', None),
            dag_run_id=self.event.path_parameters.get('runId', None)
        )
        if not pipeline_tasks:
            raise NoDataError(
                f"There are not pipeline tasks for pipeline {self.event.path_parameters.get('pipelineName', None)}")
        return {'statusCode': 200,
                'body': json.dumps({"items": [pipeline_task.to_json_dict() for pipeline_task in pipeline_tasks]})}

    def _invoke_get_pipeline_task_log(self):
        """
        Invoke method to get log of task

        :return: API response
        """
        self.logger.info("Calling _invoke_get_pipeline_task_log")
        logs = self.pipelines_management.get_logs_of_task(
            pipeline_name=self.event.path_parameters.get('pipelineName', None),
            dag_run_id=self.event.path_parameters.get('runId', None),
            task_id=self.event.path_parameters.get('taskId', None),
            try_number=int(self.event.path_parameters.get('tryNumber', 1))
        )
        if not logs:
            raise NoDataError(
                f"There are not logs for pipeline {self.event.path_parameters.get('pipelineName', None)}"
                f" and run {self.event.path_parameters.get('runId', None)}")
        return {'statusCode': 200, 'body': logs}

    def _invoke_create_pipeline(self):
        """
        Invoke method call create pipeline

        :return: API response of create pipeline
        """
        self.logger.info("Calling _invoke_create_pipeline")
        json_body = self.event.json_body
        if json_body.get('platform') == "glue":
            validate_worker_count(
                json_body.get('advancedOptions').get('glue', {}).get('workerType'),
                int(json_body.get('advancedOptions').get('glue', {}).get('numberOfWorkers'))
            )
        # validate cluster options only if platform is databricks and cluster type is job cluster
        elif json_body.get('platform') == "databricks" and json_body.get('advancedOptions', {}).get('databricks',
                                                                                                    {}).get(
                'jobCluster'):
            job_cluster = json_body.get('advancedOptions').get('databricks', {}).get('jobCluster')
            is_valid_yaml_or_json(job_cluster.get('clusterOptions'),
                                  job_cluster.get('clusterOptionsFormat'))
        # enhance by name of the pipeline
        if self.is_async:
            self.pipelines_management.event = self.pipelines_management.events_management.create_or_update_event_entity(
                event_type="createPipeline",
                request_id=self.event.request_context.request_id,
                json_body=self.event.json_body)
        inserted_pipeline = self.pipelines_management.create_pipeline(
            entity_pipeline=EntityPipeline.from_json_dict(self.event.json_body, is_create=True),
            request_id=self.event.request_context.request_id
        )
        response = {'statusCode': 201, 'body': json.dumps(
            {"result": "created",
             "pipelineName": inserted_pipeline.pipeline_name,
             "details": f"Pipeline with name {inserted_pipeline.pipeline_name} was created"}
        )}

        if self.is_async:
            self.pipelines_management.events_management.update_event_entity(event=self.pipelines_management.event,
                                                                            status="success", status_code=201,
                                                                            output=yaml.dump(response), is_active=False)
        return response

    def _invoke_update_pipeline(self):
        """
        Invoke method call update pipeline

        :return: API response of update pipeline
        """
        self.logger.info("Calling _invoke_update_pipeline")
        json_body = self.event.json_body
        if json_body.get('platform') == "glue":
            validate_worker_count(
                json_body.get('advancedOptions').get('glue', {}).get('workerType'),
                int(json_body.get('advancedOptions').get('glue', {}).get('numberOfWorkers'))
            )
        # validate cluster options only if platform is databricks and cluster type is job cluster
        elif json_body.get('platform') == "databricks" and json_body.get('advancedOptions', {}).get('databricks',
                                                                                                    {}).get(
                'jobCluster'):
            job_cluster = json_body.get('advancedOptions').get('databricks', {}).get('jobCluster')
            is_valid_yaml_or_json(job_cluster.get('clusterOptions'),
                                  job_cluster.get('clusterOptionsFormat'))
        # enhance by name of the pipeline
        json_body["pipelineName"] = self.event.path_parameters["pipelineName"]
        entity_pipeline = EntityPipeline.from_json_dict(json_body)
        # update of pipelines based on old versions is not allowed, as it will be broken inside the generator
        if not entity_pipeline.framework_version == self.event.headers.get("difw-core-version"):
            raise BadRequest("Update of pipelines based on not newest version of the Core is not allowed")
        if self.is_async:
            self.pipelines_management.event = self.pipelines_management.events_management.create_or_update_event_entity(
                event_type="updatePipeline",
                request_id=self.event.request_context.request_id,
                json_body=self.event.json_body)
        updated_pipeline = self.pipelines_management.update_pipeline(entity_pipeline=entity_pipeline,
                                                                     request_id=self.event.request_context.request_id)
        response = {'statusCode': 200, 'body': json.dumps(
            {"result": "updated",
             "pipelineName": updated_pipeline.pipeline_name,
             "details": f"Pipeline with name {updated_pipeline.pipeline_name} was updated"}
        )}
        if self.is_async:
            self.pipelines_management.events_management.update_event_entity(
                event=self.pipelines_management.event,
                status="success", status_code=200,
                output=yaml.dump(response), is_active=False)
        return response

    def _invoke_delete_pipeline(self):
        """
        Invoke method call delete pipeline template

        :return: API response of delete pipeline template
        """
        self.logger.info("Calling _invoke_delete_pipeline")
        pipeline_name = self.event.path_parameters["pipelineName"]
        self.pipelines_management.delete_pipeline(pipeline_name)
        return {'statusCode': 200, 'body': json.dumps({"result": "deleted", "pipelineName": pipeline_name,
                                                       "details": f"Pipeline with name {pipeline_name} was deleted"})}

    def _invoke_partial_update_pipeline(self):
        """
        Invoke method call to partial update of pipeline

        :return: API response to partial update pipeline
        """
        self.logger.info("Calling _invoke_partial_update_pipeline")
        data: dict = self.event.json_body
        is_enabled = convert_to_bool(data.get('isEnabled'))
        scheduling = data.get('scheduling')
        pipeline_name = self.event.path_parameters.get('pipelineName', None)
        if scheduling:
            schedule = scheduling.get("schedule", None)
            # check if cron expression and not None is valid
            if schedule and not croniter.is_valid(schedule):
                raise BadRequest("Invalid cron expression for scheduling, please revalidate")
            # in case schedule was None or '', pass it in as None
            self.pipelines_management.update_schedule(pipeline_name, schedule if schedule else None)

        if 'acl' in data:
            acls = data.get('acl', [])
            self.pipelines_management.update_pipeline_acl(
                pipeline_name,
                [EntityACL.from_json_dict_object_acl(acl_model) for acl_model in acls])

        if is_enabled is not None:
            self.pipelines_management.update_pipeline_enable_flag(pipeline_name, is_enabled)

        return {'statusCode': 200, 'body': json.dumps(
            {"result": "updated",
             "pipelineName": pipeline_name,
             "details": f"Pipeline with name {pipeline_name} was partially updated"}
        )}

    def _invoke_reverse_engineering(self):
        """
        Invoke method call to reverse engineering

        :return: API response
        """
        self.logger.info("Calling _invoke_partial_update_pipeline")
        try:
            final_entity_pipeline_model, unprocessed_yaml_configuration, created_secrets = \
                self.pipelines_management.convert_yaml_to_model(
                    pipeline_configuration=yaml.safe_load(
                        self.event.json_body.get("yamlConfiguration")
                        .replace('!!int', '')
                        .replace('!!bool', '')
                        .replace('!!float', '')
                    ),
                    pipeline_name=self.event.json_body.get("pipelineName"),
                    framework_version=self.event.json_body.get("frameworkVersion"),
                    environment=self.event.json_body.get("environment", "dev"),
                )
        except ConfigurationModelConvertorError as exc:
            raise BadRequest(f"Error during create pipeline from YAML: {str(exc)}") from exc

        return {'statusCode': 200, 'body': json.dumps(
            {
                "pipelineName": final_entity_pipeline_model.pipeline_name,
                "model": final_entity_pipeline_model.to_json_dict(),
                "secrets": [{"secretName": created_secret_name} for created_secret_name in created_secrets],
                "excludedAttributes": yaml.dump(unprocessed_yaml_configuration)
            },
            cls=JsonSecretEncoder
        )}

    def _invoke_convert_model_to_config(self):
        """
        Invoke method call conversion from model to configuration

        :return: API response
        """
        self.logger.info("Calling _invoke_convert_model_to_config")
        yaml_configuration, pipeline_name = self.pipelines_management.convert_model_to_yaml(
            EntityPipeline.from_json_dict(self.event.json_body)
        )
        return {'statusCode': 200, 'body': json.dumps(
            {"pipelineName": pipeline_name,
             "yamlConfiguration": yaml.dump(yaml_configuration)}
        )}

    def _invoke_export_pipeline_to_repo(self):
        """
        Invoke method  to exporting pipeline to gitHub repository

        :return: API response
        """
        self.logger.info("Calling _invoke_export_pipeline_to_repo")
        pipeline_name = self.event.path_parameters.get("pipelineName")
        self.pipelines_management.export_pipeline_to_github_repository(
            pipeline_name=pipeline_name,
            pipeline_version=self.event.json_body.get("pipelineVersion", "1.0.0"),
            dataset_repo_location=self.event.json_body.get("datasetRepositoryLocation", "datasets"),
            github_branch=self.event.json_body.get("branchToStore")
        )
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "exported",
             "pipelineName": pipeline_name,
             "details": f"Pipeline with name {pipeline_name} was exported into project github repository"}
        )}

    def _invoke_start_pipeline(self):
        """
        Invoke method to start pipeline

        :return: API response
        """
        self.logger.info("Calling _invoke_start_pipeline")
        pipeline_name = self.event.path_parameters.get("pipelineName")
        self.pipelines_management.start_pipeline(
            pipeline_name=pipeline_name,
            logical_date=self.event.json_body.get("logicalDate"),
            run_conf=self.event.json_body.get("runConf", {})
        )
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "started",
             "pipelineName": pipeline_name,
             "details": f"Pipeline with name {pipeline_name} started"}
        )}

    def _invoke_stop_pipeline(self):
        """
        Invoke method to stop pipeline

        :return: API response
        """
        self.logger.info("Calling _invoke_stop_pipeline")
        pipeline_name = self.event.path_parameters.get("pipelineName")
        state = self.event.json_body.get("state")
        if state not in ("success", "failed"):
            raise BadRequest("Supported state into which the pipeline should be stopped has to be success or failed,"
                             f" passed state is {state}")
        self.pipelines_management.stop_pipeline(
            pipeline_name=pipeline_name,
            state=state
        )
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "Stopped",
             "pipelineName": pipeline_name,
             "details": f"Runs which were running for pipeline with name {pipeline_name},"
                        f" were stopped and runs were marked as {state}"}
        )}

    def _invoke_check_pipeline_existence(self):
        """
        Invoke method call check pipeline existence

        :return: API response of check pipeline existence
        """
        self.logger.info("Calling _invoke_check_pipeline_existence")
        pipeline_name = self.event.path_parameters.get("pipelineName")
        self.pipelines_management.check_pipeline_existence(pipeline_name)
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "exists",
             "pipelineName": pipeline_name,
             "details": f"Pipeline with name {pipeline_name} exists"}
        )}

    def _invoke_get_airflow_orchestrator_info(self):
        """
        Invoke method call get airflow orchestration info for stringed list of pipeline names

        :return: API response of get airflow status
        """
        self.logger.info("Calling _invoke_get_airflow_orchestration_info")
        response = self.pipelines_management.get_airflow_information(
            pipelines_names=SortAndPaginate.clean_and_relist_listed_strings(
                self.event.query_string_parameters.get("pipelineNames")))
        return {'statusCode': 200, 'body': json.dumps(
            {'items': [ct.to_json_dict_orchestrator_info() for ct in response]})}

    # pylint: disable=too-many-return-statements,too-many-branches
    def invoke(self):
        """
        Invoke lambda function logic

        :return:
        """
        # ************************************* GET PIPELINE AIRFLOW STATUSES CALL *************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/pipelines/orchestratorInfo"):
            return self._invoke_get_airflow_orchestrator_info()
        # *********************************** GET PIPELINE DETAIL CALL *************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/pipelines/{pipelineName}"):
            return self._invoke_get_pipeline_detail()
        # ********************************** GET PIPELINE DETAILS CALL *************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/pipelines"):
            return self._invoke_get_pipeline_details()
        # *************************************** GET PIPELINE RUNS ****************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/pipelines/{pipelineName}/runs"):
            return self._invoke_get_pipeline_runs()
        # *************************************** GET TASKS OF RUNS ****************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith(
                "/pipelines/{pipelineName}/runs/{runId}/tasks"):
            return self._invoke_get_tasks_of_pipeline_runs()
        # *************************************** GET LOGS OF TASKS ****************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith(
                "/pipelines/{pipelineName}/runs/{runId}/tasks/{taskId}/logs/{tryNumber}"):
            return self._invoke_get_pipeline_task_log()
        # ************************************* GET PIPELINE EXISTENCE CALL ********************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/pipelines/{pipelineName}/exists"):
            return self._invoke_check_pipeline_existence()
        # **************************************** CREATE PIPELINE CALL ************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/pipelines"):
            return self._invoke_create_pipeline()
        # **************************************** CREATE PIPELINE ASYNC CALL ******************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/pipelines/async"):
            return self._invoke_create_pipeline()
        # ************************************** UPDATE PIPELINE CALL **************************************************
        if self.event.http_method == "PUT" and self.event.resource.endswith("/pipelines/{pipelineName}"):
            return self._invoke_update_pipeline()
        # ************************************** UPDATE PIPELINE ASYNC CALL ********************************************
        if self.event.http_method == "PUT" and self.event.resource.endswith("/pipelines/async/{pipelineName}"):
            return self._invoke_update_pipeline()
        # ********************************** PARTIAL UPDATE PIPELINE CALL **********************************************
        if self.event.http_method == "PATCH" and self.event.resource.endswith("/pipelines/{pipelineName}"):
            return self._invoke_partial_update_pipeline()
        # ************************************** REVERSE ENGINEERING CALL **********************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/pipelines/model/reverseEngineering"):
            return self._invoke_reverse_engineering()
        # **************************************** MODEL CONVERSION CALL ***********************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/pipelines/model/convert"):
            return self._invoke_convert_model_to_config()
        # ******************************** EXPORT PIPELINE TO REPOSITORY CALL ******************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/pipelines/{pipelineName}/exportToRepo"):
            return self._invoke_export_pipeline_to_repo()
        # ***************************************** START PIPELINE CALL ************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/pipelines/{pipelineName}/start"):
            return self._invoke_start_pipeline()
        # ***************************************** STOP PIPELINE CALL ************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/pipelines/{pipelineName}/stop"):
            return self._invoke_stop_pipeline()
        # ************************************** DELETE PIPELINE CALL **************************************************
        if self.event.http_method == "DELETE" and self.event.resource.endswith("/pipelines/{pipelineName}"):
            return self._invoke_delete_pipeline()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct pipelines method was chosen")
