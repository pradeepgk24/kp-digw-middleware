from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline


class PipelineCatalogConfigResolver(ConfigPartResolver):
    """
    Resolve catalogs related configuration
    """

    def resolve_model_to_config(self, entity_pipeline: EntityPipeline, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """

        config_part = {}
        if entity_pipeline.catalogs:
            catalogs_config = entity_pipeline.catalogs.to_json_dict()
            unity_catalog_config = catalogs_config.get("unityCatalog")
            if unity_catalog_config:
                config_part["unity_catalog"] = catalogs_config["unityCatalog"]
                # in case of unity catalog, glue databases needs to be empty
                config_part["glue_databases"] = {}

            glue_databases_config = catalogs_config.get("glueDatabases")
            if glue_databases_config:
                config_part["glue_databases"] = catalogs_config["glueDatabases"]
        # will be place into global configuration
        return None, config_part
