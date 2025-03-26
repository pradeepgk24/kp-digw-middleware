from middleware.common.configuration.model_converter.base_model_to_configuration_converter import \
    BaseModelToConfigurationConverter
from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.configuration.model_converter.resolvers.pipeline_runtime_jobs_config_resolver import \
    PipelineRuntimeJobsConfigResolver
from middleware.common.entity_management.secrets_management import SecretsManagement


class PipelineRuntimeModelToConfigurationConverter(BaseModelToConfigurationConverter):
    """
    Model converter for pipeline to be used only when running start pipeline with runtime parameters as it only
    has one resolver part - PipelineRuntimeJobsConfigResolver, and mandatory input params are not having
    platform_configuration.
    As the runtime params are applicable only to pipelines, there is no need to handle the template logic here
    """

    # pylint: disable=useless-parent-delegation
    def __init__(self, logger, secrets_management: SecretsManagement):
        super().__init__(logger, secrets_management)

    def get_mandatory_input_parameters(self) -> [str]:
        """
        @rtype list of strings
        @return list of mandatory input parameters to be validated
        """
        return [
            "pipeline_name",
            "region"
        ]

    def get_config_part_converters(self) -> [ConfigPartResolver.__class__]:
        """
        @rtype list of classes
        @return list containing class of PipelineRuntimeJobsConfigResolver
        """
        converters = [
            PipelineRuntimeJobsConfigResolver
        ]
        return converters
