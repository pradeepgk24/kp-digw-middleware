from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline


class PipelineAirflowConfigResolver(ConfigPartResolver):
    """
    Resolve airflow related configuration
    """

    def resolve_model_to_config(self, entity_pipeline: EntityPipeline, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """
        config_part = {}
        self.map_object_attr_to_dict_bulk(
            entity_pipeline,
            config_part,
            [
                (["advanced_options", "entity_airflow_options", "dag_instance_parameters"],
                 ["dag_instance_parameters"]),
                (["advanced_options", "entity_airflow_options", "dag_concurrency"], ["dag_concurrency"]),
                (["advanced_options", "entity_airflow_options", "airflow_pool_name"], ["airflow_pool"]),
                (["advanced_options", "entity_airflow_options", "airflow_pool_slots"], ["airflow_pool_slots"]),
                (["advanced_options", "entity_airflow_options", "aws_connection_name"], ["airflow_connection"]),
                (["advanced_options", "entity_airflow_options", "airflow_tags"], ["airflow_tags"]),
            ]
        )
        # will be place into global configuration
        return None, config_part