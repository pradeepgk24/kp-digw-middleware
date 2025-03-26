# pylint: skip-file

import json

from middleware.common.metadatabase.model.difw_metadb_model import Components, ObjectComponents
from middleware.common.entity_management.entities.entity_workflow_step_dependency \
    import EntityWorkflowStepDependency
from middleware.common.entity_management.entities.entity_object import EntityObject


class EntityWorkflowStep(EntityObject):
    """
    Entity workflow Step
    """

    def __init__(self, component_id: int, component_name: str, cross_component_dependency_operator: str = None,
                 description: str = None, dependencies: [EntityWorkflowStepDependency] = None, definition: dict = None,
                 component_coordinates: dict = None, properties: dict = None, linked_workflow=None):
        self._component_id = component_id
        self._component_name = component_name
        self._cross_component_dependency_operator = cross_component_dependency_operator
        self._description = description
        self._dependencies = dependencies
        self._definition = definition
        self._component_coordinates = component_coordinates
        self._properties = properties
        self._linked_workflow = linked_workflow

    @property
    def properties(self):
        """
        get properties

        @return properties
        """
        return self._properties

    def set_properties(self, properties):
        """
        set properties

        @param properties: new value of properties
        """
        self._properties = properties

    @property
    def linked_workflow(self):
        """
        get linked_workflow

        @return linked_workflow
        """
        return self._linked_workflow

    def set_linked_workflow(self, linked_workflow):
        """
        set linked_workflow

        @param linked_workflow: new value of linked_workflow
        """
        self._linked_workflow = linked_workflow

    @property
    def component_id(self):
        """
        get component_id

        @return component id
        """
        return self._component_id

    def set_component_id(self, component_id):
        """
        set component_id

        @param component_id: new value of component_id
        """
        self._component_id = component_id

    @property
    def component_name(self):
        """
        get component_name

        @return component_name
        """
        return self._component_name

    def set_component_name(self, component_name):
        """
        set component_name

        @param component_name: new value of component_name
        """
        self._component_name = component_name

    @property
    def cross_component_dependency_operator(self):
        """
        get cross_component_dependency_operator

        @return cross_component_dependency_operator
        """
        if not self._cross_component_dependency_operator:
            self._cross_component_dependency_operator = "OR"
        return self._cross_component_dependency_operator

    @property
    def description(self):
        """
        get description

        @return description id
        """
        return self._description

    @property
    def definition(self):
        """
        get definition

        @return description id
        """
        return self._definition

    @property
    def dependencies(self):
        """
        get dependency_condition

        @return dependency_condition
        """
        if not self._dependencies:
            return []
        return self._dependencies

    @property
    def component_coordinates(self):
        """
        get component_coordinates

        @return component_coordinates id
        """
        if not self._component_coordinates:
            return {}
        return self._component_coordinates

    def set_component_coordinates(self, component_coordinates):
        """
        set component_coordinates

        @param component_coordinates: new value of component_coordinates
        """
        self._component_coordinates = component_coordinates

    def to_json_dict(self):
        """
        Return a JSON representation of Entity workflow Steps.
        """
        return {
            "componentId": self.component_id,
            "componentName": self.component_name,
            "parentComponents": {
                "crossComponentDependencyOperator": self.cross_component_dependency_operator,
                "dependencies": [dependency.to_json_dict() for dependency in self.dependencies]
            },
            "description": self.description,
            "model": self.definition.copy(),
            "coordinates": self.component_coordinates
        }

    @staticmethod
    def from_json_dict(workflow_step_model):
        """
        Create instance of this class from dict
        """
        if not workflow_step_model:
            return None
        parent_components = workflow_step_model.get('parentComponents', {})
        return EntityWorkflowStep(
            component_id=workflow_step_model.get('componentId'),
            component_name=workflow_step_model['componentName'],
            description=workflow_step_model.get('description'),
            cross_component_dependency_operator=parent_components.get('crossComponentDependencyOperator') if
            parent_components else None,
            dependencies=[EntityWorkflowStepDependency.from_json_dict(dependency) for dependency in
                          parent_components.get("dependencies", [])] if parent_components else None,
            definition=workflow_step_model.get('model'),
            component_coordinates=workflow_step_model.get('coordinates')
        )

    @staticmethod
    def from_metadb_object(db_component_object: ObjectComponents):
        """
        Convert from DB object to entity workflow steps object
        @param db_component_object: object to convert
        @return: Entity workflow steps
        """
        dependencies: [EntityWorkflowStepDependency] = []
        if db_component_object.rel_parent_components_hierarchy:
            # in case of pipeline there is only one child
            for db_component_hierarchy_object in db_component_object.rel_parent_components_hierarchy:
                dependencies.append(EntityWorkflowStepDependency.from_metadb_object(db_component_hierarchy_object))

        return EntityWorkflowStep(
            component_id=db_component_object.COMPONENT_ID,
            component_name=db_component_object.COMPONENT_NAME,
            description=db_component_object.rel_component.DESCRIPTION,
            cross_component_dependency_operator=db_component_object.rel_component.PROPERTIES.get(
                "crossComponentDependencyOperator"),
            dependencies=dependencies,
            definition=json.loads(db_component_object.rel_component.DEFINITION),
            component_coordinates=json.loads(
                db_component_object.COMPONENT_COORDINATES) if db_component_object.COMPONENT_COORDINATES else None
        )

    @staticmethod
    def from_metadb_objects(db_component_objects: [ObjectComponents]):
        workflow_steps = []
        if db_component_objects:
            for object_component in db_component_objects:
                workflow_steps.append(EntityWorkflowStep.from_metadb_object(object_component))
        return workflow_steps