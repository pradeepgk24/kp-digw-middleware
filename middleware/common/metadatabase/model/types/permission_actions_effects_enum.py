# pylint: skip-file
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class PermissionEffectsEnum(DifwMetadbEnum):
    """
    Enum for permission action effects
    """
    allow = 'allow'
    deny = 'deny'