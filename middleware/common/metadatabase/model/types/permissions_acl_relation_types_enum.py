# pylint: skip-file
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class PermissionsACLRelationTypesEnum(DifwMetadbEnum):
    """
    Enum for permission acl relation types
    """
    owner = 'owner'
    assigned = 'assigned'