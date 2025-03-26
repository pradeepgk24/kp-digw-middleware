# pylint: skip-file
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class ObjectTypesEnum(DifwMetadbEnum):
    """
    Enum for object types
    """
    pipeline = 'pipeline'
    pipeline_template = 'pipeline_template'
    pipeline_table = 'pipeline_table'
    workflow = 'workflow'
    workflow_template = 'workflow_template'
    workflow_table = 'workflow_table'
    component_template = 'component_template'