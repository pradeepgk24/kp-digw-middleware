
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class EntityPermissionACL(EntityACL):
    """
    Entity permission ACL
    """

    def __init__(self, subject: EntitySubject, relation_type: DifwMetadbEnum, master_owner: str = None):
        super().__init__(subject, relation_type)
        self._master_owner = master_owner

    @property
    def master_owner(self):
        """
        Get master_owner of permission.

        :return: string
        """
        return self._master_owner