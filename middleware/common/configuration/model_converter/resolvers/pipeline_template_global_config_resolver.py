from middleware.common.configuration.model_converter.resolvers.base_pipeline_global_config_resolver import \
    BasePipelineGlobalConfigResolver
from middleware.common.entity_management.entities.entity_pipeline_template import EntityPipelineTemplate


class PipelineTemplateGlobalConfigResolver(BasePipelineGlobalConfigResolver):
    """
    Resolve general root configuration of pipeline templates
    """

    def resolve_dataset_name(self, entity_pipeline_template: EntityPipelineTemplate, **kwargs):
        return entity_pipeline_template.pipeline_template_name