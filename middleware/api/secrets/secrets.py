import json

from middleware.common.entity_management.entities.entity_secret import EntitySecret
from middleware.common.entity_management.project_settings_management import ProjectSettingsManagement
from middleware.common.entity_management.secrets_management import SecretsManagement
from middleware.api.common.http_method_utils import create_error_response
from middleware.api.common.helpers import get_env_or_header_value, SortAndPaginate, convert_to_bool
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent


class SecretsLambda(AWSLambdaEventHandler):
    """
    Lambda class for Secrets API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        project_settings_management = ProjectSettingsManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)
        aws_access_key, aws_secret_key, aws_session_token = \
            project_settings_management.get_project_aws_account_access_info(self.project_id)
        self.secrets_management = SecretsManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects, aws_access_key=aws_access_key, aws_secret_key=aws_secret_key,
            aws_session_token=aws_session_token)
        self.platform = self.event.query_string_parameters.get('platform')

    def _invoke_get_secrets(self):
        """
        Invoke method call get secrets

        :return: API response
        """
        self.logger.info("Calling _invoke_get_secrets")
        sort_and_paginate = SortAndPaginate(self.event.query_string_parameters)
        secrets, total_count = self.secrets_management.get_secrets(
            secret_name=self.event.query_string_parameters.get('secretName'),
            sort_and_paginate=sort_and_paginate
        )
        return {'statusCode': 200, 'body': json.dumps(
            self.create_list_response(secrets, sort_and_paginate, total_count))}

    def _invoke_get_secret(self):
        """
        Invoke method call get secret

        :return: API response
        """
        self.logger.info("Calling _invoke_get_secret")
        secret = self.secrets_management.get_secret(
            secret_name=self.event.path_parameters.get('secretName'),
            get_values=convert_to_bool(self.event.query_string_parameters.get('getValues'))
        )

        return {'statusCode': 200, 'body': json.dumps(secret.to_json_dict())}

    def _invoke_create_secret(self):
        """
        Invoke method call create secret

        :return: API response
        """
        self.logger.info("Calling _invoke_create_secret")
        secret = self.secrets_management.create_secret(EntitySecret.from_json_dict(self.event.json_body))
        return {'statusCode': 201, 'body': json.dumps({"result": "created",
                                                       "secretName": secret.secret_name,
                                                       "details": f"Secret was created successfully "
                                                                  f"with secretName equal to {secret.secret_name}"})}

    def _invoke_update_secret(self):
        """
        Invoke method call to update secret

        """
        self.logger.info("Going to call _invoke_update_secret")
        secret_name = self.secrets_management.update_secret(EntitySecret.from_json_dict(
            self.event.json_body, self.event.path_parameters.get('secretName')))
        return {'statusCode': 200, 'body': json.dumps({"result": "updated",
                                                       "secretName": secret_name,
                                                       "details": f"Secret was updated successfully with secretName"
                                                                  f" equal to {secret_name}"})}

    def _invoke_delete_secret(self):
        """
        Invoke method call to delete secret

        """
        self.logger.info("Going to call _invoke_delete_secret")
        secret_name = self.event.path_parameters.get('secretName')
        delete_secret_manager = convert_to_bool(self.event.query_string_parameters.get('deleteSecretManager', False))
        self.secrets_management.delete_secret(secret_name, delete_secret_manager=delete_secret_manager)
        return {'statusCode': 200, 'body': json.dumps({"result": "deleted",
                                                       "secretName": secret_name,
                                                       "details": f"Secret was deleted successfully with secretName"
                                                                  f" equal to {secret_name}"})}

    def _invoke_check_secret_existence(self):
        """
        Invoke method call check secret existence

        :return: API response of check secret existence
        """
        self.logger.info("Calling _invoke_check_secret_existence")
        secret_name = self.event.path_parameters.get("secretName")
        self.secrets_management.check_secret_existence(secret_name)
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "exists",
             "secretName": secret_name,
             "details": f"Secret with name {secret_name} exists"}
        )}

    # pylint: disable=too-many-return-statements
    def invoke(self):
        """
        Invoke secrets lambda function logic

        :return:
        """
        # **************************************** GET Secret *********************************************
        # get method for getting one secret based on its name
        if self.event.http_method == 'GET' and self.event.resource.endswith("secrets/{secretName}"):
            return self._invoke_get_secret()
        # **************************************** GET Secrets *********************************************
        # get method for getting many secrets for subjects specified in header
        if self.event.http_method == 'GET' and self.event.resource.endswith("secrets"):
            return self._invoke_get_secrets()
        # **************************************** Create Secrets *********************************************
        if self.event.http_method == 'POST' and self.event.resource.endswith("secrets"):
            return self._invoke_create_secret()
        # **************************************** Update Secrets *********************************************
        if self.event.http_method == 'PUT' and self.event.resource.endswith("secrets/{secretName}"):
            return self._invoke_update_secret()
        # **************************************** Delete Secrets *********************************************
        if self.event.http_method == 'DELETE' and self.event.resource.endswith("secrets/{secretName}"):
            return self._invoke_delete_secret()
        # ******************************** GET SECRET EXISTENCE CALL ***************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("secrets/{secretName}/exists"):
            return self._invoke_check_secret_existence()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct secrets method was chosen")
