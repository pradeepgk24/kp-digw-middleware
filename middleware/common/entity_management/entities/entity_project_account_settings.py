import json

from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import ProjectAccountSettings
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum


class EntityProjectAccountSettings(EntityObject):
    """
    Entity Project account settings
    """

    def __init__(self, project_id, account_type: ProjectAccountTypesEnum, account_details):
        self._account_type = account_type
        self._account_details = account_details
        self._project_id = project_id

    @property
    def account_type(self):
        """
        Get project account type.

        :return: account type
        """
        return self._account_type

    @property
    def account_details(self):
        """
        Get project account details.

        :return: account details
        """
        return self._account_details

    @property
    def project_id(self):
        """
        Get project Id

        :return: project Id
        """
        return self._project_id

    def to_json_dict(self):
        """
        return json definition of EntityProjectAccountSettings

        :return: json object of EntityProjectAccountSettings
        """
        # only account details are needed here
        return self.account_details

    def to_metadb_object(self):
        """
        Convert to metadb related objects

        :return: type ProjectAccountSettings
        """
        return ProjectAccountSettings(PROJECT_ID=self.project_id, ACCOUNT_TYPE=self.account_type,
                                      ACCOUNT_DETAILS=json.dumps(self.account_details, indent=4))

    @staticmethod
    def from_metadb_object(db_object: ProjectAccountSettings):
        if db_object is None:
            return None
        return EntityProjectAccountSettings(db_object.PROJECT_ID, db_object.ACCOUNT_TYPE,
                                            json.loads(db_object.ACCOUNT_DETAILS))