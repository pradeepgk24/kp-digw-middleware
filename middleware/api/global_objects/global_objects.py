import json
from middleware.api.common.helpers import get_env_or_header_value, convert_to_bool, SortAndPaginate
from middleware.api.common.http_method_utils import create_error_response
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.common.entity_management.global_objects_management import GlobalObjectsManagement
from middleware.common.helpers.exception import BadRequest


class GlobalObjectsLambda(AWSLambdaEventHandler):
    """
    Lambda class for Global Objects API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.global_objects_management = GlobalObjectsManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)

    def _invoke_global_object_search(self):
        """
        Invoke method call global object search

        @return: API response of global object search
        """
        self.logger.info("Calling _invoke_global_object_search")
        object_type = self.event.query_string_parameters.get("objectType")
        # validation on object_type input
        if object_type not in ("pipeline", "pipelineTemplate", "workflow", "componentTemplate"):
            raise BadRequest(f"Selected objectType option {object_type} is not one of"
                             f" supported options: pipeline, pipelineTemplate, workflow, componentTemplate")
        cross_project_search = convert_to_bool(self.event.query_string_parameters.get("crossProjectSearch", False))
        name = self.event.query_string_parameters.get("name")
        excluded_projects = SortAndPaginate.clean_and_relist_listed_strings(
            self.event.query_string_parameters.get("excludedProjects"))
        sort_and_paginate = SortAndPaginate(self.event.query_string_parameters)
        # in case the pageSize was not passed in, overwrite the default value in sort_and_paginate
        if not self.event.query_string_parameters.get("pageSize"):
            self.logger.info("Setting pageSize to 5")
            sort_and_paginate.page_size = 5
        global_objects, total_count = self.global_objects_management.global_object_search(
            object_type=object_type, cross_project_search=cross_project_search,
            name=name, excluded_projects=excluded_projects, sort_and_paginate=sort_and_paginate)
        return {'statusCode': 200, 'body': json.dumps(self.create_list_response(global_objects,
                                                                                sort_and_paginate,
                                                                                total_count))}

    def _invoke_get_global_object_detail(self):
        """
        Invoke method call get global object detail

        @return: API response of get object detail
        """
        self.logger.info("Calling _invoke_get_global_object_detail")
        project_instance_name = self.event.path_parameters.get("projectInstanceName")
        env = self.event.path_parameters.get("env")
        project_id = self.event.path_parameters.get("projectId")
        object_type = self.event.path_parameters.get("objectType")
        object_identifiers = SortAndPaginate.clean_and_relist_listed_strings(
            self.event.query_string_parameters.get("objectIdentifiers"))
        # object_identifiers is list of stringed 'key:value' pairs, so we reparse it as key:value dictionary
        object_identifiers = {key_value_pair.split(":")[0]: key_value_pair.split(":")[1] for
                              key_value_pair in object_identifiers}
        self.logger.info(f"Object identifiers are {object_identifiers}")
        response_object = self.global_objects_management.get_global_object_detail(
            project_instance_name=project_instance_name, env=env,
            project_id=project_id, object_type=object_type, object_identifiers=object_identifiers)
        return {'statusCode': 200, 'body': json.dumps({"objectDetails": {object_type: response_object.to_json_dict()}})}

    # pylint: disable=too-many-return-statements
    def invoke(self):
        """
        Invoke lambda function logic

        @return:
        """
        # ******************************** GLOBAL OBJECT SEARCH CALL ************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/global/objects/search"):
            return self._invoke_global_object_search()
        # ******************************** GET  OBJECT DETAIL CALL *************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith(
                "/global/objects/search/{projectInstanceName}/{env}/{projectId}/{objectType}"):
            return self._invoke_get_global_object_detail()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct global object method was chosen")
