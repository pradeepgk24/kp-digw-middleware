import json

from middleware.common.entity_management.permissions_management import PermissionsManagement
from middleware.api.common.http_method_utils import create_error_response
from middleware.api.common.helpers import get_env_or_header_value, SortAndPaginate, convert_to_bool
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.common.entity_management.entities.entity_permission import EntityPermission, PermissionEffectsEnum
from middleware.common.helpers.exception import BadRequest
from middleware.common.security.action_type import ActionType


class PermissionsLambda(AWSLambdaEventHandler):
    """
    Lambda class for Permissions API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.permissions_management = PermissionsManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)
        self.platform = self.event.query_string_parameters.get('platform')

    def _invoke_get_permission(self):
        """
        Invoke method call get permission

        :return: API response
        """
        self.logger.info("Calling _invoke_get_permission")
        permissions = self.permissions_management.get_permission(
            self.event.path_parameters.get('permissionName')
        )
        # Make a call to Metadata DB to get permission
        return {'statusCode': 200, 'body': json.dumps(permissions.to_json_dict())}

    def _invoke_validate_permission(self):
        """
        Invoke method call to create permission.

        """
        self.logger.info("Going to validate permission")
        try:
            action_type = ActionType(self.event.json_body["actionType"])
        except ValueError as attr_error:
            raise BadRequest(f"Invalid actionType passed in request. Error: {attr_error}") from attr_error

        self.permissions_management.validate_permission(
            action_type,
            self.event.json_body["authorizationObject"]
        )
        return {'statusCode': 200, 'body': json.dumps({"result": PermissionEffectsEnum.allow.value})}

    def _invoke_create_permissions(self):
        """
        Invoke method call to create permissions

        """
        self.logger.info("Going to call _invoke_create_permissions")
        permission_to_create = EntityPermission.from_json_dict(self.event.json_body)
        # if passed in permission is global raise error
        if permission_to_create.is_global:
            raise BadRequest("Creating of global permission is not allowed, "
                             "permission requested to be created is global.")
        if not permission_to_create.permission_actions:
            raise BadRequest("Permission has no action types")
        inserted_permission = self.permissions_management.create_permission(permission_to_create)
        return {'statusCode': 201, 'body': json.dumps({"result": "created",
                                                       "permissionName": inserted_permission.permission_name,
                                                       "details": f"Permission with "
                                                                  f"{inserted_permission.permission_name} "
                                                                  f"was created successfully"})}

    def _invoke_update_permission(self):
        """
        Invoke method call to update permission

        """
        self.logger.info("Going to call _invoke_update_permission")
        permission_name = self.event.path_parameters["permissionName"]
        permission_to_update = EntityPermission.from_json_dict(self.event.json_body, permission_name)
        # if passed in permission is global raise error
        if permission_to_update.is_global:
            raise BadRequest("Update of global permission is not allowed, "
                             "permission requested to be updated is global.")
        if not permission_to_update.permission_actions:
            raise BadRequest("Permission has no action types")
        self.permissions_management.update_permission(permission_to_update)
        return {'statusCode': 200, 'body': json.dumps({"status": "updated",
                                                       "permissionName": permission_name,
                                                       "details": f"Permission with permission name "
                                                                  f"{permission_name} was updated successfully"})}

    def _invoke_delete_permission(self):
        """
        Invoke method call to delete permission

        """
        self.logger.info("Going to call _invoke_delete_permission")
        permission_name = self.event.path_parameters["permissionName"]
        self.permissions_management.delete_permission(permission_name)
        return {'statusCode': 200, 'body': json.dumps({"status": "deleted",
                                                       "permissionName": permission_name,
                                                       "details": f"Permission with permission name"
                                                                  f" {permission_name} was deleted successfully"})}

    def _invoke_enable_or_disable_permission(self):
        """
        Invoke method call for enable or disable  permission.

        """
        permission_name = self.event.path_parameters["permissionName"]
        self.logger.info("Calling _invoke_enable_or_disable_permission")
        enable_or_disable_flag = 'enabled' if convert_to_bool(self.event.json_body['isEnabled']) else 'disabled'
        self.permissions_management.enable_or_disable_permission(
            permission_name=permission_name,
            enable_flag=convert_to_bool(self.event.json_body['isEnabled']))
        return {
            'statusCode': 200,
            'body': json.dumps({"result": f" permission {enable_or_disable_flag}",
                                "details": f"permission with permission name {permission_name} "
                                           f"was {enable_or_disable_flag}"})}

    def _invoke_change_permission_acl(self):
        """
        Invoke method call for change permission acl.

        """
        self.logger.info("Calling _invoke_change_permission_acl")
        if self.event.json_body.get('subjectsAssignment'):
            permission = self.event.json_body.get('subjectsAssignment').get('permissionName')
            subjects = self.event.json_body.get('subjectsAssignment').get('subjectIds')
            self.permissions_management.modify_permission_acl_for_subjects(subjects, permission)
            result = {
                'statusCode': 200,
                'body': json.dumps({"result": "updated",
                                    "details": f"permission {permission} was successfully "
                                               f"assigned to subjects = {subjects}"})}
        elif self.event.json_body['permissionAssignment']:
            permissions = self.event.json_body.get('permissionAssignment').get('permissionNames')
            subject = self.event.json_body.get('permissionAssignment').get('subjectId')
            self.permissions_management.modify_permission_acl_for_permissions(subject, permissions)
            result = {
                'statusCode': 200,
                'body': json.dumps({"result": "updated",
                                    "details": f"subject {subject} was successfully "
                                               f"assigned to permissions = {permissions}"})}
        return result

    def _invoke_get_permissions(self):
        """
        Invoke method call get permissions
        :return: API response
        """
        self.logger.info("Calling _invoke_get_permissions")
        sort_and_paginate = SortAndPaginate(self.event.query_string_parameters)
        limited_view = convert_to_bool(self.event.query_string_parameters.get('limitedView', False))
        permissions, total_count = self.permissions_management.get_permissions(
            limited_view=limited_view,
            permission_name=self.event.query_string_parameters.get('permissionName'),
            is_enabled=convert_to_bool(self.event.query_string_parameters.get('isEnabled')),
            sort_and_paginate=sort_and_paginate
        )
        return {'statusCode': 200, 'body': json.dumps(
            self.create_list_response(permissions, sort_and_paginate, total_count))}

    def _invoke_get_subject_permissions(self):
        """
        Invoke method call get subject permissions
        :return: API response
        """
        self.logger.info("Calling _invoke_get_subject_permissions")
        assigned_subjects = SortAndPaginate.clean_and_relist_listed_strings(
            self.event.query_string_parameters.get('assignedSubjects'))
        permissions = self.permissions_management.get_subject_permissions(
            assigned_subjects=assigned_subjects,
            is_enabled=convert_to_bool(self.event.query_string_parameters.get('isEnabled'))
        )
        return {'statusCode': 200, 'body': json.dumps(
            {'items': [{'subjectId': subject, 'assignedPermissions': permission} for
                       subject, permission in permissions.items()]})}

    # pylint: disable=too-many-return-statements
    def invoke(self):
        """
        Invoke lambda function logic

        :return:
        """
        # ************************************** GET SUBJECTS PERMISSIONS CALL ********************************
        if self.event.http_method == "GET" and self.event.resource.endswith("security/permissions/perSubject"):
            return self._invoke_get_subject_permissions()
        # **************************************** GET PERMISSION CALL *******************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith("security/permissions/{permissionName}"):
            return self._invoke_get_permission()
        # **************************************** GET PERMISSION CALL *********************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith("security/permissions"):
            return self._invoke_get_permissions()
        # ************************************** VALIDATE PERMISSION CALL ****************************************
        if self.event.http_method == "POST" and self.event.resource.endswith(
                "security/permissions/validate"):
            return self._invoke_validate_permission()
        # ************************************** CREATE PERMISSION CALL ******************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("security/permissions"):
            return self._invoke_create_permissions()
        # ************************************** UPDATE PERMISSION CALL ******************************************
        if self.event.http_method == "PUT" and self.event.resource.endswith(
                "security/permissions/{permissionName}"):
            return self._invoke_update_permission()
        # ************************************** DELETE PERMISSION CALL ******************************************
        if self.event.http_method == "DELETE" and self.event.resource.endswith(
                "security/permissions/{permissionName}"):
            return self._invoke_delete_permission()
        # ************************************** ENABLE OR DISABLE PERMISSION CALL ********************************
        if self.event.http_method == "PATCH" and self.event.resource.endswith(
                "security/permissions/{permissionName}"):
            return self._invoke_enable_or_disable_permission()
        # ************************************** ENABLE OR DISABLE PERMISSION CALL ********************************
        if self.event.http_method == "PATCH" and self.event.resource.endswith(
                "security/permissions/acl"):
            return self._invoke_change_permission_acl()

        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct permission method was chosen")
