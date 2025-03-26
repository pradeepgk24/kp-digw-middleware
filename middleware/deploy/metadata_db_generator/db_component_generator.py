
# coding: utf-8
"""
Copyright © 2023 Merck Sharp & Dohme Corp., a subsidiary of Merck & Co., Inc.
All rights reserved.
"""
import logging
import os
import sys
from abc import abstractmethod

import boto3
import yaml

from middleware.common.secrets.secrets_manager import SecretsManager


# pylint: disable=too-many-instance-attributes
class DBComponentGenerator:
    """
    Generator for Database components
    """
    DATABASE_NAME = "DIFW"

    def __init__(self, args):
        self._setup_logger()
        self.rds_client = boto3.client('rds', region_name=args.region)
        self.args = args
        self.project_configuration = self._load_project_configuration(args.environment, args.project_settings_file)
        self.metadb_configuration = self.project_configuration.get("metadatabase")
        self.resources_meta_db_generator_path = \
            f"{args.workspace}{os.sep}middleware{os.sep}deploy{os.sep}metadata_db_generator{os.sep}resources"
        self.sql_script_path = f"{self.resources_meta_db_generator_path}{os.sep}sql_scripts"
        self.step_definitions_path = f"{self.resources_meta_db_generator_path}{os.sep}steps_definitions"
        self.permission_actions_path = f"{self.resources_meta_db_generator_path}{os.sep}permission_action_types"
        self.global_permission_path = f"{self.resources_meta_db_generator_path}{os.sep}global_permissions"
        self.enumerator_categories_path = f"{self.resources_meta_db_generator_path}{os.sep}enumerator_categories"
        self.api_aws_region = self.project_configuration.get("apiSpecs", {}).get("awsRegion", "us-east-1")
        self.api_sm_client = SecretsManager(region_name=self.api_aws_region)

    @staticmethod
    def _load_project_configuration(environment, project_settings_file):
        """
        Load project configuration
        :return: configuration
        """
        with open(project_settings_file) as config_file_stream:
            project_configuration = yaml.safe_load(config_file_stream)
        for project_env in project_configuration.get("environments", []):
            if project_env["name"].lower() == environment.lower():
                project_env["envName"] = environment.lower()
                project_env['displayName'] = project_configuration.get("displayName", "")
                project_env['description'] = project_configuration.get("description", "")
                project_env['projectSpecificRepo'] = project_configuration.get("projectSpecificRepo", [])
                return project_env
        return {}

    def _setup_logger(self):
        """
        Setup new logger
        :return:
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                            format='%(asctime)-11s [%(levelname)s] [%(name)s] %(message)s')

    def get_database_info(self, db_instance_identifier):
        """
        Get database info

        :param db_instance_identifier:
        :return:
        """
        try:
            database_info = self.rds_client.describe_db_instances(
                DBInstanceIdentifier=db_instance_identifier,
            )
            return database_info['DBInstances'][0]
        except self.rds_client.exceptions.DBInstanceNotFoundFault:
            self.logger.warning(f"Db with identifier {db_instance_identifier} does not exist")
            return None

    def get_database_status(self, db_instance_identifier):
        """
        Get status of DB instance

        :param db_instance_identifier:
        :return:
        """
        try:
            database_info = self.rds_client.describe_db_instances(
                DBInstanceIdentifier=db_instance_identifier,
            )
            return database_info['DBInstances'][0]['DBInstanceStatus']
        except self.rds_client.exceptions.DBInstanceNotFoundFault:
            self.logger.warning(f"Db with identifier {db_instance_identifier} does not exist")
            return None

    @abstractmethod
    def generate(self, args):
        """
        Abstract method for generatoion of DB component
        """

