import json

from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_component_type import EntityComponentType
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.metadatabase.model.difw_metadb_model import ComponentTemplates, Components, \
    ComponentsTemplatesACL
from middleware.common.metadatabase.model.types.component_type_categories_enum import ComponentTypeCategoriesEnum
from middleware.api.common.helpers import convert_to_bool


class EntityComponentTemplate(EntityObject):
    """
    Entity component template
    """

    def __init__(self, template_name: str, definition: dict, is_latest: bool,
                 description: str, entity_component_type: EntityComponentType, acl: list, template_id: int = None):
        self._template_name = template_name
        self._template_id = template_id
        self._definition = definition
        self._description = description
        self._is_latest = is_latest
        self._entity_component_type = entity_component_type
        self._acl = acl

    @property
    def template_name(self):
        """
        Get template_name.

        :return: template_name
        """
        return self._template_name

    @property
    def acl(self):
        """
        Get acl.

        :return: acl
        """
        if self._acl is None:
            self._acl = []
        return self._acl

    @property
    def template_id(self):
        """
        Get template_id.

        :return: template_id
        """
        return self._template_id

    def set_template_id(self, template_id):
        """
        Set template_id.

        :return: template_id
        """
        self._template_id = template_id

    @property
    def definition(self):
        """
        Get definition.

        :return: definition
        """
        return self._definition

    @property
    def description(self):
        """
        Get description.

        :return: description
        """
        return self._description

    @property
    def is_latest(self):
        """
        Get is_latest.

        :return: is_latest
        """
        return self._is_latest

    @property
    def entity_component_type(self):
        """
        Get entity_component_type.

        :return: entity_component_type
        """
        return self._entity_component_type

    @staticmethod
    def from_json_dict(json_dict):
        """
        Create instance from json dictionary
        """
        acls = []
        for request_acl in json_dict.get("acl", []):
            acls.append(EntityACL.from_json_dict_ct_acl(request_acl))
        return EntityComponentTemplate(
            template_name=json_dict['templateName'],
            template_id=json_dict.get('templateId', None),
            definition=json_dict['definition'],
            description=json_dict.get('description', ""),
            is_latest=convert_to_bool(json_dict.get('isLatest', True)),
            entity_component_type=EntityComponentType(
                component_type_name=json_dict["entityComponentType"]["componentTypeName"],
                component_category=ComponentTypeCategoriesEnum.from_str(
                    json_dict["entityComponentType"]["componentCategory"]),
                difw_core_version=json_dict["entityComponentType"]["difwCoreVersion"]
            ),
            acl=acls
        )

    def to_json_dict(self, limited_view: bool = False):
        """
        return json definition of EntityComponentTemplate
        :param limited_view: if true, then only limited response should be returned
        :return: json object of EntityComponentTemplate
        """
        if limited_view:
            return {
                'templateName': self.template_name,
                "templateId": self.template_id,
                "description": self.description,
                "isLatest": self.is_latest,
                "entityComponentType": {
                    'componentTypeName': self.entity_component_type.component_type_name,
                    "componentCategory": self.entity_component_type.component_category.value,
                    "difwCoreVersion": self.entity_component_type.difw_core_version,
                },
                "acl": [acl_item.to_json_dict() for acl_item in self.acl]
            }
        return {
            'templateName': self.template_name,
            "templateId": self.template_id,
            "definition": self.definition,
            "description": self.description,
            "isLatest": self.is_latest,
            "entityComponentType": {
                'componentTypeName': self.entity_component_type.component_type_name,
                "componentCategory": self.entity_component_type.component_category.value,
                "difwCoreVersion": self.entity_component_type.difw_core_version,
            },
            "acl": [acl_item.to_json_dict() for acl_item in self.acl]
        }

    def to_metadb_object(self):
        """
        Convert to metadb related objects

        :return: Secrets
        """
        db_object = ComponentTemplates(TEMPLATE_ID=self.template_id, TEMPLATE_NAME=self.template_name,
                                       IS_LATEST=self.is_latest)
        for acl_item in self.acl:
            acl_object = ComponentsTemplatesACL(TEMPLATE_ID=self.template_id,
                                                TEMPLATE_NAME=self.template_name,
                                                SUBJECT_ID=acl_item.subject.subject_id,
                                                RELATION_TYPE=acl_item.relation_type)
            db_object.rel_component_templates_acl.append(acl_object)
        db_object.rel_component = Components(
            COMPONENT_NAME=self.template_name,
            COMPONENT_ID=self.template_id,
            DEFINITION=json.dumps(self.definition, indent=4),
            DESCRIPTION=self.description,
            COMPONENT_TYPE_NAME=self.entity_component_type.component_type_name,
            COMPONENT_TYPE_CATEGORY=self.entity_component_type.component_category,
            DIFW_CORE_VERSION=self.entity_component_type.difw_core_version
        )
        return db_object

    @staticmethod
    def from_metadb_object(db_object: ComponentTemplates):
        """
        Convert db object to entity object
        """
        if db_object is None:
            return None

        acl = []
        if db_object.rel_component_templates_acl:
            for db_acl in db_object.rel_component_templates_acl:
                acl.append(EntityACL(subject=EntitySubject(subject_id=db_acl.SUBJECT_ID,
                                                           subject_type=db_acl.rel_subject.SUBJECT_TYPE,
                                                           display_name=db_acl.rel_subject.DISPLAY_NAME),
                                     relation_type=db_acl.RELATION_TYPE))
        return EntityComponentTemplate(
            template_name=db_object.TEMPLATE_NAME,
            template_id=db_object.TEMPLATE_ID,
            is_latest=db_object.IS_LATEST,
            definition=json.loads(db_object.rel_component.DEFINITION),
            description=db_object.rel_component.DESCRIPTION,
            entity_component_type=EntityComponentType.from_metadb_object(db_object.rel_component.rel_component_type),
            acl=acl
        )

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of  entity objects
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntityComponentTemplate.from_metadb_object(db_object))
        return result
