# pylint: skip-file
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class SubjectTypesEnum(DifwMetadbEnum):
    """
    Enum for subject types
    """
    user = 'user'
    group = 'group'
    project = 'project'