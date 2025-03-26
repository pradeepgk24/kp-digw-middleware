# pylint: skip-file
import json
import copy

from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import ObjectComponents


class EntityPipelineSteps(EntityObject):
    """
    Entity Pipeline Steps
    """

    def __init__(self, component_id, component_name, child_component_name, description, definition,
                 component_coordinates, framework_version=None):
        self._component_id = component_id
        self._component_name = component_name
        self._child_component_name = child_component_name
        self._description = description
        self._definition = definition
        self._component_coordinates = component_coordinates
        self._framework_version = framework_version

    @property
    def component_id(self):
        """
        get component_id

        return component id
        """
        return self._component_id

    def set_component_id(self, component_id):
        """
        set component_id

        :param component_id: new value of component_id
        """
        self._component_id = component_id

    @property
    def component_name(self):
        """
        get component_name

        return component_name
        """
        return self._component_name

    def set_child_component_name(self, child_component_name):
        """
        set child_component_name

        :param child_component_name: new value of child_component_name
        """
        self._child_component_name = child_component_name

    @property
    def child_component_name(self):
        """
        get child_component_name

        return child_component_name
        """
        return self._child_component_name

    @property
    def description(self):
        """
        get description

        return description
        """
        return self._description

    @property
    def definition(self):
        """
        get definition/model

        return definition/model
        """
        if self._definition is None:
            self._definition = {}
        return self._definition

    @property
    def framework_version(self):
        """
        get framework_version

        return framework_version
        """
        return self._framework_version

    @property
    def component_coordinates(self):
        """
        get component_coordinates

        return component_coordinates
        """
        return self._component_coordinates

    def to_json_dict(self):
        """
        Return a JSON representation of Entity Pipeline Steps.
        """
        return {
            "componentId": self.component_id,
            "componentName": self.component_name,
            "coordinates": self.component_coordinates,
            "childComponent": self.child_component_name,
            "description": self.description,
            "model": copy.deepcopy(self.definition)
        }

    def create_copy(self):
        """
        Method will create exact copy of the object itself
        """
        return EntityPipelineSteps.from_json_dict(self.to_json_dict(), self.framework_version)

    @staticmethod
    def from_json_dict(step_model, framework_version):
        """
        Create instance of this class from model/dict/request
        """
        if not step_model:
            return None
        return EntityPipelineSteps(
            component_id=step_model.get('componentId'),
            component_name=step_model['componentName'],
            component_coordinates=step_model.get('coordinates'),
            definition=step_model.get('model'),
            description=step_model.get('description'),
            child_component_name=step_model.get('childComponent'),
            framework_version=framework_version
        )

    @staticmethod
    def from_metadb_object(db_object: ObjectComponents, id_component_name_pair: dict):
        """
        Convert from DB object to entity pipeline steps object
        :param db_object: object to convert
        :param id_component_name_pair: dict of component ids and their instances
        :return: Entity Pipeline steps
        """
        child_component_name = None
        if db_object.rel_child_components_hierarchy:
            # in case of pipeline there is only one child
            child_component_name = id_component_name_pair.get(
                db_object.rel_child_components_hierarchy[0].CHILD_COMPONENT_ID).COMPONENT_NAME
        return EntityPipelineSteps(
            component_id=db_object.COMPONENT_ID,
            component_name=db_object.COMPONENT_NAME,
            component_coordinates=json.loads(
                db_object.COMPONENT_COORDINATES) if db_object.COMPONENT_COORDINATES else None,
            definition=json.loads(db_object.rel_component.DEFINITION),
            description=db_object.rel_component.DESCRIPTION,
            child_component_name=child_component_name
        )

    @staticmethod
    def from_metadb_objects(db_component_objects: [ObjectComponents]):
        pipeline_steps = []
        if db_component_objects:
            id_component_name_pair = {db_component_object.COMPONENT_ID: db_component_object for db_component_object in
                                      db_component_objects}
            for object_component in db_component_objects:
                pipeline_steps.append(EntityPipelineSteps.from_metadb_object(object_component, id_component_name_pair))
        return pipeline_steps
