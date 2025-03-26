from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum


class PipelineAwsAccountConfigResolver(ConfigPartResolver):
    """
    Resolve aws account configuration
    """

    def resolve_model_to_config(self, entity_pipeline: EntityPipeline, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """

        platform_configuration = kwargs['platform_configuration']
        config_part = {}

        if entity_pipeline.platform == "glue":
            aws_glue_pipeline_detail = entity_pipeline.advanced_options.entity_glue_options
            account_details = platform_configuration[ProjectAccountTypesEnum.aws].account_details
            config_part["glue_role"] = account_details.get("glueRole")
            config_part["availability_zone"] = account_details.get("availabilityZone")
            config_part["subnet_id"] = aws_glue_pipeline_detail.subnet_id if aws_glue_pipeline_detail.subnet_id \
                else account_details.get("subnetId")
            config_part["resources_bucket"] = aws_glue_pipeline_detail.resources_bucket \
                if aws_glue_pipeline_detail.resources_bucket else account_details.get("resourcesBucket")
            config_part["data_bucket"] = aws_glue_pipeline_detail.data_bucket if aws_glue_pipeline_detail.data_bucket \
                else account_details.get("dataBucket")
            config_part["log_bucket"] = account_details.get("logBucket")
            config_part["security_groups"] = aws_glue_pipeline_detail.security_groups \
                if aws_glue_pipeline_detail.security_groups else account_details.get("securityGroups")
        else:
            # in case of DBX take buckets from DBX account details
            account_details = platform_configuration[ProjectAccountTypesEnum.databricks].account_details
            dbx_account_details = entity_pipeline.advanced_options.entity_dbx_options
            config_part["resources_bucket"] = dbx_account_details.resources_bucket \
                if dbx_account_details.resources_bucket \
                else account_details.get("awsS3ResourcesBucket")
            config_part["data_bucket"] = dbx_account_details.data_bucket \
                if dbx_account_details.data_bucket \
                else account_details.get("awsS3DataBucket")
            config_part["log_bucket"] = account_details.get("awsS3LogBucket")

        # at the end update custom tags
        custom_tags = entity_pipeline.tags
        custom_tags["FrameworkVersion"] = "{{framework_version}}"
        custom_tags["PipelineVersion"] = "{{pipeline_version}}"
        config_part['custom_tags'] = custom_tags

        # will be place into aws_account key under configuration
        return "aws_account", config_part
