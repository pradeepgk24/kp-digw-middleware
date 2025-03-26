from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import DifwCoreVersions


class EntityDifwCoreVersions(EntityObject):
    """
    Entity Difw core version type
    """

    def __init__(self, difw_core_version: str, is_enabled: bool, is_latest: bool):
        self._difw_core_version = difw_core_version
        self._is_enabled = is_enabled
        self._is_latest = is_latest

    @property
    def difw_core_version(self):
        """
        Get difw_core_version.

        :return: difw_core_version
        """
        return self._difw_core_version

    @property
    def is_enabled(self):
        """
        Get is_enabled.

        :return: is_enabled
        """
        return self._is_enabled

    @property
    def is_latest(self):
        """
        Get is_latest.

        :return: is_latest
        """
        return self._is_latest

    def to_json_dict(self):
        """
        return json definition of EntityDifwCoreVersion

        :return: json object of EntityDifwCoreVersion
        """
        return {
            'frameworkVersion': self.difw_core_version,
            'isLatest': self.is_latest
        }

    def to_metadb_object(self):
        """
        Convert to metadb related objects

        :return: DifwCoreVersionTypes
        """
        return DifwCoreVersions(DIFW_CORE_VERSION=self.difw_core_version, IS_ENABLED=self.is_enabled,
                                IS_LATEST=self.is_latest)

    @staticmethod
    def from_metadb_object(db_object: DifwCoreVersions):
        """
        Convert db object to entity object
        """
        if db_object is None:
            return None
        return EntityDifwCoreVersions(db_object.DIFW_CORE_VERSION, db_object.IS_ENABLED,
                                      db_object.IS_LATEST)

