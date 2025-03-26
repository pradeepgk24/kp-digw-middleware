import json

from middleware.api.common.http_method_utils import create_error_response
from middleware.api.common.helpers import get_env_or_header_value
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.common.entity_management.definitions_metadata_management import DefinitionsMetadataManagement


class MetadataDefinitionsLambda(AWSLambdaEventHandler):
    """
    Lambda class for Metadata Definitions API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.metadata_management = DefinitionsMetadataManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)
        self.platform = self.event.query_string_parameters.get('platform')

    def _invoke_get_permission_action_types(self):
        """
        Invoke method call get permission action type

        :return: API response of permission action type
        """
        self.logger.info("Calling _invoke_get_permission_action_type")
        permission_action_metadata = self.metadata_management.get_permission_action_types()
        # Make a call to Metadata DB to get permission action type details
        return {'statusCode': 200, 'body': json.dumps({'items': [metadata_item.to_json_dict()
                                                                 for metadata_item in
                                                                 permission_action_metadata]})}

    def _invoke_get_framework_versions(self):
        """
        Invoke method call get framework versions

        :return: API response of framework versions
        """
        self.logger.info("Calling _invoke_get_framework_versions")
        framework_versions_metadata = self.metadata_management.get_framework_versions()
        # Make a call to Metadata DB to get difw framework versions
        return {'statusCode': 200, 'body': json.dumps({'items': [framework_versions.to_json_dict()
                                                                 for framework_versions in
                                                                 framework_versions_metadata]})}

    def _invoke_get_component_type(self):
        """
        Invoke method call get component type

        :return: API response of get component type
        """
        self.logger.info("Calling _invoke_get_component_type")
        component_type = self.metadata_management.get_component_type(
            self.event.path_parameters.get('componentCategory'),
            self.event.path_parameters.get('componentTypeName'),
            self.event.path_parameters.get('difwCoreVersion')
        )
        # Make a call to Metadata DB to get permission action type details
        return {'statusCode': 200, 'body': json.dumps(component_type.to_json_dict())}

    def _invoke_get_component_types(self):
        """
        Invoke method call get specific component types for example processor

        :return: API response of get component
        """
        self.logger.info("Calling _invoke_get_component_types")
        component_types = self.metadata_management.get_component_types(
            self.platform,
            self.event.path_parameters.get('difwCoreVersion'),
            self.event.path_parameters.get('componentCategory'),
        )
        # Make a call to Metadata DB to get permission action type details
        return {'statusCode': 200, 'body': json.dumps({"items": [ct.to_json_dict() for ct in component_types]})}

    def _invoke_get_enumerator_values(self):
        """
        Invoke method call get enumerator values based on given enumerator category

        :return: API response of get enumerator values
        """
        self.logger.info("Calling _invoke_get_enumerator_values")
        enumerator_entities = self.metadata_management.get_enumerator_values(
            self.event.path_parameters.get('enumeratorCategory')
        )
        return {'statusCode': 200, 'body': json.dumps({"values": [enum_ent.to_json_dict() for enum_ent in
                                                                  enumerator_entities]})}

    # pylint: disable=too-many-return-statements
    def invoke(self):
        """
        Invoke lambda function logic

        :return:
        """
        # **************************************** GET COMPONENT TYPE **********************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith(
                "metadata/components/{difwCoreVersion}/{componentCategory}/{componentTypeName}"):
            return self._invoke_get_component_type()
        # *************************************** GET SPECIFIC COMPONENT CATEGORY TYPES *****************************
        if self.event.http_method == 'GET' and self.event.resource.endswith(
                "metadata/components/{difwCoreVersion}/{componentCategory}"):
            return self._invoke_get_component_types()
        # ************************************** PERMISSION ACTION TYPE CALL ***************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith("metadata/permissionActions"):
            return self._invoke_get_permission_action_types()
        # ************************************** GET FRAMEWORK VERSIONS ********************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith("metadata/frameworkVersions"):
            return self._invoke_get_framework_versions()
        # ************************************** GET ENUMERATOR CATEGORY VALUES ***************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith(
                "metadata/enumerators/{enumeratorCategory}"):
            return self._invoke_get_enumerator_values()

        # if none of the methods were call then no correct API request has been raised
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct metadata definitions method was chosen")
