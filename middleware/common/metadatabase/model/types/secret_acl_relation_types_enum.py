# pylint: skip-file
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class SecretsACLRelationTypesEnum(DifwMetadbEnum):
    """
    Enum for secret acl relation types
    """
    owner = 'owner'