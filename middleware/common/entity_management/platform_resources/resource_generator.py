import os
import sys

from common.helpers.s3_utils import S3Utils
from deploy.generators.platform_resources_generator.platform_resources_generator_controller import \
    invoke_generator as resource_generator
from deploy.generators.platform_airflow_dag_generator.platform_airflow_dag_controller import \
    invoke_generator as dag_generator
from deploy.generators.validation.config_validator import _main
from middleware.common.entity_management.secrets_management import SecretsManagement
from middleware.common.helpers.airflow_ec2_utils import AirflowEC2Utils
from middleware.common.helpers.airflow_eks_utils import AirflowEKSUtils


class ResourceGenerator:
    """
    Class wrap all methods for running of core generators
    """

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-instance-attributes
    def __init__(self, logger, airflow_instance_settings: dict,
                 secret_management: SecretsManagement, aws_region: str = "us-east-1",
                 aws_access_key: str = None, aws_secret_key: str = None, aws_session_token: str = None):
        self.logger = logger
        self.airflow_instance_settings = airflow_instance_settings
        self.aws_region = aws_region
        self.s3_utils = S3Utils(logger=self.logger, region_name=aws_region)
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_session_token = aws_session_token
        self.secret_management = secret_management

    def run_platform_generator(self, dataset_name, framework_version, source_dir, **optional_fields):
        """
        Run platform generator in order to create pipeline resources

        :param dataset_name:
        :param framework_version:
        :param source_dir: base directory for dataset definition
        :param optional_fields:
        :return:
        """
        sys.argv[1:] = ['--output-path-folder', f'{source_dir}{os.path.sep}{dataset_name}{os.path.sep}conf',
                        '--workspace-path', source_dir,
                        '--dataset-path-folder', f'{source_dir}{os.path.sep}{dataset_name}',
                        '--environment', optional_fields.get('env', 'dev'), '--all_environments',
                        optional_fields.get('supported_envs', 'poc,mvp,dev,tst,test,sit,uat,prd,prod'),
                        '--aws_access_key', self.aws_access_key,
                        '--aws_secret_key', self.aws_secret_key,
                        '--aws_session_key', self.aws_session_token,
                        '--clean-deploy', 'false',
                        '--pipeline-version', optional_fields.get('pipeline_version', "1.0.0-API"),
                        '--framework-version', framework_version]
        self.logger.info("Invoking platform generator with input as %s", sys.argv[1:])
        return resource_generator()

    def create_and_deploy_airflow_dag(self, pipeline_name, framework_version, tmpdir, airflow_info, optional_fields):
        """
        Create and deploy DAG
        param: pipeline_name
        param: framework_version
        param: tmpdir
        param: airflow_info
        param: optional_fields

        :return: pipeline_definitions
        """
        pipeline_definitions = self._run_dag_generator(pipeline_name, framework_version, tmpdir, airflow_info,
                                                       **optional_fields)
        if self.airflow_instance_settings.get("ec2Based"):
            AirflowEC2Utils(self.airflow_instance_settings, secret_management=self.secret_management,
                            logger=self.logger, region_name=self.aws_region). \
                upload_dag(pipeline_name, tmpdir, **optional_fields)
        elif self.airflow_instance_settings.get("eksBased"):
            AirflowEKSUtils(airflow_instance_settings=self.airflow_instance_settings,
                            secret_management=self.secret_management,
                            logger=self.logger, workspace=tmpdir). \
                upload_to_eks_repo(pipeline_name, **optional_fields)
        else:
            raise Exception("Airflow settings for EKS or EC2 is missing")

        return pipeline_definitions

    def _run_dag_generator(self, dataset_name, framework_version, source_dir, airflow_info, **optional_fields):
        """
        Run DAG generator

        :param dataset_name:
        :param framework_version:
        :param source_dir: base directory for dataset definition
        :param logger:
        :param optional_fields:
        :param airflow_info:
        :return:
        """
        name_of_secret = airflow_info.get("apiUserPassword").get("secretName")
        secrets = self.secret_management.get_secret(secret_name=name_of_secret, get_values=True, check_permission=False)
        airflow_host = airflow_info.get("airflowHost").removeprefix("https://")
        sys.argv[1:] = ['--output-path',
                        f"{source_dir}/{dataset_name}_{optional_fields.get('env', 'dev')}_dag_out_dir",
                        '--workspace-path', f'{source_dir}', '--dataset-path-folder', f'{source_dir}/{dataset_name}',
                        '--environment', optional_fields.get('env', 'dev'), '--all_environments',
                        optional_fields.get('supported_envs', 'poc,mvp,dev,tst,test,sit,uat,prd,prod'),
                        '--clean-deploy', 'true', '--pipeline-version',
                        optional_fields.get('pipeline_version', "1.0.0-API"), '--framework-version',
                        framework_version,
                        '--airflow-user', f"{airflow_info.get('apiUsername')}",
                        '--airflow-user-password',
                        f"{secrets.items.get(airflow_info.get('apiUserPassword').get('secretKey'))}",
                        '--airflow-host', airflow_host,
                        '--project-name', optional_fields.get("project_name", "difw")]
        # masking airflow password key not to be logged
        log_message = sys.argv[1:]
        log_message[-3] = "*****"
        self.logger.info("Invoking dag generator with input as %s", log_message)
        dataset_definitions = dag_generator()
        self.logger.info(dataset_definitions)
        return dataset_definitions

    def _run_config_validator(self, source_dir, **optional_fields):
        """
        Run config validator

        :param source_dir: base directory for dataset definition
        :param logger:
        :param optional_fields:
        :return:
        """
        sys.argv[1:] = ['--workspace-path', f'{source_dir}',
                        '--dataset-path-folder', f'{source_dir}',
                        '--validate-pom', 'false',
                        '--environment', optional_fields.get('env', 'dev'), '--all_environments',
                        optional_fields.get('supported_envs', 'dev')]
        self.logger.info("Validating pipeline definition with input as %s", sys.argv[1:])
        _main(sys.argv)
