from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline


class PipelineGlobalDatabricksConfigResolver(ConfigPartResolver):
    """
    Resolve root configurations related with DBX platform
    """

    def resolve_model_to_config(self, entity_pipeline: EntityPipeline, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """
        config_part = {}
        if entity_pipeline.platform == "databricks":
            # resolve ACLs if there are present any, merge all possible acls into one list
            existing_acls = entity_pipeline.advanced_options.entity_dbx_options.dbx_acl + \
                            entity_pipeline.advanced_options.entity_dbx_options.dbx_acl_user + \
                            entity_pipeline.advanced_options.entity_dbx_options.dbx_acl_group
            # if the list of acls is non-empty go through them and saved them under access_control_list in config
            if existing_acls:
                config_acls = []
                for dbx_acl in existing_acls:
                    config_acl = {
                        "permission_level": dbx_acl["Permission"]
                    }
                    if "UserGroup" in dbx_acl:
                        config_acl["group_name"] = dbx_acl["UserGroup"]
                    if "UserName" in dbx_acl:
                        config_acl["user_name"] = dbx_acl["UserName"]
                    config_acls.append(config_acl)
                if config_acls:
                    config_part['access_control_list'] = config_acls
        return None, config_part
