from middleware.common.configuration.model_converter.resolvers.base_pipeline_global_config_resolver import \
    BasePipelineGlobalConfigResolver
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline


class PipelineGlobalConfigResolver(BasePipelineGlobalConfigResolver):
    """
    Resolve pipeline global configuration
    """

    def resolve_dataset_name(self, entity_pipeline: EntityPipeline, **kwargs):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """
        return entity_pipeline.pipeline_name