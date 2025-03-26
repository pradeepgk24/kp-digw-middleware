import json

from middleware.api.common.helpers import get_env_or_header_value, SortAndPaginate, convert_to_bool
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.http_method_utils import create_error_response
from middleware.common.entity_management.component_templates_management import ComponentTemplatesManagement
from middleware.common.entity_management.components_management import ComponentsManagement
from middleware.common.entity_management.entities.entity_component_template import EntityComponentTemplate


class ComponentsLambda(AWSLambdaEventHandler):
    """
    Lambda class for Metadata Definitions API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger):
        super().__init__(event, context, logger)
        self.component_templates_management = ComponentTemplatesManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            metadatabase_region=self.event.headers.get('aws-region', 'us-east-1'), user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)
        self.components_management = ComponentsManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger), metadatabase_region=self.event.headers.get(
                'aws-region', 'us-east-1'), user_isid=self.user_isid, selected_subjects=self.selected_subjects)
        self.platform = self.event.query_string_parameters.get('platform')

    def _invoke_get_component_template(self):
        """
        Invoke method call get component templated detail

        :return: API response
        """
        self.logger.info("Calling _invoke_get_component_template")
        component_template = self.component_templates_management.get_component_template(
            int(self.event.path_parameters.get('templateId'))
        )
        # Make a call to Metadata DB to get permission action type details
        return {'statusCode': 200, 'body': json.dumps(component_template.to_json_dict())}

    def _invoke_get_component_templates(self):
        """
        Invoke method call get component types

        :return: API response
        """
        self.logger.info("Calling _invoke_get_component_templates")
        sort_and_paginate = SortAndPaginate(self.event.query_string_parameters)
        component_category = SortAndPaginate.clean_and_relist_listed_strings(
            self.event.query_string_parameters.get('componentCategory'))
        component_type = SortAndPaginate.clean_and_relist_listed_strings(
            self.event.query_string_parameters.get('componentType'))
        limited_view = convert_to_bool(self.event.query_string_parameters.get('limitedView', 'False'))
        component_templates, total_count = self.component_templates_management.get_component_templates(
            template_name=self.event.query_string_parameters.get('templateName'),
            component_category=component_category,
            component_type=component_type,
            sort_and_paginate=sort_and_paginate,
            limited_view=limited_view
        )

        return {'statusCode': 200, 'body': json.dumps(
            self.create_list_response(component_templates, sort_and_paginate, total_count))}

    def _invoke_delete_component_templates(self):
        """
        Invoke method call get component types

        :return: API response
        """
        self.logger.info("Calling _invoke_delete_component_templates")
        component_template = self.component_templates_management.delete_component_templates(
            int(self.event.path_parameters.get('templateId'))
        )
        # Make a call to Metadata DB to get permission action type details
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "deleted", "details": f"Component template with id {component_template.template_id} was deleted",
             "templateId": component_template.template_id})}

    def _invoke_add_component_templates(self):
        """
        Invoke method to add new component template

        :return: API response
        """
        self.logger.info("Calling _invoke_add_component_templates")
        component_template = self.component_templates_management.insert_component_template(
            EntityComponentTemplate.from_json_dict(self.event.json_body)
        )
        return {'statusCode': 201, 'body': json.dumps(
            {"result": "created", "details": f"Component template with id {component_template.template_id} was created",
             "templateId": component_template.template_id})}

    def _invoke_update_component_templates(self):
        """
        Invoke method to add update component template

        :return: API response
        """
        self.logger.info("Calling _invoke_update_component_templates")
        component_template_to_update = EntityComponentTemplate.from_json_dict(self.event.json_body)
        component_template_to_update.set_template_id(int(self.event.path_parameters.get('templateId')))
        component_template = self.component_templates_management.update_component_template(component_template_to_update)
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "updated", "details": f"Template with id {component_template.template_id} was updated",
             "templateId": component_template.template_id})}

    def _invoke_update_component_templates_sharing(self):
        """
        Invoke method to add new component template sharing
        This method keeps owners of selected template and replaces shared access with new from request body
        :return: API response
        """
        self.logger.info("Calling _invoke_update_component_templates_sharing")
        acls = self.event.json_body.get('acl')
        component_template = self.component_templates_management. \
            update_component_template_sharing(int(self.event.path_parameters.get('templateId')), acls)
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "updated",
             "details": f"Sharing of template with id {component_template.template_id} was updated",
             "templateId": component_template.template_id})}

    def _invoke_obtain_connector_objects(self):
        """
        Invoke method to obtain connector objects
        :return: API response
        """
        self.logger.info("Calling _invoke_obtain_connector_objects")
        request = self.event.json_body
        out_items = self.components_management.obtain_connector_objects(
            component_category=self.event.path_parameters.get('componentCategory'),
            component_type_name=self.event.path_parameters.get('componentType'),
            difw_core_version=self.event.path_parameters.get('difwCoreVersion'),
            request=request,
            get_table_details=convert_to_bool(self.event.query_string_parameters.get('getTableDetails'))
        )
        return {'statusCode': 200, 'body': json.dumps(out_items)}

    def _invoke_validate_connections(self):
        """
        Invoke method to validate connection based on connector info
        :return: API response
        """
        self.logger.info("Calling _invoke_validate_connections")
        request = self.event.json_body
        result = self.components_management.validate_connections(
            component_category=self.event.path_parameters.get('componentCategory'),
            component_type_name=self.event.path_parameters.get('componentType'),
            request=request
        )
        if result:
            response_result = "Valid"
            response_details = "Your connection is valid"
        else:
            response_result = "Invalid"
            response_details = "Your connection is invalid"
        return {'statusCode': 200, 'body': json.dumps({"result": response_result, "details": response_details,
                                                       "componentType": self.event.path_parameters.
                                                      get('componentType')})}

    def _invoke_check_component_template_existence(self):
        """
        Invoke method call check component template existence

        :return: API response of check component template existence
        """
        self.logger.info("Calling _invoke_check_component_template_existence")
        ct_name = self.event.query_string_parameters.get("componentTemplateName")
        self.component_templates_management.check_component_template_existence(ct_name)
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "exists",
             "componentTemplateName": ct_name,
             "details": f"component template with name {ct_name} exists"}
        )}

    # pylint: disable=too-many-return-statements
    def invoke(self):
        """
        Invoke lambda function logic

        :return:
        """
        # **************************************** GET COMPONENT TEMPLATE ********************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith("componentTemplates/{templateId}"):
            return self._invoke_get_component_template()
        # **************************************** GET COMPONENT TEMPLATES *******************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith("componentTemplates"):
            return self._invoke_get_component_templates()
        # **************************************** DELETE COMPONENT TEMPLATE **************************************
        if self.event.http_method == 'DELETE' and self.event.resource.endswith("componentTemplates/{templateId}"):
            return self._invoke_delete_component_templates()
        # **************************************** CREATE COMPONENT TEMPLATE **************************************
        if self.event.http_method == 'POST' and self.event.resource.endswith("componentTemplates"):
            return self._invoke_add_component_templates()
        # **************************************** UPDATE COMPONENT TEMPLATE **************************************
        if self.event.http_method == 'PUT' and self.event.resource.endswith("componentTemplates/{templateId}"):
            return self._invoke_update_component_templates()
        # **************************************** UPDATE COMPONENT TEMPLATE SHARING *********************************
        if self.event.http_method == 'PATCH' and self.event.resource.endswith("componentTemplates/{templateId}"):
            return self._invoke_update_component_templates_sharing()
        # **************************************** POST - OBTAIN CONNECTOR OBJECTS *********************************
        if self.event.http_method == 'POST' and self.event.resource.endswith(
                "components/{difwCoreVersion}/{componentCategory}/{componentType}/browse"):
            return self._invoke_obtain_connector_objects()
        # **************************************** POST - VALIDATE CONNECTOR INFO  *********************************
        if self.event.http_method == 'POST' and self.event.resource.endswith(
                "components/{difwCoreVersion}/{componentCategory}/{componentType}/validate"):
            return self._invoke_validate_connections()
        # ******************************** CHECK COMPONENT TEMPLATE NAME UNIQUENESS *********************************
        if self.event.http_method == "GET" and self.event.resource.endswith(
                "componentTemplates/exists"):
            return self._invoke_check_component_template_existence()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct components method was chosen")
