from middleware.common.configuration.model_converter.base_model_to_configuration_converter import \
    BaseModelToConfigurationConverter
from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.configuration.model_converter.resolvers.object_airflow_notifications_resolver import \
    ObjectAirflowNotificationsResolver

from middleware.common.configuration.model_converter.resolvers.workflow_airflow_config_resolver import \
    WorkflowAirflowConfigResolver
from middleware.common.configuration.model_converter.resolvers.workflow_global_config_resolver import \
    WorkflowGlobalConfigResolver
from middleware.common.configuration.model_converter.resolvers.workflow_groups_config_resolver import \
    WorkflowGroupsConfigResolver
from middleware.common.entity_management.secrets_management import SecretsManagement


class WorkflowModelToConfigurationConverter(BaseModelToConfigurationConverter):
    """
    Model converter for pipeline and pipeline templates
    """

    def __init__(self, logger, secrets_management: SecretsManagement):
        super().__init__(logger, secrets_management)
        self.resolvers = None

    def get_mandatory_input_parameters(self) -> [str]:
        return [
            "platform_configuration",
            "workflow_name",
            "region"
        ]

    def get_config_part_converters(self) -> [ConfigPartResolver.__class__]:
        converters = [
            WorkflowGlobalConfigResolver,
            ObjectAirflowNotificationsResolver,
            WorkflowAirflowConfigResolver,
            WorkflowGroupsConfigResolver
        ]
        return converters
