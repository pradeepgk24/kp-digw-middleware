# pylint: skip-file
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class ComponentTypeCategoriesEnum(DifwMetadbEnum):
    """
    Enum type for component types
    """
    data_type = 'data_type'
    input_connector = 'input_connector'
    output_connector = 'output_connector'
    processor = 'processor'
    transformer = 'transformer'
    data_transformation_tool = "data_transformation_tool"
    airflow_component = "airflow_component"
    pipeline_object = "pipeline_object"


