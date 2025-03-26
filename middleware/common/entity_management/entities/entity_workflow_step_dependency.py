from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_workflow_dependency_condition import \
    EntityWorkflowDependencyCondition
from middleware.common.metadatabase.model.difw_metadb_model import ObjectComponentsHierarchy


class EntityWorkflowStepDependency(EntityObject):
    """
    Entity workflow step dependency.
    """

    def __init__(self, component_id: int, component_name: str, cross_condition_dependency_operator: str = None,
                 dependency_conditions: list[EntityWorkflowDependencyCondition] = None):
        self._component_id = component_id
        self._component_name = component_name
        self._cross_condition_dependency_operator = cross_condition_dependency_operator
        self._dependency_conditions = dependency_conditions

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

        :param component_id: new value of component_id
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

        :param component_name: new value of component_name
        """
        self._component_name = component_name

    @property
    def cross_condition_dependency_operator(self):
        """
        get cross_condition_dependency_operator

        @return cross_condition_dependency_operator
        """
        if not self._cross_condition_dependency_operator:
            self._cross_condition_dependency_operator = "OR"
        return self._cross_condition_dependency_operator

    @property
    def dependency_conditions(self):
        """
        get dependency_conditions

        @return dependency_conditions
        """
        if not self._dependency_conditions:
            self._dependency_conditions = []
        return self._dependency_conditions

    def to_json_dict(self):
        """
        Return a JSON representation of Entity workflow step dependency.
        """
        return {
            "componentId": self.component_id,
            "componentName": self.component_name,
            "crossConditionsDependencyOperator": self.cross_condition_dependency_operator,
            "dependencyConditions": [condition.to_json_dict() for condition in self.dependency_conditions]
        }

    @staticmethod
    def from_json_dict(workflow_dependency):
        """
        Create instance of this class from dict
        """
        if not workflow_dependency:
            return None
        return EntityWorkflowStepDependency(
            component_id=workflow_dependency.get('componentId'),
            component_name=workflow_dependency.get('componentName'),
            cross_condition_dependency_operator=workflow_dependency.get('crossConditionsDependencyOperator'),
            dependency_conditions=[EntityWorkflowDependencyCondition.from_json_dict(dependency_condition) for
                                   dependency_condition in workflow_dependency.get('dependencyConditions', [])]
        )

    @staticmethod
    def from_metadb_object(db_hierarchy_object: ObjectComponentsHierarchy):
        return EntityWorkflowStepDependency(
            component_id=db_hierarchy_object.PARENT_COMPONENT_ID,
            component_name=None,
            cross_condition_dependency_operator=db_hierarchy_object.PROPERTIES.get('crossConditionsDependencyOperator'),
            dependency_conditions=[EntityWorkflowDependencyCondition.from_json_dict(dependency_condition) for
                                   dependency_condition in
                                   db_hierarchy_object.PROPERTIES.get('dependencyConditions', [])]
        )