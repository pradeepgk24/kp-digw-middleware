# pylint: skip-file
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class ComponentTemplatesACLRelationTypesEnum(DifwMetadbEnum):
    """
    Enum for relation types for component templates
    """
    owner = 'owner'
    shared = 'shared'
