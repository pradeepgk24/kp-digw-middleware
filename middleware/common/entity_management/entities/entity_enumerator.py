from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import Enumerators


class EntityEnumerator(EntityObject):
    """
    Entity Enumerator
    """

    def __init__(self, enumerator_category: str, enumerator_value: str = "", display_name: str = ""):
        self._enumerator_category = enumerator_category
        self._enumerator_value = enumerator_value
        self._display_name = display_name

    @property
    def display_name(self):
        """
        Get display_name

        :return: display_name
        """
        return self._display_name

    @property
    def enumerator_value(self):
        """
        Get enumerator_value

        :return: enumerator_value
        """
        return self._enumerator_value

    @property
    def enumerator_category(self):
        """
        Get enumerator_category.

        :return: enumerator_category
        """
        return self._enumerator_category

    def set_enumerator_value(self, enumerator_value):
        """
        Set enumerator_value.

        :return: enumerator_value
        """
        self._enumerator_value = enumerator_value

    def set_display_name(self, display_name):
        """
        Set display_name

        :return display_name
        """
        self._display_name = display_name

    def set_enumerator_category(self, enumerator_category):
        """
        Set enumerator_category

        :return: enumerator_category
        """
        self._enumerator_category = enumerator_category

    def to_json_dict(self):
        """
        return json definition of EntityEnumerator
        :return: json object of EntityEnumerator
        """
        return {
            "enumeratorCategory": self.enumerator_category,
            "enumeratorValue": self.enumerator_value,
            "displayName": self.display_name
        }

    def to_metadb_object(self):
        """
        Convert db object to entity object
        """
        return Enumerators(ENUMERATOR_CATEGORY=self.enumerator_category, ENUMERATOR_VALUE=self.enumerator_value,
                           DISPLAY_NAME=self.display_name)

    @staticmethod
    def from_metadb_object(db_object):
        """
        Convert db object to entity object
        """
        if db_object is None:
            return None
        return EntityEnumerator(db_object.ENUMERATOR_CATEGORY, db_object.ENUMERATOR_VALUE,
                                db_object.DISPLAY_NAME)

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of  entity objects
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntityEnumerator.from_metadb_object(db_object))
        return result
