from middleware.common.entity_management.entities.entity_object import EntityObject


class EntityWorkflowDependencyCondition(EntityObject):
    """
    Entity workflow step dependency condition.
    """

    def __init__(self, name: str, status: str, timeout: str, finish_time_less_then: str, finish_time_greater_then: str,
                 condition_dependency_operator: str):
        self._name = name
        self._status = status
        self._timeout = timeout
        self._finish_time_less_then = finish_time_less_then
        self._finish_time_greater_then = finish_time_greater_then
        self._condition_dependency_operator = condition_dependency_operator

    @property
    def name(self):
        """
        get name

        @return name id
        """
        return self._name

    def set_name(self, name):
        """
        set name

        @param name: new value of name
        """
        self._name = name

    @property
    def status(self):
        """
        get status

        @return status
        """
        return self._status

    def set_status(self, status):
        """
        set status

        @param status: new value of status
        """
        self._status = status

    @property
    def timeout(self):
        """
        get timeout

        @return timeout
        """
        return self._timeout

    def set_timeout(self, timeout):
        """
        set status

        @param timeout: new value of status
        """
        self._timeout = timeout

    @property
    def finish_time_less_then(self):
        """
        get finish_time_less_then

        @return finish_time_less_then
        """
        return self._finish_time_less_then

    def set_finish_time_less_then(self, finish_time_less_then):
        """
        set finishTimeLessThen

        @param finish_time_less_then: new value of finish_time_less_then
        """
        self._finish_time_less_then = finish_time_less_then

    @property
    def finish_time_greater_then(self):
        """
        get finish_time_greater_then

        @return finish_time_greater_then
        """
        return self._finish_time_greater_then

    def set_finish_time_greater_then(self, finish_time_greater_then):
        """
        set finish_time_greater_then

        @param finish_time_greater_then: new value of finish_time_greater_then
        """
        self._finish_time_greater_then = finish_time_greater_then

    @property
    def condition_dependency_operator(self):
        """
        get condition_dependency_operator

        @return condition_dependency_operator
        """
        if not self._condition_dependency_operator:
            self._condition_dependency_operator = "OR"
        return self._condition_dependency_operator

    def set_condition_dependency_operator(self, condition_dependency_operator):
        """
        set condition_dependency_operator

        @param condition_dependency_operator: new value of condition_dependency_operator
        """
        self._condition_dependency_operator = condition_dependency_operator

    def to_json_dict(self):
        """
        Return a JSON representation of Entity workflow dependency condition.
        """
        return {
            "name": self.name,
            "status": self.status,
            "timeout": self.timeout,
            "finishTimeLessThen": self.finish_time_less_then,
            "finishTimeGreaterThen": self.finish_time_greater_then,
            "conditionDependencyOperator": self.condition_dependency_operator
        }

    @staticmethod
    def from_json_dict(workflow_dependency_condition):
        """
        Create instance of this class from dict
        """
        if not workflow_dependency_condition:
            return None
        return EntityWorkflowDependencyCondition(
            name=workflow_dependency_condition.get('name'),
            status=workflow_dependency_condition.get('status'),
            timeout=workflow_dependency_condition.get('timeout'),
            finish_time_less_then=workflow_dependency_condition.get('finishTimeLessThen'),
            finish_time_greater_then=workflow_dependency_condition.get('finishTimeGreaterThen'),
            condition_dependency_operator=workflow_dependency_condition.get('conditionDependencyOperator')
        )