from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline


class PipelineGlobalGlueConfigResolver(ConfigPartResolver):
    """
    Resolve root configurations related with AWS Glue platform
    """

    def resolve_model_to_config(self, entity_pipeline: EntityPipeline, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """
        config_part = {}
        if entity_pipeline.platform == "glue":
            self.map_object_attr_to_dict_bulk(
                entity_pipeline,
                config_part,
                [
                    (["advanced_options", "entity_glue_options", "number_of_workers"], ["num_workers"]),
                    (["advanced_options", "entity_glue_options", "worker_type"], ["worker_type"]),
                    (["advanced_options", "entity_glue_options", "autoscaling"], ["enable_auto_scaling"]),
                    (["advanced_options", "entity_glue_options", "spark_configuration"], ["spark_config"]),
                    (["advanced_options", "entity_glue_options", "java_system_properties"], ["system_properties"])
                ]
            )
            spark_sql_settings = self._create_sql_spark_configuration_section(
                entity_pipeline.advanced_options.entity_glue_options.spark_sql_configuration
            )
            if spark_sql_settings:
                config_part["spark_sql_settings"] = spark_sql_settings
            # will be place into root of configuration
        return None, config_part

