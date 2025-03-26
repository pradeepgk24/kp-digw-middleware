# pylint: skip-file
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class ProjectAccountTypesEnum(DifwMetadbEnum):
    """
    Enum type for component types
    """
    aws = 'aws'
    databricks = 'databricks'
    airflow = 'airflow'
    github = 'github'