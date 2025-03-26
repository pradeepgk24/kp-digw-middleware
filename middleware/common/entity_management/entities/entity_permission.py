# pylint: skip-file
from collections import defaultdict

from middleware.api.common.helpers import convert_to_bool
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_permission_acl import EntityPermissionACL
from middleware.common.entity_management.entities.entity_permission_action import EntityPermissionAction
from middleware.common.metadatabase.model.difw_metadb_model import Permissions, PermissionsACL
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.metadatabase.model.types.permissions_acl_relation_types_enum import \
    PermissionsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum


class EntityPermission(EntityObject):
    """
    Entity permission
    """

    def __init__(self, permission_name: str, effect: PermissionEffectsEnum, description: str,
                 is_enabled: bool, permission_actions: list, acl: list = None, is_global: bool = False):
        self._permission_name = permission_name
        self._effect = effect
        self._description = description
        self._is_enabled = is_enabled
        self._permission_actions = permission_actions
        self._acl = acl
        self._is_global = is_global

    @property
    def permission_name(self):
        """
        Get permission_name.

        :return: permission_name
        """
        return self._permission_name

    @property
    def effect(self):
        """
        Get effect.

        :return: effect
        """
        return self._effect

    @property
    def is_enabled(self):
        """
        Get is_enabled.

        :return: is_enabled
        """
        return self._is_enabled

    @property
    def description(self):
        """
        Get description.

        :return: description
        """
        return self._description

    @property
    def permission_actions(self):
        """
        Get permission_actions.

        :return: permission_actions
        """
        if self._permission_actions is None:
            self._permission_actions = list()
        return self._permission_actions

    @property
    def acl(self):
        """
        Get acl

        :return: acl
        """
        if self._acl is None:
            self._acl = list()
        return self._acl

    @property
    def is_global(self):
        """
        Get is_global.

        :return: is_global
        """
        return self._is_global

    def add_acl(self, subject: EntitySubject,
                relation: PermissionsACLRelationTypesEnum = PermissionsACLRelationTypesEnum.owner,
                project_id: str = None):
        """
        Add ACL into permissions
        """
        self.acl.append(EntityPermissionACL(subject, relation, master_owner=project_id))

    def set_is_enabled(self, is_enabled):
        """
        Set is_enabled.

        :return: is_enabled
        """
        self._is_enabled = is_enabled

    def to_json_dict(self, limited_view: bool = False):
        """
        return json definition of EntityPermission

        :return: json object of EntityPermission
        """
        if limited_view:
            return {
                'permissionName': self.permission_name,
                "isEnabled": self.is_enabled
            }
        return {
            'permissionName': self.permission_name,
            "effect": self.effect.value,
            "description": self.description,
            "isEnabled": self.is_enabled,
            "isGlobal": self.is_global,
            "permissionActions": [permission_action.to_json_dict() for permission_action in self.permission_actions],
            "acl": [acl_item.to_json_dict() for acl_item in self.acl]
        }

    def to_metadb_object(self):
        """
        Convert to metadb related objects

        :return: Secrets
        """
        permission = Permissions(PERMISSION_NAME=self.permission_name, EFFECT=self.effect,
                                 DESCRIPTION=self.description, IS_ENABLED=self.is_enabled)
        permission.rel_permission_actions = [permission_action.to_metadb_object() for permission_action in
                                             self.permission_actions]
        for acl_item in self.acl:
            permission.rel_permissions_acl.append(
                PermissionsACL(PERMISSION_NAME=self.permission_name, SUBJECT_ID=acl_item.subject.subject_id,
                               RELATION_TYPE=acl_item.relation_type, MASTER_OWNER=acl_item.master_owner))
        return permission

    @staticmethod
    def from_metadb_object(db_object: Permissions = None, limited_view: bool = False):
        """
        Convert db object to entity object
        """
        if db_object is None:
            return None
        acl = []
        if limited_view:
            return EntityPermission(db_object.PERMISSION_NAME, PermissionEffectsEnum.allow, "",
                                    db_object.IS_ENABLED,
                                    [])
        is_global = True
        if db_object.rel_permissions_acl is not None:
            for db_acl in db_object.rel_permissions_acl:
                entity_to_acl = EntityPermissionACL(subject=EntitySubject(subject_id=db_acl.SUBJECT_ID,
                                                                          subject_type=db_acl.rel_subject.SUBJECT_TYPE,
                                                                          display_name=db_acl.rel_subject.DISPLAY_NAME),
                                                    relation_type=db_acl.RELATION_TYPE,
                                                    master_owner=db_acl.MASTER_OWNER)
                if (entity_to_acl.subject.subject_type == SubjectTypesEnum.project) and \
                        (entity_to_acl.relation_type == PermissionsACLRelationTypesEnum.owner):
                    is_global = False
                acl.append(entity_to_acl)
        return EntityPermission(db_object.PERMISSION_NAME, db_object.EFFECT, db_object.DESCRIPTION,
                                db_object.IS_ENABLED,
                                [EntityPermissionAction.from_metadb_object(db_per_action) for db_per_action in
                                 db_object.rel_permission_actions], acl, is_global)

    @staticmethod
    def from_metadb_objects(db_objects: list, limited_view: bool = False):
        """
        Convert list of db objects to list of  entity objects
        """
        if not db_objects:
            return []
        result = []
        if limited_view:
            for db_object in db_objects:
                result.append(EntityPermission.from_metadb_object(db_object, limited_view))
            return result
        for db_object in db_objects:
            result.append(EntityPermission.from_metadb_object(db_object))
        return result

    @staticmethod
    def from_metadb_objects_subjects_permissions(db_objects: list = None):
        """
        Convert list of db objects to list of  entity objects
        """
        if not db_objects:
            return []
        subjects = defaultdict(list)

        for SUBJECT_ID, PERMISSION_NAME, IS_ENABLED in db_objects:
            subjects[SUBJECT_ID].append({"permissionName": PERMISSION_NAME, "isEnabled": IS_ENABLED})
        return subjects

    @staticmethod
    def create_actions_object(body):
        """
        Create action list from request body

        :param body:
        :return:
        """
        actions = []
        for action in body.get("actions", []):
            actions.append(EntityPermissionAction(action["actionType"], action["actionDetail"]))
        return actions

    @staticmethod
    def from_json_dict(json_dict, permission_name_path: str = None):
        """
        method for creating entity permission from request
        """
        return EntityPermission(permission_name=permission_name_path if permission_name_path else
        json_dict.get('permissionName'),
                                effect=json_dict.get('effect'),
                                description=json_dict.get('description'),
                                is_enabled=convert_to_bool(json_dict.get('isEnabled', True)),
                                permission_actions=EntityPermission.create_actions_object(json_dict),
                                is_global=convert_to_bool(json_dict.get('isGlobal', False)))
