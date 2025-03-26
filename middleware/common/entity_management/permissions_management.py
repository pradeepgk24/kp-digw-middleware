from middleware.api.common.helpers import SortAndPaginate
from middleware.common.entity_management.entities.entity_permission import EntityPermission
from middleware.common.entity_management.entities.entity_permission_acl import EntityPermissionACL
from middleware.common.entity_management.entity_management import EntityManagement
from middleware.common.helpers.exception import AuthorizationError, NoDataError, BadRequest
from middleware.common.metadatabase.permissions_metadata_provider import PermissionMetadataProvider
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.metadatabase.model.types.permissions_acl_relation_types_enum import \
    PermissionsACLRelationTypesEnum
from middleware.common.entity_management.entities.entity_subject import EntitySubject, SubjectTypesEnum
from middleware.common.security.action_type import ActionType


class PermissionsManagement(EntityManagement):
    """
    Permissions management
    """

    # pylint: disable=too-many-arguments
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._permission_metadata_provider = None

    @property
    def permission_metadata_provider(self):
        """
        permission metadata provider property
        """
        if self._permission_metadata_provider is None:
            self._permission_metadata_provider = PermissionMetadataProvider(self.logger,
                                                                            self.metadatabase_connection,
                                                                            self.lambda_secrets_manager)
        return self._permission_metadata_provider

    def get_permission(self, permission_name: str = None):
        """
        Get permission
        @param permission_name:
        @return: EntityPermission
        """
        self.logger.info(f"Going to get permissions with name {permission_name}")
        entity_permission = EntityPermission.from_metadb_object(
            self.permission_metadata_provider.get_permission(
                permission_name, self.user_isid
            ))
        if entity_permission is None:
            raise NoDataError("There are no permissions which fit your filter parameters.")
        self.logger.info(f"Validating read permissions for user {self.user_isid}.")
        if self.auth_validator.validate(
                ActionType.READ_PERMISSION,
                {}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"The user {self.user_isid} under group {self.group_id} and project {self.project_id}"
                f" has no permission to read permission.")
        return entity_permission

    def validate_permission(self, action_type: ActionType, action_detail):
        """
        Validate the given permission action type

        param action_type
        param action_detail

        return result of permission validation
        """
        self.logger.info(f"Going to validate permission action type {action_type.value}")
        validation_result = self.auth_validator.validate(action_type, action_detail)
        if validation_result == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"Insufficient permissions - Reason: user {self.user_isid} is not authorized to perform "
                f"action type {action_type.value}")
        return validation_result

    def create_permission(self, permission: EntityPermission):
        """
        Create new permission.

        @param permission:
        @return: permission name
        """
        if self.auth_validator.validate(ActionType.WRITE_PERMISSION,
                                        {}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"user {self.user_isid} does not have access to create permission")
        self.logger.info(f"Going to create new permission {permission.permission_name}")
        # add user owner and project
        permission.add_acl(EntitySubject(subject_id=self.user_isid, subject_type=SubjectTypesEnum.user),
                           PermissionsACLRelationTypesEnum.owner, project_id=self.project_id)
        permission.add_acl(EntitySubject(subject_id=self.project_id, subject_type=SubjectTypesEnum.project),
                           PermissionsACLRelationTypesEnum.owner, project_id=self.project_id)

        # insert it into DB
        return EntityPermission.from_metadb_object(
            self.permission_metadata_provider.insert_permission(permission.to_metadb_object(), self.user_isid))

    def update_permission(self, permission: EntityPermission):
        """
        Update permission

        @param permission:
        @return:
        """
        entity_permission = self.get_permission(permission.permission_name)
        if self.auth_validator.validate(ActionType.WRITE_PERMISSION,
                                        {}) \
                == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"user {self.user_isid} does not have access to update permission {permission.permission_name}")
        # if obtained permission is global, raise error, as those are not editable
        if entity_permission.is_global:
            raise BadRequest("Update of global permission is not allowed, "
                             "permission requested to be updated is global.")
        self.logger.info(f"Going to update permission {permission.permission_name}")
        # update it into DB
        return EntityPermission.from_metadb_object(
            self.permission_metadata_provider.update_permission(permission.to_metadb_object(), self.user_isid))

    def delete_permission(self, permission_name):
        """
        Delete permission.

        @param permission_name:
        @return:
        """
        permission = self.get_permission(permission_name)
        if self.auth_validator.validate(ActionType.DELETE_PERMISSION,
                                        {}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"user {self.user_isid} does not have access to delete permission {permission.permission_name}")
        # if obtained permission is global, raise error, as those can not be deleted
        if permission.is_global:
            raise BadRequest("Deletion of global permission is not allowed, "
                             "permission requested to be deleted is global.")
        self.logger.info(f"Going to delete permission with name {permission_name}")
        return self.permission_metadata_provider.delete_permission(permission_name, self.user_isid)

    def enable_or_disable_permission(self, permission_name: str, enable_flag: bool):
        """
        enables the given permission, if the enable_flag is set to true and  disables the given permission
        if enable_flag is set to false.

        @param permission_name:
        @param enable_flag:
        """
        permission = self.get_permission(permission_name)
        permission.set_is_enabled(enable_flag)
        self.logger.info(
            f"Going to update is_enable flag of the given notification from {permission.is_enabled} to {enable_flag}")
        return self.update_permission(permission)

    def modify_permission_acl_for_subjects(self, subject_ids: list, permission_name: str):
        """
        assign permission to single or multiple subjects.

        @param subject_ids - List of subject ids whose acls needs to updated
        @param permission_name - name of the permission to which subjects will be assigned

        """
        self.logger.info(
            f"Going to validate write permission for user {self.user_isid} on permission with name {permission_name}")
        if self.auth_validator.validate(ActionType.WRITE_PERMISSION,
                                        {}) \
                == PermissionEffectsEnum.deny:
            raise AuthorizationError(f"user {self.user_isid} does not have access to update permission"
                                     f" {permission_name}")
        new_acl_list = []
        for subject in subject_ids:
            # prepare the new acl list of subject to whom the permission needs to be assigned.
            new_acl_list.append(
                EntityPermissionACL(EntitySubject(subject_id=subject, subject_type=SubjectTypesEnum.user),
                                    PermissionsACLRelationTypesEnum.assigned, master_owner=self.project_id))
        return self.permission_metadata_provider.update_permissions_assigned_acl_list(subject_ids, [permission_name],
                                                                                      new_acl_list, self.user_isid,
                                                                                      True, project_id=self.project_id)

    def modify_permission_acl_for_permissions(self, subject_id: str, permission_names: list):
        """
        Modifies permission acls tagged to subjects

        @param subject_id - subject for which permission acl needs to be added
        @param permission_names - list of permissions names to which subject wll  be assigned
        """
        for permission in permission_names:
            self.logger.info(
                f"Going to validate write permission for user {self.user_isid} on permission with name {permission}")
            if self.auth_validator.validate(ActionType.WRITE_PERMISSION,
                                            {}) \
                    == PermissionEffectsEnum.deny:
                raise AuthorizationError(f"user {self.user_isid} does not have access to update permission"
                                         f" {permission}")
        # prepare the new acl list of subject to whom the permission needs to be assigned.
        new_acl_list = [EntityPermissionACL(EntitySubject(subject_id=subject_id, subject_type=SubjectTypesEnum.user),
                                            PermissionsACLRelationTypesEnum.assigned, master_owner=self.project_id)]
        return self.permission_metadata_provider.update_permissions_assigned_acl_list([subject_id], permission_names,
                                                                                      new_acl_list, self.user_isid,
                                                                                      project_id=self.project_id)

    def get_permissions(self, limited_view: bool = False, permission_name: str = None,
                        is_enabled: bool = None, sort_and_paginate: SortAndPaginate = None):
        """
        Get permissions
        @param limited_view: flag, if true return only permission_name and is_enabled
        @param permission_name: optional, substring of permission name
        @param is_enabled: enabling flag, if you want to retrieve all permissions
        @param sort_and_paginate:
        @return: list of EntityPermissions
        """
        self.logger.info(f"Going to retrieve global permissions and for "
                         f"related project {self.project_id}")
        # if limited_view is true, we will use different option of from_metadb_objects, so we will pass as additional
        # argument to it
        populated_query, total_count = self.permission_metadata_provider.get_permissions(
            self.user_isid, self.project_id, limited_view,
            permission_name, is_enabled, sort_and_paginate)
        entity_permissions = EntityPermission.from_metadb_objects(populated_query, limited_view)
        if (not entity_permissions) or (total_count == 0):
            raise NoDataError("There are no permission which fit your filter parameters.")
        self.logger.info(f"Validating read permissions of user {self.user_isid}.")
        if self.auth_validator.validate(
                ActionType.READ_PERMISSION,
                {}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} has"
                f" no permission to read permission")
        entity_permissions = [ct.to_json_dict(limited_view) for ct in entity_permissions]

        return entity_permissions, total_count

    def get_subject_permissions(self, assigned_subjects: list = None, is_enabled: bool = None):
        """
        Get permissions
        @param assigned_subjects: list of subject with assigned permissions
        @param is_enabled: enabling flag, if you want to retrieve all permissions
        @return: list of EntityPermissions
        """
        self.logger.info(f"Validating read permissions of user {self.user_isid}.")
        if self.auth_validator.validate(
                ActionType.READ_PERMISSION,
                {}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} has"
                f" no permission to read permission")
        self.logger.info(f"Going to retrieve permissions for subjects {assigned_subjects} and for "
                         f"related project {self.project_id}")
        # get from DB all permissions which selected subjects have assigned to them
        entity_permissions = EntityPermission.from_metadb_objects_subjects_permissions(
            self.permission_metadata_provider.get_subject_permissions(self.user_isid, assigned_subjects, is_enabled,
                                                                      project_id=self.project_id))
        if not entity_permissions:
            raise NoDataError("There are no subjects with permissions which fit your filter parameters.")
        return entity_permissions
