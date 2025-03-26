from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.metadatabase.model.difw_metadb_model import ComponentsTemplatesACL, ObjectsACL
from middleware.common.metadatabase.model.types.component_templates_acl_relation_types_enum import \
    ComponentTemplatesACLRelationTypesEnum
from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum


class EntityACL(EntityObject):
    """
    Entity ACL
    """

    def __init__(self, subject: EntitySubject, relation_type: DifwMetadbEnum):
        self._subject = subject
        self._relation_type = relation_type

    @property
    def relation_type(self):
        """
        Get project relation_type.

        :return: subject_type
        """
        return self._relation_type

    @property
    def subject(self):
        """
        Get project subject.

        :return: subject
        """
        return self._subject

    @staticmethod
    def from_json_dict_object_acl(acl_model):
        """
        Create class instance from model/dict/request
        """
        return EntityACL(
            subject=EntitySubject(subject_id=acl_model["subjectId"],
                                  display_name=acl_model.get("displayName"),
                                  subject_type=SubjectTypesEnum.from_str(acl_model["subjectType"])),
            relation_type=ObjectsACLRelationTypesEnum.from_str(acl_model["relationship"])
        )

    @staticmethod
    def from_json_dict_ct_acl(acl_model):
        """
        Create class instance from model/dict/request
        """
        return EntityACL(
            subject=EntitySubject(subject_id=acl_model["subjectId"],
                                  display_name=acl_model.get("displayName"),
                                  subject_type=SubjectTypesEnum.from_str(acl_model["subjectType"])),
            relation_type=ComponentTemplatesACLRelationTypesEnum.from_str(acl_model["relationship"])
        )

    def to_json_dict(self):
        """
        return json definition of EntityACL

        :return: json object of EntityACL
        """
        return {
            'subjectId': self.subject.subject_id,
            "subjectType": self.subject.subject_type.value,
            "displayName": self.subject.display_name,
            "relationship": self.relation_type.value
        }

    @staticmethod
    def from_metadb_object_component_templates_acl(db_object: ComponentsTemplatesACL):
        """
        Convert from DB object ComponentsTemplatesACL to entity acl object
        :param db_object: object to convert
        :return: EntityACL object
        """
        return EntityACL(relation_type=db_object.RELATION_TYPE,
                         subject=EntitySubject(subject_id=db_object.SUBJECT_ID,
                                               subject_type=db_object.rel_subject.SUBJECT_TYPE,
                                               display_name=db_object.rel_subject.DISPLAY_NAME))

    @staticmethod
    def from_metadb_object_objects_acl(db_object: ObjectsACL):
        """
        Convert from DB object ObjectsACL to entity acl object
        :param db_object: object to convert
        :return: EntityACL object
        """
        return EntityACL(relation_type=db_object.RELATION_TYPE,
                         subject=EntitySubject(subject_id=db_object.SUBJECT_ID,
                                               subject_type=db_object.rel_subject.SUBJECT_TYPE,
                                               display_name=db_object.rel_subject.DISPLAY_NAME))

    @staticmethod
    def from_metadb_object_objects_acls(db_objects: [ObjectsACL]):
        """
        Convert from DB object ObjectsACL to entity acl object
        :param db_objects: list of objects to convert
        :return: list of EntityACL object
        """
        result_list = []
        for db_object in db_objects:
            result_list.append(EntityACL.from_metadb_object_objects_acl(db_object))
        return result_list

    @staticmethod
    def from_metadb_objects_component_templates_acl(db_objects: list):
        """
        Convert from list of DB objects to list of entity acl objects
        :param db_objects: list of ComponentsTemplatesACL
        :return: list of EntityACL objects
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntityACL.from_metadb_object_component_templates_acl(db_object))
        return result

    @staticmethod
    def filter_entity_acls(entity_acl_objects, relation_type: DifwMetadbEnum = None, subjects_ids: list = None):
        """
        Filter acl entities by type

        :param entity_acl_objects: list of EntityAcl objects
        :param relation_type: list relation type
        :param subjects_ids: id of subjects
        :return: list of EntityACL objects
        """
        if not subjects_ids:
            subjects_ids = []
        return list(
            filter(lambda acl_obj: (relation_type is None or acl_obj.relation_type == relation_type) and
                                   (not subjects_ids or acl_obj.subject.subject_id in subjects_ids),
                   entity_acl_objects))
