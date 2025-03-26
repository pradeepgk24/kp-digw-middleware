import copy

from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_workflow import EntityWorkflow

from middleware.common.entity_management.entities.entity_workflow_step import EntityWorkflowStep
from middleware.common.helpers.exception import BadRequest


class WorkflowGroupsConfigResolver(ConfigPartResolver):
    """
    Resolve groups and tasks related configuration
    """

    def resolve_model_to_config(self, workflow_entity: EntityWorkflow, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """
        # extract steps into dict and check uniqueness of names
        steps_dict = self._convert_steps_to_dict_check_duplicities(workflow_entity.steps)

        # order steps into
        ordered_list = self._order_steps_into_list(steps_dict)

        # resolve attributes of airflow component steps
        job_configuration_part, component_step_name_mapping = self._create_tasks_configuration_section(
            ordered_list)

        # will be place into global configuration as one task group under hardcoded key
        group_config_part = [{"name": "difw_ui_group", "tasks": job_configuration_part}]
        return "groups[:]", group_config_part

    def _convert_steps_to_dict_check_duplicities(self, steps: [EntityWorkflowStep]) -> dict[str, EntityWorkflowStep]:
        """
        Extract and sort steps from workflow model based on parent component name

        @param steps: list of instance EntityWorkflowStep
        @return:
        """
        # need to or
        steps_dict = {}
        # divide steps into hash map, based on component name key
        for step in steps:
            step_name = step.component_name
            if step_name in steps_dict:
                raise Exception(
                    f"There is duplicity within step name. Name of step {step_name} exists more then once ")
            steps_dict[step_name] = step
        self.converter.logger.info(f"Steps names: {list(steps_dict.keys())}")
        return steps_dict

    def _order_steps_into_list(self, steps: dict[str, EntityWorkflowStep]) -> [EntityWorkflowStep]:
        """
        Order steps so the parent steps will be before the child steps
        Those with upstream dependencies will be placed in array only when the parent task are already in list

        @param steps: dict  of instance EntityWorkflowStep
        @return:
        """
        ordered_list = list(steps.keys())
        # loop dependencies and put it into correct order
        for name, step in steps.items():
            if not all(dependency.component_name in steps for dependency in step.dependencies):
                raise BadRequest("There is mapping in dependencies onto component names,"
                                 " which are not present in steps.")
            if step.dependencies:
                step_position = ordered_list.index(name)
                for dependency in step.dependencies:
                    ordered_list.remove(dependency.component_name)
                    ordered_list.insert(step_position, dependency.component_name)
        self.converter.logger.info(f"Ordered steps are: {ordered_list}")
        return [steps[step_name] for step_name in ordered_list]

    def _create_tasks_configuration_section(self, tasks: list) -> (list, dict):
        """
        Convert job section

        @param tasks:
        @return: task configuration result and mapping of componentName -> stepName
        """
        job_configuration_result = []
        component_step_name_mapping = {}
        for step in tasks:
            if self.converter.DIFW_JOB_CATEGORY_SNIFFER == step.definition.get("difwJobCategory"):
                self._create_jobs_airflow_configuration_section(step, component_step_name_mapping,
                                                                job_configuration_result,
                                                                self.converter.DIFW_JOB_CATEGORY_SNIFFER)
            if self.converter.DIFW_JOB_CATEGORY_OPERATOR == step.definition.get("difwJobCategory"):
                self._create_jobs_airflow_configuration_section(step, component_step_name_mapping,
                                                                job_configuration_result,
                                                                self.converter.DIFW_JOB_CATEGORY_OPERATOR)
        return job_configuration_result, component_step_name_mapping

    def _create_jobs_airflow_configuration_section(self, airflow_step_config: EntityWorkflowStep,
                                                   component_step_name_mapping: dict,
                                                   job_configuration_result: list,
                                                   job_category: str) -> None:
        """
        Create job configuration section for airflow component (sniffer/operator)

        @param airflow_step_config: step configuration
        @param component_step_name_mapping:
        @param job_configuration_result: final result fo configuration
        @param job_category: It can be either sniffer or operator

        @return None
        """
        # because of remove operation in next step, copy the definition of step
        airflow_step_definition = copy.deepcopy(airflow_step_config.definition)
        task_type = airflow_step_definition.get("difwTaskType")
        if task_type != "airflow_component":
            raise BadRequest(f"Component {airflow_step_config.component_name} has difw task type {task_type}, which is"
                             f" not supported as it is not airflow_component, revalidate input.")
        airflow_component_type = "operator" if job_category == self.converter.DIFW_JOB_CATEGORY_OPERATOR else "sensor"
        class_attr_name = f"{airflow_component_type}_class"
        kwargs_attr_name = f"{airflow_component_type}_kwargs"
        airflow_configuration = {
            "name": airflow_step_config.component_name,
            "type": task_type,
            "instance_source": "",
            "task_parameters": {}
        }
        airflow_task_parameters_attr = next((attr for attr in airflow_step_definition["attributes"] if
                                             attr["attributeName"] == "airflow_task_parameters"), None)
        if airflow_task_parameters_attr:
            airflow_configuration["task_parameters"].update(
                self._convert_dynamic_attributes_to_simple_dict(airflow_task_parameters_attr["type"]["attributes"]))
            # delete for next processing
            airflow_step_definition["attributes"].remove(airflow_task_parameters_attr)
        if f"{airflow_component_type}Class" in airflow_step_definition.get("componentProperties", {}):
            airflow_configuration["instance_source"] = \
                airflow_step_definition.get("componentProperties")[f"{airflow_component_type}Class"]
            airflow_configuration["task_parameters"].update(
                self._convert_dynamic_attributes_to_simple_dict(airflow_step_definition["attributes"]))
        else:
            class_attr = next((attr for attr in airflow_step_definition["attributes"] if
                               attr["attributeName"] == class_attr_name), None)
            if not class_attr:
                raise Exception(f"Within the step {airflow_step_config.component_name} the {class_attr_name} "
                                f"is missing. Please fix metadata")
            class_kwargs = next((attr for attr in airflow_step_definition["attributes"] if
                                 attr["attributeName"] == kwargs_attr_name), None)
            if not class_kwargs:
                raise Exception(f"Within the step {airflow_step_config.component_name} the {kwargs_attr_name} "
                                f"are missing. Please fix metadata")
            # assign the values to config
            airflow_configuration["instance_source"] = class_attr.get("value")
            airflow_configuration["task_parameters"].update(self._convert_dynamic_attributes_to_simple_dict(
                class_kwargs["type"]["attributes"]))

        # section to hold parent/upstream dependencies of the step
        if airflow_step_config.dependencies:
            upstream_dependencies_list = []
            # go through dependencies and assign them under correct key to
            for dependency in airflow_step_config.dependencies:
                tasks_dependencies = {"name": dependency.component_name}
                condition_list = []
                if dependency.dependency_conditions:
                    tasks_dependencies["condition_evaluator_operator"] = dependency.cross_condition_dependency_operator
                for dependency_condition in dependency.dependency_conditions:
                    condition_dict = {}
                    self.map_object_attr_to_dict_bulk(
                        dependency_condition,
                        condition_dict,
                        [
                            (["name"], ["name"]),
                            (["timeout"], ["timeout"]),
                            (["finish_time_less_then"], ["execution_time_le"]),
                            (["finish_time_greater_then"], ["execution_time_ge"]),
                            (["status"], ["status"]),
                            (["condition_dependency_operator"], ["condition_operator"])
                        ]
                    )
                    condition_list.append(condition_dict)
                if condition_list:
                    tasks_dependencies["conditions"] = condition_list
                upstream_dependencies_list.append(tasks_dependencies)
            airflow_configuration.update({"upstream_dependencies": {"tasks": upstream_dependencies_list}})
            airflow_configuration["upstream_dependencies"]["task_condition_evaluator_operator"] = \
                airflow_step_config.cross_component_dependency_operator.upper()
        job_configuration_result.append(airflow_configuration)
        component_step_name_mapping[airflow_step_config.component_name] = \
            (airflow_step_config.component_name, job_category, None, None)
