# pylint: skip-file
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class ObjectStatusEnum(DifwMetadbEnum):
    """
    Enum for object status types, some are possible for pipeline templates and some for pipelines
    """
    drafted = 'drafted'
    readyToUse = 'readyToUse'
    queued = "queued"
    running = "running"
    successful = "successful"
    failed = "failed"
    inRefresh = "inRefresh"