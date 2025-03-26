import json
import yaml
from middleware.api.common.helpers import get_env_or_header_value, SortAndPaginate, convert_to_bool, \
    is_valid_yaml_or_json, validate_worker_count
from middleware.api.common.http_method_utils import create_error_response
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.common.entity_management.pipeline_templates_management import PipelineTemplateManagement
from middleware.common.entity_management.entities.entity_subject import EntitySubject, SubjectTypesEnum
from middleware.common.entity_management.entities.entity_pipeline_template import EntityPipelineTemplate
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.helpers.exception import BadRequest


class PipelineTemplatesLambda(AWSLambdaEventHandler):
    """
    Lambda class for Pipeline Templates API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.pipeline_template_management = PipelineTemplateManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)

    def _invoke_create_pipeline_template(self):
        """
        Invoke method call create pipeline template

        :return: API response of create pipeline template
        """
        self.logger.info("Calling _invoke_create_pipeline_template")
        request_body = self.event.json_body
        if request_body.get('platform') == "glue":
            validate_worker_count(
                request_body.get('advancedOptions').get('glue', {}).get('workerType'),
                int(request_body.get('advancedOptions').get('glue', {}).get('numberOfWorkers'))
            )
        # validate cluster options only if platform is databricks and cluster type is job cluster
        elif request_body.get('platform') == "databricks" and request_body.get('advancedOptions', {}).get('databricks',
                                                                                                          {}).get(
            'jobCluster'):
            job_cluster = request_body.get('advancedOptions').get('databricks', {}).get('jobCluster')
            is_valid_yaml_or_json(job_cluster.get('clusterOptions'),
                                  job_cluster.get('clusterOptionsFormat'))
        # enhance by name of the pipeline
        pipeline_template_name = self.pipeline_template_management.create_pipeline_template(
            EntityPipelineTemplate.from_json_dict(self.event.json_body)
        )
        return {'statusCode': 201, 'body': json.dumps(
            {"result": "created",
             "pipelineTemplateName": pipeline_template_name,
             "details": f"Pipeline template with name {pipeline_template_name} was created"}

        )}

    def _invoke_update_pipeline_template(self):
        """
        Invoke method call update pipeline template

        :return: API response of update pipeline template
        """
        self.logger.info("Calling _invoke_update_pipeline_template")
        pipeline_template = self.event.path_parameters["pipelineTemplateName"]
        request_body = self.event.json_body
        if request_body.get('platform') == "glue":
            validate_worker_count(
                request_body.get('advancedOptions').get('glue', {}).get('workerType'),
                int(request_body.get('advancedOptions').get('glue', {}).get('numberOfWorkers'))
            )
        # validate cluster options only if platform is databricks and cluster type is job cluster
        elif request_body.get('platform') == "databricks" and request_body.get('advancedOptions', {}).get('databricks',
                                                                                                          {}).get(
            'jobCluster'):
            job_cluster = request_body.get('advancedOptions').get('databricks', {}).get('jobCluster')
            is_valid_yaml_or_json(job_cluster.get('clusterOptions'),
                                  job_cluster.get('clusterOptionsFormat'))
        # enhance by name of the pipeline
        request_body.update({"pipelineTemplateName": pipeline_template})
        pipeline_template_name = self.pipeline_template_management.update_pipeline_template(
            EntityPipelineTemplate.from_json_dict(request_body)
        )

        return {'statusCode': 200, 'body': json.dumps(
            {"result": "updated",
             "pipelineTemplateName": pipeline_template_name,
             "details": f"Pipeline template with name {pipeline_template_name} was updated"}

        )}

    def _invoke_delete_pipeline_template(self):
        """
        Invoke method call delete pipeline template

        :return: API response of delete pipeline template
        """
        self.logger.info("Calling _invoke_delete_pipeline_template")
        pipeline_template = self.event.path_parameters["pipelineTemplateName"]
        self.pipeline_template_management.delete_pipeline_template(pipeline_template)
        return {'statusCode': 200, 'body': json.dumps({"result": "deleted",
                                                       "pipelineTemplateName": pipeline_template,
                                                       "details": f"Pipeline template with name "
                                                                  f"{pipeline_template} was deleted"})}

    def _invoke_share_pipeline_template(self):
        """
        Invoke method call share pipeline template as whole

        :return: API response of share  pipeline template
        """
        self.logger.info("Calling _invoke_share_pipeline_template")
        pipeline_template = self.event.path_parameters["pipelineTemplateName"]
        acls = self.event.json_body.get('acl', [])
        new_acl_list = []
        for acl in acls:
            if acl.get('relationType') == "owner":
                raise BadRequest("Relation type cannot be set to owner while sharing the pipeline template")
            # we set relationship directly relation to shared_template
            new_acl_list.append(
                EntityACL(EntitySubject(subject_id=acl['subjectId'], subject_type=SubjectTypesEnum.user),
                          ObjectsACLRelationTypesEnum.shared_template))

        self.pipeline_template_management.modify_acl_for_pipeline_template(new_acl_list, pipeline_template)
        return {'statusCode': 200, 'body': json.dumps({"result": "updated",
                                                       "pipelineTemplateName": pipeline_template,
                                                       "details": f"pipeline template with name  "
                                                                  f"{pipeline_template} was updated"})}

    def _invoke_get_pipeline_template_detail(self):
        """
        Invoke method call get pipeline template

        :return: API response of get pipeline template
        """
        self.logger.info("Calling _invoke_get_pipeline_template_detail")
        pipeline_template_name = self.event.path_parameters["pipelineTemplateName"]
        response_object = self.pipeline_template_management.get_pipeline_template(pipeline_template_name,
                                                                                  self.event.headers.get(
                                                                                      'difw-core-version'))
        if pipeline_template_name == 'defaultProjectValues':
            return {'statusCode': 200, 'body': json.dumps(response_object.to_json_dict(default_project_values=True))}

        return {'statusCode': 200, 'body': json.dumps(response_object.to_json_dict())}

    def _invoke_get_pipeline_templates(self):
        """
        Invoke method call get pipeline templates

        :return: API response of get pipeline templates
        """
        self.logger.info("Calling _invoke_get_pipeline_templates")
        sort_and_paginate = SortAndPaginate(self.event.query_string_parameters)
        limited_view = convert_to_bool(self.event.query_string_parameters.get('limitedView', False))
        pipeline_templates, total_count = self.pipeline_template_management.get_pipeline_templates(
            status=self.event.query_string_parameters.get('status', None),
            pipeline_template_name=self.event.query_string_parameters.get('pipelineTemplateName', None),
            sort_and_paginate=sort_and_paginate,
            limited_view=limited_view
        )
        return {'statusCode': 200, 'body': json.dumps(self.create_list_response(pipeline_templates,
                                                                                sort_and_paginate, total_count))}

    def _invoke_convert_model_to_config(self):
        """
        Invoke method call conversion from model to configuration

        :return: API response
        """
        self.logger.info("Calling _invoke_convert_model_to_config")
        yaml_configuration, pipeline_template_name = self.pipeline_template_management.convert_model_to_yaml(
            EntityPipelineTemplate.from_json_dict(self.event.json_body)
        )
        return {'statusCode': 200, 'body': json.dumps({
            "pipelineTemplateName": pipeline_template_name,
            "yamlConfiguration": yaml.dump(yaml_configuration)})}

    # pylint: disable=inconsistent-return-statements
    def _invoke_check_pipeline_template_existence(self):
        """
        Invoke method call check pipeline template existence

        :return: API response of check pipeline template existence
        """
        self.logger.info("Calling _invoke_check_pipeline_template_exists")
        pipeline_template_name = self.event.path_parameters.get("pipelineTemplateName")
        if self.pipeline_template_management.check_pipeline_template_existence(pipeline_template_name):
            return {'statusCode': 200, 'body': json.dumps({"result": "exists",
                                                           "pipelineTemplateName": pipeline_template_name,
                                                           "details": f"pipeline template with name "
                                                                      f"{pipeline_template_name} already exists"})}

    # pylint: disable=too-many-return-statements
    def invoke(self):
        """
        Invoke lambda function logic

        :return:
        """
        # ******************************** CREATE PIPELINE TEMPLATE CALL *********************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/pipelineTemplates"):
            return self._invoke_create_pipeline_template()
        # ******************************** UPDATE PIPELINE TEMPLATE CALL *********************************************
        if self.event.http_method == "PUT" and self.event.resource.endswith(
                "/pipelineTemplates/{pipelineTemplateName}"):
            return self._invoke_update_pipeline_template()
        # ******************************** DELETE PIPELINE TEMPLATE CALL *********************************************
        if self.event.http_method == "DELETE" and self.event.resource.endswith(
                "/pipelineTemplates/{pipelineTemplateName}"):
            return self._invoke_delete_pipeline_template()
        # ******************************** SHARE PIPELINE TEMPLATE CALL *********************************************
        if self.event.http_method == "PATCH" and self.event.resource.endswith(
                "/pipelineTemplates/{pipelineTemplateName}"):
            return self._invoke_share_pipeline_template()
        # ******************************** GET PIPELINE TEMPLATE  DETAIL CALL *****************************************
        if self.event.http_method == "GET" and self.event.resource.endswith(
                "/pipelineTemplates/{pipelineTemplateName}"):
            return self._invoke_get_pipeline_template_detail()
        # ******************************** GET PIPELINE TEMPLATES CALL ***********************************************
        if self.event.http_method == "GET" and self.event.resource.endswith(
                "/pipelineTemplates"):
            return self._invoke_get_pipeline_templates()
        # ******************************** GET PIPELINE TEMPLATE EXISTENCE CALL ***************************************
        if self.event.http_method == "GET" and self.event.resource.endswith(
                "/pipelineTemplates/{pipelineTemplateName}/exists"):
            return self._invoke_check_pipeline_template_existence()
        # **************************************** MODEL CONVERSION CALL ***********************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/pipelineTemplates/model/convert"):
            return self._invoke_convert_model_to_config()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct pipeline templates method was chosen")
