from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from sqlalchemy.orm import contains_eager

from middleware.api.common.helpers import SortAndPaginate, add_order_to_query
from middleware.common.helpers.local_cache import lru_cache_with_ttl
from middleware.common.metadatabase.model.difw_metadb_model import Permissions, PermissionsACL, PermissionActions, \
    Subjects
from middleware.common.metadatabase.clients.meta_database_client import MetaDatabaseClient
from middleware.common.helpers.exception import EntityConflictError
from middleware.common.metadatabase.model.types.permissions_acl_relation_types_enum import \
    PermissionsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum


class PermissionMetadataProvider(MetaDatabaseClient):
    """
    Database client which served actions related with permissions
    """

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=not-callable
    def get_permissions(self, user_id: str, project_id: str = None,
                        limited_view: bool = False, permission_name: str = None,
                        is_enabled: bool = None, sort_and_paginate: SortAndPaginate = None):
        """
        Gets permissions from DB which can be somehow accessible for user and assigned project
        Process flow>
        process is as follows
           - first we will get all permissions, which we don't want to have, they are as follows
           - Subject type is project, this project is owner of the permissions - this mean, that permission is not
          global and this project is not the project the user is under, since we want to keep all the permissions
          of the project, which user is under
          - list not_included_permission_names contains names of the permissions, which we want to exclude based on
          the point above

        :param user_id: logon user isid
        :param project_id:
        :param limited_view:
        :param permission_name:
        :param is_enabled: boolean
        :param sort_and_paginate: number of permissions per page in output
        :return:
        """
        self.logger.info(
            f"User {user_id} going to get all global permissions and permissions regarding same project")
        # bigger comment in the function declaration
        # we get all permissions, which we don't want
        query_to_dispose = self.session.query(Permissions.PERMISSION_NAME). \
            join(PermissionsACL, Permissions.PERMISSION_NAME == PermissionsACL.PERMISSION_NAME). \
            join(Subjects, and_(PermissionsACL.SUBJECT_ID == Subjects.SUBJECT_ID,
                                Subjects.SUBJECT_TYPE == SubjectTypesEnum.project,
                                PermissionsACL.RELATION_TYPE == PermissionsACLRelationTypesEnum.owner,
                                PermissionsACL.SUBJECT_ID != project_id))
        # convert said query to list for faster calculation
        not_included_permission_names = [item[0] for item in query_to_dispose.all()]
        query_to_keep = self.session.query(Permissions)
        dynamic_query = query_to_keep.filter(Permissions.PERMISSION_NAME.not_in(not_included_permission_names))
        if limited_view:
            dynamic_query = dynamic_query.with_entities(Permissions.PERMISSION_NAME, Permissions.IS_ENABLED)
        # filter on is_enabled - if true/false, return only with the same flag value
        if is_enabled is not None:
            # pylint: disable=singleton-comparison
            dynamic_query = dynamic_query.filter(Permissions.IS_ENABLED == True) if is_enabled \
                else dynamic_query.filter(Permissions.IS_ENABLED == False)
        # if permission_name is given (or substring)
        if permission_name:
            dynamic_query = dynamic_query.filter(Permissions.PERMISSION_NAME.ilike(f"%{permission_name}%"))
        if sort_and_paginate and sort_and_paginate.sorted_conversion:
            dynamic_query = add_order_to_query(dynamic_query, Permissions, sort_and_paginate.sorted_conversion)

        permissions, total_count = self.process_get_entries_and_count(sort_and_paginate, dynamic_query)
        return permissions, total_count

    def get_permission(self, permission_name: str, user_id: str):
        """
        Get permission
        :param permission_name: permission_name which we want to get
        :param user_id: user wants to get the permission
        :return: Permissions object
        """
        self.logger.info(f"User {user_id} is going to retrieve permission {permission_name}")
        return Permissions(PERMISSION_NAME=permission_name).get_unique(self.session)

    def insert_or_update_permission(self, permission: Permissions, user_id: str):
        """
        Insert or update permission.

        :param permission: permission which will
        :param user_id: user who create/update the permission

        :return: inserted or updated permission
        """
        db_result = permission.get_unique(self.session)
        # check existence of records. If exists then update, If it does not exist then create new
        if not db_result:
            return self.insert_permission(permission, user_id)
        return self.update_permission(permission, user_id)

    def update_permission(self, permission: Permissions, user_id: str):
        """
        Update existing permission

        :param permission:
        :param user_id: user who update the permission
        :return: updated permission
        """
        permission_name = permission.PERMISSION_NAME
        self.logger.info(f"User {user_id} going to update permission with name {permission_name}")
        self.enrich_with_updating_audit_columns(permission, user_id)
        updated_permission = self.update_record(permission, user_id, commit=False)
        PermissionActions.delete_many(self.session, and_(PermissionActions.PERMISSION_NAME.is_(None)),
                                      commit=False)
        # commit the changes only when the all transactions in session are completed successfully.
        self.commit()
        return updated_permission

    def insert_permission(self, permission: Permissions, user_id: str):
        """
        Insert new permission.

        :param permission:
        :param user_id: user who create the permission
        :return: inserted permission
        """
        permission_name = permission.PERMISSION_NAME
        try:
            self.logger.info(f"User {user_id} going to insert permission with name {permission_name}")
            # first insert permission with all relations
            self.enrich_with_creation_audit_columns(permission, user_id)
            permission.insert(self.session)
            return permission
        except IntegrityError as integrity_error:
            raise EntityConflictError(
                f"The permission with name {permission_name}  already exists") \
                from integrity_error

    def insert_permission_subject_relationship(self, permission_acl: PermissionsACL, user_id: str, commit: bool = True):
        """
        Insert relationship between subject and permission.

        :param permission_acl:
        :param user_id:
        :param commit:
        """
        self.insert_or_update_record(permission_acl, user_id, commit)

    # pylint: disable=singleton-comparison
    @lru_cache_with_ttl(ttl=60)
    def get_assigned_permissions_with_action_types(self, user_id: str, subject_id: str, action_type: str,
                                                   project_id: str):
        """
        Get assigned permissions.

        Method is cached for 30 seconds

        :param subject_id:
        :param action_type:
        :param user_id:
        :param project_id: project id for master owner of permission
        """
        self.logger.info(
            f"User {user_id} going to retrieve permissions with for subject with id {subject_id} and "
            f"action_type {action_type}")
        result = self.session.query(Permissions). \
            filter(Permissions.IS_ENABLED == True). \
            join(PermissionActions, and_(Permissions.PERMISSION_NAME == PermissionActions.PERMISSION_NAME,
                                         PermissionActions.ACTION_TYPE == action_type)). \
            join(PermissionsACL, and_(Permissions.PERMISSION_NAME == PermissionsACL.PERMISSION_NAME,
                                      PermissionsACL.RELATION_TYPE == PermissionsACLRelationTypesEnum.assigned,
                                      PermissionsACL.SUBJECT_ID.ilike(subject_id),
                                      PermissionsACL.MASTER_OWNER == project_id)). \
            options(contains_eager(Permissions.rel_permission_actions)).all()
        self.session.close()
        return result

    def delete_permission(self, permission_name: str, user_id: str):
        """
        Delete permission

        :param permission_name: permission to delete
        :param user_id: logon user isid
        """
        self.logger.info(f"user {user_id} is going to delete permission with name {permission_name}")
        return Permissions(PERMISSION_NAME=permission_name).delete(self.session)

    def get_permission_acl(self, permission_name: str, user_id: str):
        """
        Get the acls tagged to the given permission.

        :param permission_name:
        :param user_id:
        """
        self.logger.info(
            f"user {user_id} is going to retrieve the acl details of the given permission with name {permission_name}")
        dynamic_query = (
            self.session.query(PermissionsACL)
            .filter(PermissionsACL.PERMISSION_NAME.in_([permission_name]))
        )
        return dynamic_query.all()

    def delete_permissions_acl(self, permission_name: str, user_id: str):
        """
        param permission_name
        param user_id

        """
        self.logger.info(f"user {user_id} is going to delete all the acls tagged to "
                         f" permission with name {permission_name}")
        return PermissionsACL(PERMISSION_NAME=permission_name).delete(self.session)

    def update_permissions_assigned_acl_list(self, subject_ids: list, permission_names: list, new_assigned_acls: list,
                                             user_id: str, modify_acl_for_subject: bool = False,
                                             project_id: str = None):
        """
        removes the existing acl either for subject/subjects or permissions and recreate the new acl.

        :param subject_ids
        :param permission_names
        :param new_assigned_acls - list of new acls that will be added to Permissions ACL
        :param user_id:
        :param modify_acl_for_subject - if set to True will fetch all acl that are assigned to subject,
        id set to False will fetch all the acls by permission wise
        :param project_id: project_id to be added as master owner
        """
        if modify_acl_for_subject:
            # Get all ACL for given permissions which are having relation type as assigned
            list_of_acl_to_remove = PermissionsACL.get_many(
                self.session,
                and_(PermissionsACL.PERMISSION_NAME.in_(permission_names),
                     PermissionsACL.RELATION_TYPE == PermissionsACLRelationTypesEnum.assigned,
                     PermissionsACL.MASTER_OWNER == project_id)
            )

        else:
            # Get all ACL for the given subject which are having  relation type as assigned
            list_of_acl_to_remove = PermissionsACL.get_many(
                self.session, and_(PermissionsACL.SUBJECT_ID.in_(subject_ids),
                                   PermissionsACL.RELATION_TYPE == PermissionsACLRelationTypesEnum.assigned,
                                   PermissionsACL.MASTER_OWNER == project_id)
            )
        self.logger.info("Going to remove the existing acls")
        for existing_acl in list_of_acl_to_remove:
            existing_acl.delete(self.session, commit=False)
        self.logger.info("Going to recreate the new acls")
        for permission in permission_names:
            for new_acl in new_assigned_acls:
                self.insert_record(PermissionsACL(PERMISSION_NAME=permission,
                                                  SUBJECT_ID=new_acl.subject.subject_id,
                                                  RELATION_TYPE=new_acl.relation_type,
                                                  MASTER_OWNER=project_id), user_id, commit=False)
        # issue commit on session only if whole transaction is complete.
        return self.commit()

    def get_subject_permissions(self, user_id: str, subject_ids: list, is_enabled: bool = None, project_id: str = None):
        """
        Gets permissions from DB which are assigned to selected subjects.
        Get all permissions based on relation and subject ids
        :param user_id: logon user isid
        :param subject_ids: list of subject ids
        :param is_enabled: boolean
        :param project_id: master owner of permission
        :return:
        """
        self.logger.info(f"User {user_id} going to get permissions assigned to"
                         f" {subject_ids} with filtering flag is_enabled {is_enabled}.")
        dynamic_query = self.session.query(Permissions). \
            join(PermissionsACL, and_(Permissions.PERMISSION_NAME == PermissionsACL.PERMISSION_NAME,
                                      PermissionsACL.SUBJECT_ID.in_(subject_ids),
                                      PermissionsACL.RELATION_TYPE == PermissionsACLRelationTypesEnum.assigned,
                                      PermissionsACL.MASTER_OWNER == project_id))
        dynamic_query = dynamic_query.with_entities(PermissionsACL.SUBJECT_ID, PermissionsACL.PERMISSION_NAME,
                                                    Permissions.IS_ENABLED)
        # filter on is_enabled - if true/false, return only with the same flag value
        if is_enabled is not None:
            # pylint: disable=singleton-comparison
            dynamic_query = dynamic_query.filter(Permissions.IS_ENABLED == True) if is_enabled \
                else dynamic_query.filter(Permissions.IS_ENABLED == False)
        return dynamic_query.all()
