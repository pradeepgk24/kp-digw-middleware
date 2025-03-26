import json

from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import PermissionActions


class EntityPermissionAction(EntityObject):
    """
    Entity permission action
    """

    def __init__(self, action_type: str, action_detail: dict):
        self._action_type = action_type
        self._action_detail = action_detail

    @property
    def action_type(self):
        """
        Get action_type.

        :return: action_type
        """
        return self._action_type

    @property
    def action_detail(self):
        """
        Get action_detail.

        :return: action_detail
        """
        return self._action_detail

    def to_json_dict(self):
        """
        return json definition of EntityPermissionAction

        :return: json object of EntityPermissionAction
        """
        return {
            'actionType': self.action_type,
            "actionDetail": self.action_detail
        }

    def to_metadb_object(self):
        """
        Convert to metadb related objects

        :return: Secrets
        """
        return PermissionActions(ACTION_TYPE=self.action_type, ACTION_DETAIL=json.dumps(self.action_detail))

    @staticmethod
    def from_metadb_object(db_object: PermissionActions):
        """
        Convert db object to entity object
        """
        if db_object is None:
            return None
        return EntityPermissionAction(db_object.ACTION_TYPE, json.loads(db_object.ACTION_DETAIL))