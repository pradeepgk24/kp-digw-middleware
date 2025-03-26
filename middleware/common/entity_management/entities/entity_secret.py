from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.metadatabase.model.difw_metadb_model import Secrets, SecretsACL
from middleware.common.metadatabase.model.types.secrets_acl_relation_types_enum import SecretsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum


class EntitySecret(EntityObject):
    """
    Entity Secret
    """

    def __init__(self, secret_name: str, secret_manager_name: str = None, description: str = None,
                 acl: list = None, items: dict = None):
        self._secret_name = secret_name
        self._secret_manager_name = secret_manager_name
        self._description = description
        self._acl = acl
        self._items = items

    def set_secret_name(self, secret_name):
        """
        Set secret name
        :param secret_name: value of new secret name
        """
        self._secret_name = secret_name

    def set_secret_manager_name(self, secret_manager_name):
        """
        Set secret manager name
        :param secret_manager_name: value of new secret name
        """
        self._secret_manager_name = secret_manager_name

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
    def description(self):
        """
        Get description.

        :return: description
        """
        return self._description

    @description.setter
    def description(self, value):
        """
        Set value to description property
        Without setter it can not be manually assigned
        """
        self._description = value

    @property
    def secret_name(self):
        """
        Get secret_name.

        :return: secret_name
        """
        return self._secret_name

    @property
    def secret_manager_name(self):
        """
        Get secret_manager_name.

        :return: secret_manager_name
        """
        return self._secret_manager_name

    @secret_manager_name.setter
    def secret_manager_name(self, value):
        """
        Set value to secret_manager_name property
        Without setter it can not be manually assigned
        """
        self._secret_manager_name = value

    @property
    def items(self):
        """
        Get items.

        :return: items
        """
        if self._items is None:
            self._items = dict()
        return self._items

    def add_acl(self, subject: EntitySubject,
                relation: SecretsACLRelationTypesEnum = SecretsACLRelationTypesEnum.owner):
        """
        Add ACL into secret
        """
        self.acl.append(EntityACL(subject, relation))

    def is_subject_owner(self, subject_id):
        """
        Return flag indicates is subject is owner of secret
        """
        return any(EntityACL.filter_entity_acls(self.acl, SecretsACLRelationTypesEnum.owner, [subject_id]))

    def to_json_dict(self):
        """
        return json definition of EntitySecret

        :return: json object of EntitySecret
        """
        if self.items.items():
            return {
                'secretName': self.secret_name,
                "secretManagerName": self.secret_manager_name,
                "description": self.description,
                "acl": [acl_item.to_json_dict() for acl_item in self.acl],
                "items": {key: value for key, value in self.items.items()}
            }
        return {
            'secretName': self.secret_name,
            "secretManagerName": self.secret_manager_name,
            "description": self.description
        }

    def to_metadb_object(self):
        """
        Convert to metadb related objects

        :return: Secrets
        """
        secret = Secrets(SECRET_NAME=self.secret_name, SECRET_MANAGER_NAME=self.secret_manager_name,
                         DESCRIPTION=self.description)
        for acl_item in self.acl:
            secret.rel_secrets_acl.append(
                SecretsACL(SECRET_NAME=self.secret_name, SUBJECT_ID=acl_item.subject.subject_id,
                           RELATION_TYPE=acl_item.relation_type))
        return secret

    @staticmethod
    def from_metadb_object(db_object: Secrets = None):
        """
        Convert db object to entity object
        """
        acl = []
        if db_object is None:
            return None
        if db_object.rel_secrets_acl:
            for db_acl in db_object.rel_secrets_acl:
                acl.append(EntityACL(subject=EntitySubject(subject_id=db_acl.SUBJECT_ID,
                                                           subject_type=db_acl.rel_subject.SUBJECT_TYPE,
                                                           display_name=db_acl.rel_subject.DISPLAY_NAME),
                                     relation_type=db_acl.RELATION_TYPE))
        if db_object is None:
            return None
        return EntitySecret(db_object.SECRET_NAME, db_object.SECRET_MANAGER_NAME, db_object.DESCRIPTION, acl)

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of  entity objects
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntitySecret.from_metadb_object(db_object))
        return result

    @staticmethod
    def from_json_dict(json_dict, name_from_path: str = None):
        """
        create Secret from request information
        if secret name was passed as path parameter - from update secret method
        """
        return EntitySecret(
            secret_name=name_from_path if name_from_path else json_dict.get('secretName').replace('/', '_'),
            secret_manager_name=json_dict.get('secretManagerName'),
            description=json_dict.get('description'),
            items=json_dict.get('items'))


