import json

from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import PermissionActionTypes


class EntityPermissionActionType(EntityObject):
    """
    Entity permission action type
    """

    def __init__(self, action_type: str, definition: dict, description: str):
        self._action_type = action_type
        self._definition = definition
        self._description = description

    @property
    def action_type(self):
        """
        Get action_type.

        :return: action_type
        """
        return self._action_type

    @property
    def definition(self):
        """
        Get definition.

        :return: definition
        """
        return self._definition

    @property
    def description(self):
        """
        Get description.

        :return: description
        """
        return self._description

    def to_json_dict(self):
        """
        return json definition of EntityPermissionActionType

        :return: json object of EntityPermissionActionType
        """
        return {
            'permissionActionType': self.action_type,
            "actionDescription": self.description,
            "definition": self.definition
        }

    def to_metadb_object(self):
        """
        Convert to metadb related objects

        :return: PermissionActionTypes
        """
        return PermissionActionTypes(ACTION_TYPE=self.action_type, DEFINITION=json.dumps(self.definition),
                                     DESCRIPTION=self.description)

    @staticmethod
    def from_metadb_object(db_object: PermissionActionTypes):
        """
        Convert db object to entity object
        """
        if db_object is None:
            return None
        return EntityPermissionActionType(db_object.ACTION_TYPE, json.loads(db_object.DEFINITION),
                                          db_object.DESCRIPTION)
