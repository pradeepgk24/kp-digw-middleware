from sqlalchemy.engine import Row

from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import Subjects
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum


class EntitySubject(EntityObject):
    """
    Entity Subject
    """

    def __init__(self, subject_id: str, subject_type: SubjectTypesEnum, display_name: str = "", description: str = "",
                 is_enabled: bool = True):
        self._subject_id = subject_id
        self._subject_type = subject_type
        self._display_name = display_name
        self._description = description
        self._is_enabled = is_enabled
        self._children = []
        self._parents = []

    @property
    def children(self):
        """
        Get children

        @return: children
        """
        return self._children

    @property
    def description(self):
        """
        Get description

        @return: description
        """
        return self._description

    @property
    def is_enabled(self):
        """
        Get is_enabled

        @return: is_enabled
        """
        return self._is_enabled

    @property
    def subject_id(self):
        """
        Get project subject_id.

        @return: subject_id
        """
        return self._subject_id

    @property
    def subject_type(self):
        """
        Get project subject_type.

        @return: subject_type
        """
        return self._subject_type

    @property
    def display_name(self):
        """
        Get display_name

        @return: display_name
        """
        return self._display_name

    def set_display_name(self, display_name):
        """
        Set Display name

        @return display name
        """
        self._display_name = display_name

    def set_description(self, description):
        """
        Set description

        @return new value for description
        """
        self._description = description

    def set_is_enabled(self, is_enabled):
        """
        Set is_enabled.

        @return: is_enabled
        """
        self._is_enabled = is_enabled

    def set_children(self, children):
        """
        Sets the children

        :param children:
        @return:
        """
        self._children = children

    @property
    def parents(self):
        """
        Get parents

        @return: parents
        """
        return self._parents

    def set_parents(self, parents):
        """
        Sets the parents

        :param parents:
        @return:
        """
        self._parents = parents

    def to_json_dict(self):
        """
        return json definition of EntitySubject

        @return: json object of EntitySubject
        """
        response = {
            'subjectId': self.subject_id,
            "subjectType": self.subject_type.value,
            "displayName": self.display_name if self.display_name else self.subject_id,
            "description": self.description,
            "isEnabled": self.is_enabled,
            'children': [child.to_json_dict() for child in self.children],

        }
        # parents will be sent in response only if getParents flag is set to true
        if self.parents:
            response.update({'parents': [parent.to_json_dict() for parent in self.parents]})
        return response

    def to_metadb_object(self):
        """
        Convert db object to entity object
        """
        display_name = self.display_name if self.display_name else self.subject_id
        return Subjects(SUBJECT_ID=self.subject_id, SUBJECT_TYPE=self.subject_type, DISPLAY_NAME=display_name,
                        DESCRIPTION=self.description, IS_ENABLED=self.is_enabled)

    @staticmethod
    def filter_subjects_by_type(subject_type: SubjectTypesEnum, subjects: list, uselist=True):
        """
        Filter list of subjects by type

        :param subject_type: type of subject
        :param subjects: list of subjects to filter
        :param uselist: Flag indicates if return type should be list or single EntitySubject OBJ
        @return: list of EntitySubject of type of param subject_type or only single EntitySubject obj
        """
        if not subjects:
            return None

        list_result = list(filter(lambda subj_obj: subj_obj.subject_type == subject_type, subjects))
        if uselist:
            return list_result
        if list_result:
            return list_result[0]
        return None

    @staticmethod
    def from_metadb_object(db_object):
        """
        Convert db object to entity object
        """
        if db_object is None:
            return None
        return EntitySubject(db_object.SUBJECT_ID, db_object.SUBJECT_TYPE, db_object.DISPLAY_NAME,
                             db_object.DESCRIPTION, db_object.IS_ENABLED)

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of  entity objects
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntitySubject.from_metadb_object(db_object))
        return result