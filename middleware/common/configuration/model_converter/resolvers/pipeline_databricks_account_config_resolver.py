import yaml

from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from common.secrets.secrets import SecretValue


class PipelineDatabricksAccountConfigResolver(ConfigPartResolver):
    """
    Resolve databricks account configuration
    """

    def resolve_model_to_config(self, entity_pipeline: EntityPipeline, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """

        platform_configuration = kwargs['platform_configuration']
        config_part = {}
        if entity_pipeline.platform == "databricks":
            account_type = ProjectAccountTypesEnum.databricks
            account_details = platform_configuration[account_type].account_details
            self.map_object_attr_to_dict_bulk(
                entity_pipeline,
                config_part,
                [
                    (["advanced_options", "entity_dbx_options", "all_purpose_cluster_id"], ["existing_cluster_id"]),
                    (["advanced_options", "entity_dbx_options", "all_purpose_cluster_name"],
                     ["existing_cluster_name"]),
                    (["advanced_options", "entity_dbx_options", "all_purpose_cluster_validate"],
                     ["validate_all_purpose_cluster"])
                ]
            )
            cluster_options = entity_pipeline.advanced_options.entity_dbx_options.job_cluster_options
            if isinstance(cluster_options, dict):
                config_part["cluster_options"] = cluster_options
            # if cluster options were passed in as string, it should be copied yaml config part
            # for this reason we use yaml.safe_load to save it as dictionary
            elif isinstance(cluster_options, str):
                config_part["cluster_options"] = yaml.safe_load(cluster_options)
            dbx_pipeline_settings = entity_pipeline.advanced_options.entity_dbx_options
            config_part["databricks_instance_url"] = account_details.get("databricksInstanceUrl")
            secret_name = dbx_pipeline_settings.security_api_token_secret_name if \
                dbx_pipeline_settings.security_api_token_secret_name else \
                account_details["securityApiToken"]["secretName"]
            secret_key = dbx_pipeline_settings.security_api_token_secret_key if \
                dbx_pipeline_settings.security_api_token_secret_name else \
                account_details["securityApiToken"]["secretKey"]
            config_part["security_api_token"] = SecretValue(
                self._resolve_secret_manager_name({"secretName": secret_name}), secret_key)
        # will be place into databricks_account key under configuration
        return "databricks_account", config_part