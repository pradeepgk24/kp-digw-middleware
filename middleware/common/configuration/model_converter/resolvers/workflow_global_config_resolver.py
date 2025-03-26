from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_workflow import EntityWorkflow
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from middleware.common.helpers.datetime_formater import from_datetime_to_standard_no_timezone_str


class WorkflowGlobalConfigResolver(ConfigPartResolver):
    """
    Resolve general root configuration
    """

    def resolve_model_to_config(self, entity_workflow: EntityWorkflow, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """
        general_configuration = {}
        if "{{dataset_name}}" not in entity_workflow.resource_prefix:
            entity_workflow.set_resource_prefix(entity_workflow.resource_prefix + "_{{dataset_name}}")
        platform_configuration = kwargs['platform_configuration']
        self.map_object_attr_to_dict_bulk(
            entity_workflow,
            general_configuration,
            [
                (["resource_prefix"], ["resource_prefix"], None),
                (["schedule"], ["schedule"], None),
                (["initial_load_start_date"], ["initial_load", "start_date"], None, True,
                 from_datetime_to_standard_no_timezone_str),
                (["lower_bound_start_date"], ["initial_load", "lower_bound"], None, True,
                 from_datetime_to_standard_no_timezone_str),
                (["enable_deffer_operators"], ["defer"], False)
            ]
        )
        airflow_options = entity_workflow.advanced_options.entity_airflow_options
        general_configuration["airflow_connection"] = airflow_options.aws_connection_name if \
            airflow_options.aws_connection_name else \
            platform_configuration[ProjectAccountTypesEnum.airflow].account_details.get("awsConnectionName",
                                                                                        "aws_srv_ingest_user_{{env}}")
        airflow_tags = airflow_options.airflow_tags if airflow_options.airflow_tags else \
            platform_configuration[ProjectAccountTypesEnum.airflow].account_details.get("tags")
        if airflow_tags:
            general_configuration["airflow_tags"] = airflow_tags
        if entity_workflow.initial_load_start_date is not None:
            general_configuration["catchup"] = True
        general_configuration["dataset_name"] = entity_workflow.workflow_name
        general_configuration["platform"] = "airflow"
        general_configuration["region"] = kwargs.get('region', 'us-east-1')
        # will be place into root of configuration
        return None, general_configuration
