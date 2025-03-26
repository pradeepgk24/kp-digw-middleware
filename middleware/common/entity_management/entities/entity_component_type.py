import json
import copy

from common.helpers.exception import ValidationException
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import ComponentTypes
from middleware.common.metadatabase.model.types.component_type_categories_enum import ComponentTypeCategoriesEnum


class EntityComponentType(EntityObject):
    """
    Entity component type
    """

    def __init__(self, component_type_name: str, component_category: ComponentTypeCategoriesEnum,
                 difw_core_version: str,
                 definition: dict = None):
        self._component_type_name = component_type_name
        self._component_category = component_category
        self._difw_core_version = difw_core_version
        self._definition = definition

    @property
    def component_type_name(self):
        """
        Get project component_type_name.

        @return: component_type_name
        """
        return self._component_type_name

    @property
    def component_category(self):
        """
        Get project component_category.

        @return: component_category
        """
        return self._component_category

    def set_component_category(self, component_category):
        """
        Set project component_category.

        @param component_category: New category of component
        """
        self._component_category = component_category

    @property
    def difw_core_version(self):
        """
        Get project difw_core_version.

        @return: difw_core_version
        """
        return self._difw_core_version

    @property
    def definition(self):
        """
        Get project definition.

        @return: definition
        """
        return self._definition

    def to_json_dict(self):
        """
        return json definition of EntityComponentType

        @return: json object of EntityComponentType
        """
        return {
            'componentTypeName': self.component_type_name,
            "componentCategory": self.component_category.value,
            "difwCoreVersion": self.difw_core_version,
            "definition": self.definition
        }

    def from_pipeline_object_metadata_db(self, db_pipeline_object: dict, airflow_connection_id):
        """
        Convert Db pipeline object into pipeline metadata using dag trigger template

        @param db_pipeline_object:
        @param airflow_connection_id:
        """
        if self.component_category != ComponentTypeCategoriesEnum.airflow_component and \
                self.component_type_name == "dag_trigger":
            raise ValidationException(
                f"The component type {self.component_category}/{self.component_type_name} can not be transfer to "
                f"pipeline object metadata")

        pipeline_object = EntityComponentType(component_type_name=db_pipeline_object["pipeline_name"],
                                              component_category=ComponentTypeCategoriesEnum.pipeline_object,
                                              difw_core_version=self.difw_core_version,
                                              definition=copy.deepcopy(self.definition))
        dag_id = None
        runtime_steps = []
        for pipeline_property in db_pipeline_object['properties']:
            if pipeline_property['PROPERTY_NAME'] == "dagId":
                dag_id = pipeline_property['PROPERTY_STRING_VALUE']
            if pipeline_property['PROPERTY_NAME'] == "runtimeSteps":
                runtime_steps = json.loads(pipeline_property['PROPERTY_LONGTEXT_VALUE'])
        if dag_id is None:
            # if there is no dag Id then the pipeline will not be used
            return None
        template_trigger_attributes = \
            pipeline_object.definition.get("attributes")[0]["type"]["elementsType"]["attributes"]

        # assign dag id
        dag_id_attr = copy.deepcopy(template_trigger_attributes[0])
        dag_id_attr["value"] = dag_id
        dag_id_attr["isVisible"] = False  # visibility set to false

        # assign connection id
        conn_id_attr = copy.deepcopy(template_trigger_attributes[1])
        conn_id_attr["value"] = airflow_connection_id
        conn_id_attr["isVisible"] = False  # visibility set to false

        # remove documentation link
        del pipeline_object.definition["documentationLink"]

        # update definition attributes
        pipeline_object.definition["componentCategory"] = ComponentTypeCategoriesEnum.pipeline_object.value
        pipeline_object.definition["displayName"] = db_pipeline_object['pipeline_name']
        pipeline_object.definition.get("attributes")[0]["value"] = [{
            "attributes": [
                dag_id_attr,
                conn_id_attr,
                copy.deepcopy(template_trigger_attributes[2]),  # here is logical_date
                copy.deepcopy(template_trigger_attributes[3]),  # here is conflict_resolution
                copy.deepcopy(template_trigger_attributes[4])  # here is wait_for_dag
            ]
        }]
        # TODO https://issues.merck.com/browse/NGA-4667
        if runtime_steps:
            pipeline_object.definition.get("attributes")[1]["type"]["attributes"] = runtime_steps
        else:
            del pipeline_object.definition.get("attributes")[1]

        # temporary delete runtime parameters for now
        # del pipeline_object.definition.get("attributes")[1]
        # delete UI icon also
        del pipeline_object.definition["uiProperties"]
        return pipeline_object

    @staticmethod
    def from_metadb_objects(db_objects: [ComponentTypes]) -> list:
        """
        Convert list of db objects to entity object
        @param db_objects: list of input db objects
        @return: list of EntityComponentType
        """
        result: [ComponentTypes] = []
        for db_object in db_objects:
            result.append(EntityComponentType.from_metadb_object(db_object))
        return result

    @staticmethod
    def from_metadb_object(db_object: ComponentTypes):
        """
        Convert db object to entity object
        """
        if db_object is None:
            return None
        return EntityComponentType(db_object.COMPONENT_TYPE_NAME, db_object.COMPONENT_TYPE_CATEGORY,
                                   db_object.DIFW_CORE_VERSION,
                                   json.loads(db_object.DEFINITION))
