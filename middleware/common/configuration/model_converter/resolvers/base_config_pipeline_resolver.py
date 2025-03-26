from abc import abstractmethod

from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_base_pipeline import EntityBasePipeline
from middleware.common.entity_management.entities.entity_pipeline_steps import EntityPipelineSteps
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from middleware.common.helpers.datetime_formater import from_datetime_to_standard_no_timezone_str


class BasePipelineGlobalConfigResolver(ConfigPartResolver):
    """
    Resolve general root configuration
    """

    @abstractmethod
    def resolve_dataset_name(self, entity_base_pipeline: EntityBasePipeline, **kwargs):
        """
        This method resolve dataset name. The name of dataset depends on if it is pipeline or pipeline template.
        In case it is pipeline the pipeline_name parameter needs to be taken
        In case it is pipeline template the pipeline_template_name parameter needs to be taken
        """
        pass

    def resolve_model_to_config(self, entity_base_pipeline: EntityBasePipeline, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """
        general_configuration = {}
        if "{{dataset_name}}" not in entity_base_pipeline.resource_prefix:
            entity_base_pipeline.set_resource_prefix(entity_base_pipeline.resource_prefix + "_{{dataset_name}}")
        platform_configuration = kwargs['platform_configuration']
        self.map_object_attr_to_dict_bulk(
            entity_base_pipeline,
            general_configuration,
            [
                (["resource_prefix"], ["resource_prefix"], None),
                (["platform"], ["platform"], "glue"),
                (["schedule"], ["schedule"], None),
                (["initial_load_start_date"], ["initial_load", "start_date"], None, True,
                 from_datetime_to_standard_no_timezone_str),
                (["lower_bound_start_date"], ["initial_load", "lower_bound"], None, True,
                 from_datetime_to_standard_no_timezone_str),
                (["enable_deffer_operators"], ["defer"], False)
            ]
        )
        general_configuration["region"] = kwargs.get('region', 'us-east-1')
        # if there is no aws_connection_name in entity, use one from project_settings
        if not entity_base_pipeline.advanced_options.entity_airflow_options.aws_connection_name:
            general_configuration["airflow_connection"] = platform_configuration[
                ProjectAccountTypesEnum.airflow].account_details.get(
                "awsConnectionName",
                "aws_srv_ingest_user_{{env}}")
        # if there are no airflow_tags in entity, use tags from project_settings
        if not entity_base_pipeline.advanced_options.entity_airflow_options.airflow_tags and\
                platform_configuration[ProjectAccountTypesEnum.airflow].account_details.get("tags"):
            general_configuration["airflow_tags"] = platform_configuration[
                ProjectAccountTypesEnum.airflow].account_details.get("tags")
        if entity_base_pipeline.initial_load_start_date is not None:
            general_configuration["catchup"] = True
        # resolve additional jar dependencies
        additional_jar_dependencies = self._resolve_additional_jar_dependencies(entity_base_pipeline.steps)
        if additional_jar_dependencies:
            general_configuration['additional_jar_dependencies'] = additional_jar_dependencies
        general_configuration["dataset_name"] = self.resolve_dataset_name(entity_base_pipeline, **kwargs)
        # will be place into root of configuration
        return None, general_configuration

    def _resolve_additional_jar_dependencies(self, job_steps: [EntityPipelineSteps]):
        """
        Check if any of the job contains any mandatory job dependencies

        @param job_steps:
        """
        additional_jar_dependencies = []
        for job_step in job_steps:
            step_job_jar_dependencies = job_step.definition.get(
                "additionalJarDependencies", []) or self._get_user_specified_additional_jar_dependencies(
                job_step.definition.get("attributes", []))
            attributes_jar_dependencies = [
                attr.get("value", []) for attr in job_step.definition.get("attributes", []) if
                attr.get("attributeName") == "additional_jar_dependencies"
            ]
            for step_job_dependency in step_job_jar_dependencies:
                additional_jar_dependencies.append({
                    "group_id": step_job_dependency["groupId"],
                    "artifact_id": step_job_dependency["artifactId"],
                    "version": step_job_dependency["version"]
                })
            for attr_jar_dep_value in attributes_jar_dependencies:
                for attr_jar_dep_value_single_value in attr_jar_dep_value:
                    jar_dependency = {}
                    for item_value in attr_jar_dep_value_single_value["attributes"]:
                        if item_value["attributeName"] == "group_id":
                            jar_dependency["group_id"] = item_value["value"]
                        if item_value["attributeName"] == "artifact_id":
                            jar_dependency["artifact_id"] = item_value["value"]
                        if item_value["attributeName"] == "version":
                            jar_dependency["version"] = item_value["value"]
                    additional_jar_dependencies.append(jar_dependency)
        return additional_jar_dependencies

    def _get_user_specified_additional_jar_dependencies(self, model_attrs):
        """
        Get the user specified additional jar dependencies

        @param model_attrs:
        @return:
        """
        attribute_value = []
        for attr in model_attrs:
            if attr['attributeName'] == 'additionalJarDependencies':
                attribute_value = self._get_attr_value_from_dynamic_attribute(model_attr=attr)
                return attribute_value
        return attribute_value
