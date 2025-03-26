import json

from middleware.api.common.http_method_utils import create_error_response
from middleware.common.entity_management.entities.entity_project_account_settings import EntityProjectAccountSettings
from middleware.common.entity_management.entities.entity_project_general_settings import EntityProjectGeneralSettings
from middleware.common.entity_management.project_settings_management import ProjectSettingsManagement
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.helpers import get_env_or_header_value
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum


class ProjectsSettingsLambda(AWSLambdaEventHandler):
    """
    Lambda class for Project settings API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.project_settings_management = ProjectSettingsManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)

    def _invoke_get_projects_general_settings(self):
        """
        Invoke get project general settings
        """
        project_general_settings = self.project_settings_management.get_project_general_settings()
        return {'statusCode': 200, 'body': json.dumps(project_general_settings.to_json_dict())}

    def _invoke_update_projects_general_settings(self):
        """
        Invoke update project general settings
        """

        general_settings = EntityProjectGeneralSettings.from_json_dict(project_id=self.project_id,
                                                                       json_dict=self.event.json_body)
        self.project_settings_management.insert_or_update_project_general_settings(general_settings)
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "updated",
             "projectId": self.project_id,
             "details": f"Project general settings was successfully updated within project {self.project_id}"}
        )}

    def _invoke_get_projects_account_settings(self):
        """
        Invoke get project account settings
        """
        project_account_settings = self.project_settings_management.get_project_account_settings(
            account_type=ProjectAccountTypesEnum.from_str(self.event.path_parameters.get('accountType')),
            check_permission=True, raise_not_found_error=True, project_id=self.project_id
        )

        return {'statusCode': 200, 'body': json.dumps(project_account_settings.to_json_dict())}

    def _invoke_update_projects_account_settings(self):
        """
        Invoke update project account settings
        """
        account_to_update = EntityProjectAccountSettings(
            project_id=self.project_id,
            account_type=ProjectAccountTypesEnum.from_str(self.event.path_parameters.get('accountType')),
            account_details=self.event.json_body)
        self.project_settings_management.insert_or_update_project_account_settings(account_to_update, True)
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "updated",
             "details": f"Project account settings of type {self.event.path_parameters.get('accountType')} "
                        f"was successful updated within project {account_to_update.project_id}",
             "projectId": account_to_update.project_id})}

    def invoke(self):  # pylint: disable=inconsistent-return-statements
        """
        Lambda function implementation
        @return:
        """
        # *********************************** GET PROJECTS SETTINGS ACCOUNT CALL ***************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith("settings/projects/accounts/{accountType}"):
            return self._invoke_get_projects_account_settings()
        # ********************************** UPDATE PROJECTS SETTINGS ACCOUNT CALL *************************************
        if self.event.http_method == 'PUT' and self.event.resource.endswith("settings/projects/accounts/{accountType}"):
            return self._invoke_update_projects_account_settings()
        # ********************************** GET PROJECT GENERAL SETTINGS CALL *****************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith("settings/projects/general"):
            return self._invoke_get_projects_general_settings()
        # ********************************** UPDATE PROJECT GENERAL SETTINGS CALL **************************************
        if self.event.http_method == 'PUT' and self.event.resource.endswith("settings/projects/general"):
            return self._invoke_update_projects_general_settings()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct project settings method was chosen")
