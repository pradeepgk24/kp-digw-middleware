from middleware.common.configuration.model_converter.base_model_to_configuration_converter import \
    BaseModelToConfigurationConverter
from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.configuration.model_converter.resolvers.pipeline_airflow_config_resolver import \
    PipelineAirflowConfigResolver
from middleware.common.configuration.model_converter.resolvers.pipeline_aws_account_config_resolver import \
    PipelineAwsAccountConfigResolver
from middleware.common.configuration.model_converter.resolvers.pipeline_catalogs_config_resolver import \
    PipelineCatalogConfigResolver
from middleware.common.configuration.model_converter.resolvers.pipeline_databricks_account_config_resolver import \
    PipelineDatabricksAccountConfigResolver
from middleware.common.configuration.model_converter.resolvers.pipeline_global_config_resolver import \
    PipelineGlobalConfigResolver
from middleware.common.configuration.model_converter.resolvers.pipeline_global_databricks_config_resolver import \
    PipelineGlobalDatabricksConfigResolver
from middleware.common.configuration.model_converter.resolvers.pipeline_global_glue_config_resolver import \
    PipelineGlobalGlueConfigResolver

from middleware.common.configuration.model_converter.resolvers.object_airflow_notifications_resolver import \
    ObjectAirflowNotificationsResolver
from middleware.common.configuration.model_converter.resolvers.pipeline_jobs_config_resolver import \
    PipelineJobsConfigResolver
from middleware.common.configuration.model_converter.resolvers.pipeline_tables_config_resolver import \
    PipelineTablesConfigResolver
from middleware.common.configuration.model_converter.resolvers.pipeline_template_global_config_resolver import \
    PipelineTemplateGlobalConfigResolver
from middleware.common.entity_management.secrets_management import SecretsManagement
from middleware.common.configuration.model_converter.resolvers.pipeline_difw_notifications_resolver import \
    PipelineDifwNotificationsResolver


class PipelineModelToConfigurationConverter(BaseModelToConfigurationConverter):
    """
    Model converter for pipeline and pipeline templates
    """

    def __init__(self, logger, secrets_management: SecretsManagement, resolve_as_template):
        super().__init__(logger, secrets_management)
        self.resolve_as_template = resolve_as_template

    def get_mandatory_input_parameters(self) -> [str]:
        return [
            "platform_configuration",
            "pipeline_name",
            "region"
        ]

    def get_config_part_converters(self) -> [ConfigPartResolver.__class__]:
        converters = [
            PipelineGlobalDatabricksConfigResolver,
            PipelineGlobalGlueConfigResolver,
            ObjectAirflowNotificationsResolver,
            PipelineAwsAccountConfigResolver,
            PipelineDatabricksAccountConfigResolver,
            PipelineAirflowConfigResolver,
            PipelineCatalogConfigResolver,
            PipelineDifwNotificationsResolver,
            PipelineJobsConfigResolver,
        ]
        if not self.resolve_as_template:
            converters.append(PipelineGlobalConfigResolver)
            converters.append(PipelineTablesConfigResolver)
        else:
            converters.append(PipelineTemplateGlobalConfigResolver)
        return converters