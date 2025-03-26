# coding: utf-8
"""
Copyright © 2021 Merck Sharp & Dohme Corp., a subsidiary of Merck & Co., Inc.
All rights reserved.
"""
from argparse import ArgumentParser

import json
import logging
import sys
import yaml


class TerraformAPIVariableGenerator(object):
    def __init__(self):
        self.args = None
        self.aws_region = None
        self.resource_bucket = None
        self._setup_logger()

    def get_project_settings(self):
        """
        Return project settings for the environment

        @return: Project settings for the project
        """
        with open(self.args.project_settings_file) as config_file_stream:
            project_configuration = yaml.safe_load(config_file_stream)
        for project_env in project_configuration.get("environments", []):
            if project_env["name"].lower() == self.args.environment.lower():
                project_env["envName"] = self.args.environment.lower()
                project_env['displayName'] = project_configuration.get("displayName", "")
                project_env['description'] = project_configuration.get("description", "")
                project_env['projectSpecificRepo'] = project_configuration.get("projectSpecificRepo", [])
                return project_env
        return {}

    def create_tf_var_config(self):
        """
            Create deployment.tfvars file needed for terraform deployment
        """
        project_settings = self.get_project_settings()

        try:
            api_specs = project_settings.get('apiSpecs')
            metadb_specs = project_settings.get('metadatabase')
            self.resource_bucket = api_specs.get('s3Bucket')

            lambda_vpc_subnet_ids = api_specs.get('awslambdaSubnetIDs')
            lambda_env = self.args.environment
            supported_envs = self.args.all_envs
            lambda_msd_internal_api_secret = api_specs.get('msdInternalApiSecretName')
            lambda_msd_internal_api_sg_prefix = api_specs.get('msdInternalApiSgPrefix')
            lambda_msd_internal_api_url = api_specs.get('msdInternalApiURL')
            metadata_connection = metadb_specs.get('dbSecretManagerCredentialStorage')
            stage_name = self.args.stage_name
            api_name = self.args.api_name
            framework_version = self.args.framework_version
            middleware_version = self.args.middleware_version
            self.aws_region = api_specs.get('awsRegion')
            lambda_prefix = self.args.lambda_prefix
            bucket_name = self.resource_bucket
            dbx_bucket_name = api_specs.get('computing', {}).get('databricksAccount', {}).get('awsS3ResourcesBucket')
            private_vpce_ids = api_specs.get('awsVpcEndpointIds')
            redis_secret = api_specs.get('redisSecretName')
            ecr_repo = api_specs.get('ecrRepo')
            ecr_registry = api_specs.get('ecrRegistry')
            lambda_role_arn = api_specs.get('awslambdaRole')
            lambda_vpc_security_group_ids = api_specs.get('awslambdaVPCSecurityGrp')

        except:
            self.logger.error('The project settings file is not configured properly for ECS deployment')
            raise Exception

        with open(f"{self.args.output_path_folder}/deployment.tfvars", 'w+') as tf_var_file:
            lambda_vpc_subnet_ids = json.dumps(lambda_vpc_subnet_ids)
            tf_var_file.write(f'lambda_vpc_subnet_ids={lambda_vpc_subnet_ids}\n')
            tf_var_file.write(f'lambda_env="{lambda_env}"\n')
            tf_var_file.write(f'supported_envs="{supported_envs}"\n')
            tf_var_file.write(f'lambda_msd_internal_api_secret="{lambda_msd_internal_api_secret}"\n')
            tf_var_file.write(f'lambda_msd_internal_api_sg_prefix="{lambda_msd_internal_api_sg_prefix}"\n')
            tf_var_file.write(f'lambda_msd_internal_api_url="{lambda_msd_internal_api_url}"\n')
            tf_var_file.write(f'metadata_connection="{metadata_connection}"\n')
            tf_var_file.write(f'stage_name="{stage_name}"\n')
            tf_var_file.write(f'api_name="{api_name}"\n')
            tf_var_file.write(f'framework_version="{framework_version}"\n')
            tf_var_file.write(f'middleware_version="{middleware_version}"\n')
            tf_var_file.write(f'aws_region="{self.aws_region}"\n')
            tf_var_file.write(f'lambda_prefix="{lambda_prefix}"\n')
            tf_var_file.write(f'bucket_name="{bucket_name}"\n')
            tf_var_file.write(f'dbx_bucket_name="{dbx_bucket_name}"\n')
            private_vpce_ids = json.dumps(private_vpce_ids)
            tf_var_file.write(f'private_vpce_ids={private_vpce_ids}\n')
            tf_var_file.write(f'redis_secret="{redis_secret}"\n')
            tf_var_file.write(f'ecr_repo="{ecr_repo}"\n')
            tf_var_file.write(f'ecr_registry="{ecr_registry}"\n')
            tf_var_file.write(f'lambda_role_arn="{lambda_role_arn}"\n')
            lambda_vpc_security_group_ids = json.dumps(lambda_vpc_security_group_ids)
            tf_var_file.write(f'lambda_vpc_security_group_ids={lambda_vpc_security_group_ids}\n')

        self.logger.info(f"File {self.args.output_path_folder}/deployment.tfvars was created successfully")

    def create_backend_config(self):
        """
        Create backend.cfg file needed for terraform deployment
        This is used for the region only for now, but might be extended for other purposes.
        """
        with open(f"{self.args.output_path_folder}/backend_api.cfg", 'w+') as cfg_file:
            cfg_file.write(f'region="{self.aws_region}"\n')
            cfg_file.write(f'bucket="{self.resource_bucket}"\n')
            cfg_file.write(f'key="terraform/state/{self.args.environment}/{self.args.api_name}/'
                           f'{self.args.middleware_version}/API/terraform.tfstate"\n')
        self.logger.info(f"File {self.args.output_path_folder}/backend_api.cfg was created successfully")

    def _setup_logger(self):
        """
        Setup new logger
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                            format='%(asctime)-11s [%(levelname)s] [%(name)s] %(message)s')

    @staticmethod
    def parse_args(parser):
        """
        Parse the arguments

        @param parser: argument parser
        @return: parsed arguments
        """
        parser.add_argument('-of', '--output_path_folder', required=True, type=str, help='Path to the output folder')
        parser.add_argument('-pr', '--project_name', required=True, type=str, help='Project name')
        parser.add_argument('-env', '--environment', required=True, type=str, help='Environment')
        parser.add_argument('-mv', '--middleware_version', required=True, type=str, help='Middleware version')
        parser.add_argument('-fwv', '--framework_version', required=True, type=str, help='Framework version')
        parser.add_argument('-ae', '--all_envs', required=True, type=str, help='Al environments supported')
        parser.add_argument('-sn', '--stage_name', required=True, type=str, help='Stage name')
        parser.add_argument('-an', '--api_name', required=True, type=str, help='Api name')
        parser.add_argument('-lp', '--lambda_prefix', required=True, type=str, help='Lambda prefix')
        parser.add_argument('-psf', '--project_settings_file', required=True, help='Path to project settings file')

        return parser.parse_args()

    def generate(self):
        self.args = self.parse_args(ArgumentParser())
        self.create_tf_var_config()
        self.create_backend_config()


if __name__ == "__main__":
    generator = TerraformAPIVariableGenerator()
    generator.generate()
