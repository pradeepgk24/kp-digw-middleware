# pylint: skip-file
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class ObjectsACLRelationTypesEnum(DifwMetadbEnum):
    """
    Enum for relation types for objects
    """
    owner = 'owner'
    shared = 'shared'
    # in case of sharing pipeline template as whole, not the inner pipeline, but the outer template
    shared_template = "shared_template"
