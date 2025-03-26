import json
import os
import tempfile
import uuid
from os import environ
import concurrent.futures
import boto3
import botocore
from middleware.common.api_clients.airflow.airflow_api_client import AirflowApiClient
from middleware.common.entity_management.definitions_metadata_management import DefinitionsMetadataManagement
from middleware.common.entity_management.entities.entity_project_account_settings import EntityProjectAccountSettings
from middleware.common.entity_management.entities.entity_project_general_settings import EntityProjectGeneralSettings
from middleware.common.entity_management.entity_management import EntityManagement
from middleware.common.entity_management.secrets_management import SecretsManagement
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.security.action_type import ActionType
from middleware.common.helpers.exception import AuthorizationError, NoDataError
from middleware.common.metadatabase.project_settings_metadata_provider import ProjectSettingsMetadataProvider
from middleware.common.entity_management.subjects_management import SubjectManagement
from middleware.common.entity_management.entities.entity_subject import EntitySubject


class ProjectSettingsManagement(EntityManagement):
    """
    Project settings management
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._project_settings_metadata_provider = None
        self._secret_management = None
        self._definition_metadata_management = None
        self._subjects_management = None
        if kwargs.get('project_id'):
            self.project_id = kwargs.get('project_id')

    @property
    def secret_management(self) -> SecretsManagement:
        """
        secret_management property
        """
        if self._secret_management is None:
            self._secret_management = SecretsManagement(
                logger=self.logger, metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
                selected_subjects=self.selected_subjects, project_id=self.project_id)
        return self._secret_management

    @property
    def project_settings_metadata_provider(self) -> ProjectSettingsMetadataProvider:
        """
        project_settings_metadata_provider property
        """
        if self._project_settings_metadata_provider is None:
            self._project_settings_metadata_provider = ProjectSettingsMetadataProvider(self.logger,
                                                                                       self.metadatabase_connection,
                                                                                       self.lambda_secrets_manager)
        return self._project_settings_metadata_provider

    @property
    def definition_metadata_management(self) -> DefinitionsMetadataManagement:
        """
        definition metadata management property
        """
        if self._definition_metadata_management is None:
            self._definition_metadata_management = DefinitionsMetadataManagement(
                logger=self.logger, metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
                selected_subjects=self.selected_subjects)
        return self._definition_metadata_management

    @property
    def subjects_management(self) -> SubjectManagement:
        """
        subjects management property
        """
        if self._subjects_management is None:
            self._subjects_management = SubjectManagement(
                logger=self.logger, metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
                selected_subjects=self.selected_subjects)
        return self._subjects_management

    def _get_secret_manager_of_aws_service_user(self, aws_service_user: dict):
        """
        Get SM and key of AWS account service user

        @param aws_service_user: configuration info of aws_service_user
        @return secret_manager_name, secret_manager_key
        """
        sm_storage = aws_service_user.get("secretKey", {}).get("secretManagerStorage", None)
        if sm_storage:
            sm_parts = sm_storage.split("/")
            secret_manager_name = "/".join(sm_parts[:-1])
            secret_manager_key = sm_parts[-1]  # last item is the key
            return secret_manager_name, secret_manager_key
        return f"{self.project_id}-aws-account-srv-user", "secret-key"

    def get_project_aws_account_access_info(self, project_id: str = None):
        """
        Get access key and secret key of AWS user

        @param project_id: Id of project for which you want to retrieve the account access info. By default, it is
        logon project id
        @return: tuple of aws_access_key, aws_secret_key, aws_session_token
        """
        project_id = self.project_id if project_id is None else project_id
        self.logger.info(f"Going to get aws account access information for project {project_id}")
        aws_project_settings = self.get_project_account_settings(ProjectAccountTypesEnum.aws, check_permission=False,
                                                                 raise_not_found_error=False, project_id=project_id)
        # if there are no project settings then return empty results
        if aws_project_settings is None:
            return None, None, None
        # there can be 3 use cases:
        # 1. No config. Then it will use default aws access based
        # 2. Use assumed role. Then the temporary credentials will be created
        # 3. Use service user. Then take access key and service user from project configuration
        if "awsServiceUser" in aws_project_settings.account_details:
            self.logger.info(f"awsServiceUser {aws_project_settings.account_details['awsServiceUser']} is configure. "
                             f"Going to take access key and secret key of NPA user")
            aws_service_user = aws_project_settings.account_details["awsServiceUser"]
            access_key = aws_service_user["accessKey"]
            secret_manager_name, secret_manager_key = self._get_secret_manager_of_aws_service_user(aws_service_user)
            # check if secret manager exists
            aws_sm = self.secret_management.secret_manager.describe_secrets(secret_manager_name)
            if not aws_sm:
                raise Exception(f"There is no secret manager with name {secret_manager_name}")
            aws_sm_data = self.secret_management.secret_manager.get_secret_string_data(secret_manager_name)
            if not aws_sm_data.get(secret_manager_key):
                raise Exception(
                    f"There is not key in {secret_manager_key} secret manager with name {secret_manager_name}")
            return access_key, aws_sm_data.get(secret_manager_key), None
        if "awsAssumedRole" in aws_project_settings.account_details:
            self.logger.info(f"awsAssumedRole {aws_project_settings.account_details['awsAssumedRole']} is configure. "
                             f"Going to assume role in order to take temporary credentials")
            # assumed role is configured. Take temp credentials"
            return self.assume_role_credentials(aws_project_settings.account_details["awsAssumedRole"],
                                                project_id + '_' +
                                                aws_project_settings.account_details["awsAssumedRole"].split("/")[1])
        return None, None, None

    def assume_role_credentials(self, assume_role_name, role_session_name):
        """
        Retrieve TMP credential for assume role
        @param assume_role_name: name of assume role
        @param role_session_name: name of the principle
        @return: tuple of aws_access_key, aws_secret_key, aws_session_token
        """
        self.logger.info(f"Going to retrieve TMP credentials for role {assume_role_name}")
        # role session name is not mandatory if it is present then we will be passing it to STS client during the call

        sts_response = boto3.client('sts').assume_role(RoleArn=assume_role_name, RoleSessionName=role_session_name)

        sts_credentials = sts_response["Credentials"]
        return sts_credentials["AccessKeyId"], sts_credentials["SecretAccessKey"], sts_credentials["SessionToken"]

    def insert_or_update_project_account_settings(self, project_settings: EntityProjectAccountSettings,
                                                  check_permission: bool = True):
        """
        Update project account settings

        @param project_settings:
        @param check_permission:
        """
        self.logger.info("Going to update project account settings")
        # check if user has permission to such action
        if check_permission and self.auth_validator.validate(
                ActionType.UPDATE_PROJECT_SETTINGS,
                {"settingsType": "account"}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"The user {self.user_isid} does not have access to update project account settings")
        # in case of:
        # 1. aws account
        # 2. service user is part of this update
        # 3. value of accessKey is defined
        # then update awsServiceUser/secretKey value in secret manager. Secret manager name and key is stored under
        # key secretManagerStorage
        if project_settings.account_type == ProjectAccountTypesEnum.aws and \
                "awsServiceUser" in project_settings.account_details:
            self.logger.info("AWS service user is going to be update")
            secret_key_value = project_settings.account_details["awsServiceUser"].get("secretKey", {}).get("value")
            if secret_key_value:
                self.logger.info("AWS service user / secret key  is going to be update")
                secret_manager_name, secret_manager_key = self._get_secret_manager_of_aws_service_user(
                    project_settings.account_details["awsServiceUser"])
                # in case there come empty value from request then fill the default values into secretManagerStorage
                project_settings.account_details["awsServiceUser"]["secretKey"][
                    "secretManagerStorage"] = f"{secret_manager_name}/{secret_manager_key}"
                aws_sm = self.secret_management.secret_manager.describe_secrets(secret_manager_name)
                if not aws_sm:
                    # if SM does not exist then create newone
                    self.logger.info(
                        f"Secret manager with name {secret_manager_name} does not exists. Going to create new one")
                    self.secret_management.secret_manager.create_secrets(
                        secret_manager_name, json.dumps({secret_manager_key: secret_key_value}),
                        description="Secret manager for storing of AWS service user secret key")
                else:
                    # if SM exists then update it
                    self.logger.info(
                        f"Secret manager with name {secret_manager_name} already exists. "
                        f"Going to update value with key new {secret_manager_key}")
                    self.secret_management.secret_manager.update_secret(
                        secret_manager_name, json.dumps({secret_manager_key: secret_key_value}))
                # at the end remove secret key from account details in order to prevent to save it into DB
                del project_settings.account_details["awsServiceUser"]["secretKey"]["value"]
            else:
                self.logger.warning("AWS service user / secret key  is defined, but value is not present")
        # TODO 4318 add check for bucket existence
        # Update project settings in database
        self.project_settings_metadata_provider.insert_or_update_project_account_settings(
            project_settings.to_metadb_object(), self.user_isid)

        # now we can upload common FW packages into newly setup resource bucket
        if project_settings.account_type == ProjectAccountTypesEnum.aws:
            self._upload_common_fw_packages_into_resource_bucket(
                project_settings.account_details.get("resourcesBucket"),
                project_settings.account_details.get('awsRegion', 'us-east-1'))
        if project_settings.account_type == ProjectAccountTypesEnum.databricks:
            self._upload_common_fw_packages_into_resource_bucket(
                project_settings.account_details.get("awsS3ResourcesBucket"),
                project_settings.account_details.get('awsRegion', 'us-east-1'))

    def _upload_common_fw_packages_into_resource_bucket(self, target_bucket, region_name="us-east-1"):
        """
        Take common FW packages and save it into resource bucket

        @param target_bucket: target bucket where the FW packages will be uploaded
        """
        self.logger.info(f"Upload common FW packages into bucket {target_bucket}")
        central_resource_bucket = environ.get('CENTRAL_RESOURCE_BUCKET')
        if central_resource_bucket is not None:
            # check if target bucket contains any sub folders
            bucket_parts = target_bucket.split("/", 1)
            target_bucket = bucket_parts[0]
            sub_folder = ""
            if len(bucket_parts) > 1:
                sub_folder = bucket_parts[1]
            tmp_folder = "/tmp"
            tmp_folder_prefix = uuid.uuid4().hex
            with tempfile.TemporaryDirectory(prefix=tmp_folder_prefix, dir=tmp_folder) as tmpdir:
                all_fw_versions = [fw_version.difw_core_version for fw_version in
                                   self.definition_metadata_management.get_framework_versions()]
                self._copy_packages_between_buckets(
                    central_resource_bucket, target_bucket, tmpdir, all_fw_versions, sub_folder, region_name)

    # pylint: disable=too-many-locals
    # pylint: disable=expression-not-assigned
    # pylint: disable=consider-using-set-comprehension
    # pylint: disable=too-many-arguments
    def _copy_packages_between_buckets(self, central_bucket_name: str, destination_bucket_name: str,
                                       local_dir, all_fw_versions_names: [str], sub_folder="", region_name="us-east-1"):
        """
        Upload all files from bucket with specific prefix into target location

        @param central_bucket_name: central bucket name
        @param destination_bucket_name: target bucket where the FW packages will be uploaded
        @param local_dir: local directory
        @param all_fw_versions_names: list of all enabled FW versions
        @param sub_folder: sub folder
        """
        self.logger.info(f"Going to copy packages from bucket {central_bucket_name}")
        # this is source central bucket therefore do not use any of the access keys from project settings
        # the bucket need to be accessible by lambda role
        central_bucket = boto3.resource('s3').Bucket(central_bucket_name)
        # this is target S3 client into project account therefore we need to use access keys from project settings
        self.refresh_aws_tokens(self)
        s3_client = boto3.client('s3', aws_access_key_id=self.aws_access_key, aws_secret_access_key=self.aws_secret_key,
                                 aws_session_token=self.aws_session_token, region_name=region_name)
        # to prevent the process of the same package we will create 2 structures:
        # 1: dict of packages to download. So if the same package exists multiple time in multiple locations then
        # downloading will happen only once. The dict structure is the following
        #   - key = name of package,
        #   - value = s3 object
        packages_to_download = {}
        # 2: dict of packages to upload. The dict structure is the following
        #   - key = name of destination location,
        #   - value = file in local
        packages_to_upload = {}
        for package_type in ["python", "python_databricks", "python_databricks_submit", "spark", "spark_databricks",
                             "spark_databricks_submit", "external_databricks", "external_databricks_submit"]:
            target_bucket_s3_packages_location = f"data-integration-framework/libs/{package_type}-package"
            if sub_folder:
                target_bucket_s3_packages_location = f"{sub_folder}/{target_bucket_s3_packages_location}"
            # copy to local workspace
            for s3_obj in central_bucket.objects.filter(
                    Prefix=f"data-integration-framework/libs/{package_type}-package"):
                package_name = s3_obj.key.split('/')[-1]
                if any(fw_version in package_name for fw_version in all_fw_versions_names):
                    if package_name not in packages_to_download:
                        packages_to_download[package_name] = s3_obj
                    # upload only files which really needs to be uploaded because it is not exists in target
                    # s3 location and bucket or the size differ (so it was changed)
                    try:
                        target_s3_object = s3_client.head_object(
                            Bucket=destination_bucket_name,
                            Key=f"{target_bucket_s3_packages_location}/{package_name}")
                    except botocore.exceptions.ClientError as client_error:
                        if client_error.response['Error']['Code'] == '404':
                            # if there are not such bucket files, you can continue
                            target_s3_object = None
                        else:
                            raise
                    if not target_s3_object or target_s3_object.get("ContentLength") != s3_obj.size:
                        packages_to_upload[f"{target_bucket_s3_packages_location}/{package_name}"] = \
                            f"{local_dir}{os.path.sep}{package_name}"

        # at this moment we know unique files which we can download and files which need to upload. Let's limit the
        # files to download. We need download only those file which are within the list packages_to_upload
        packages_to_download = \
            {key: packages_to_download[key] for key in
             list(set([target_s3_location.split('/')[-1] for target_s3_location in packages_to_upload]))
             if key in packages_to_download}
        # now process all packages
        # download from S3
        with concurrent.futures.ThreadPoolExecutor() as executor:
            [executor.submit(
                self._download_from_s3,
                central_bucket_name,
                s3_object.key, f"{local_dir}{os.path.sep}{package_name}"
            ) for package_name, s3_object in packages_to_download.items()]

        # upload to s3
        with concurrent.futures.ThreadPoolExecutor() as executor:
            [executor.submit(
                self._upload_to_s3,
                source_file, destination_bucket_name, target_s3_location,
                self.aws_access_key, self.aws_secret_key, self.aws_session_token, region_name
            ) for target_s3_location, source_file in packages_to_upload.items()]

    @staticmethod
    def _download_from_s3(source_bucket: str, obj_key, target_location_in_local: str):
        """
        Download s3 bucket object to local directory

        @param source_bucket: name of source bucket
        @param obj_key: instance represent S3 object
        @param target_location_in_local: folder location in local workspace
        """
        # we are going to copy packages from central location and put it into TMP location
        # in workspace where API is deployed therefore we will not use
        # access settings from project
        central_bucket = boto3.resource('s3').Bucket(source_bucket)
        central_bucket.download_file(obj_key, target_location_in_local)

    @staticmethod
    def _upload_to_s3(source_file_location: str, target_bucket: str, target_s3_location: str,
                      aws_access_key: str, aws_secret_key: str, aws_session_token: str, region_name: str):
        """
        Upload file into S3 location

        @param source_file_location: source file location
        @param target_bucket: name of target bucket
        @param target_s3_location: location in target s3 bucket where file will be uploaded
        @param aws_access_key: Access key to access external account
        @param aws_secret_key: Secret key to access external account
        @param aws_session_token: Session key to access external account
        """
        s3_client = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key,
                                 aws_session_token=aws_session_token, region_name=region_name)
        with open(source_file_location, 'rb') as file_to_upload:
            s3_client.upload_fileobj(file_to_upload, target_bucket, target_s3_location)

    def get_project_account_settings(self, account_type: ProjectAccountTypesEnum,
                                     check_permission: bool = True,
                                     raise_not_found_error: bool = True,
                                     project_id: str = None) -> EntityProjectAccountSettings:
        """
        Get project account settings

        @param raise_not_found_error: raise not found error if there are no project settings
        @param account_type:
        @param check_permission: True = will check if user has permission to read settings, False = check is disabled
        @param project_id
        @return:

        """
        project_id = self.project_id if project_id is None else project_id
        self.logger.info("Going to retrieve project account settings")
        # check if user has permission to such action
        if not check_permission or self.auth_validator.validate(
                ActionType.READ_PROJECT_SETTINGS,
                {"settingsType": "account"}) == PermissionEffectsEnum.allow:
            # Update project settings
            db_project_settings = self.project_settings_metadata_provider.get_project_account_settings(
                project_id=project_id, account_type=account_type)
            if raise_not_found_error and not db_project_settings:
                raise NoDataError(f"There are no project settings for project '{project_id}'")
            return EntityProjectAccountSettings.from_metadb_object(db_project_settings)

        raise AuthorizationError(
            f"The user {self.user_isid} does not have access to read project account settings")
    def get_airflow_api_access(self, project_id: str) -> (str, str, dict):
        """
        Get airflow api access for one particular project

        @param project_id: id of project for which we want to retrieve the credentials
        @return: airflow api username, airflow api password, airflow api settings
        """
        self.logger.info(f"Going to retrieve airflow credentials for project with id = {project_id}")
        airflow_account = self.get_project_account_settings(
            account_type=ProjectAccountTypesEnum.airflow, check_permission=False, raise_not_found_error=False,
            project_id=project_id)
        # if the requested project id is different with current project id
        # then we know that it can be in different AWS account, therefore we need to init new secret manager
        # with credentials from target account
        if project_id != self.project_id:
            # get AWS credentials from project and use it for retrieving of the secret
            access_key, secret_key, session_key = self.get_project_aws_account_access_info(project_id)
            secret_manager = SecretsManagement(
                logger=self.logger, metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
                selected_subjects=self.selected_subjects, project_id=project_id, aws_access_key=access_key,
                aws_secret_key=secret_key, aws_session_token=session_key)
        else:
            secret_manager = self.secret_management
        username = airflow_account.account_details["apiAccess"]["apiUsername"]
        password = secret_manager.get_secret(
            airflow_account.account_details["apiAccess"]["apiUserPassword"]["secretName"], get_values=True,
            check_permission=False
        ).items.get(airflow_account.account_details["apiAccess"]["apiUserPassword"]["secretKey"])
        return username, password, airflow_account.account_details

    def get_shared_project_specific_airflow_api_client(self, project_id: str) -> AirflowApiClient:
        """
        Return project specific airflow client

        @param project_id: instance of project
        @return: airflow api username, airflow api password, airflow api settings
        """
        username, password, airflow_settings = \
            self.get_airflow_api_access(project_id)
        return AirflowApiClient(airflow_settings, logger=self.logger, username=username, password=password)

    def insert_or_update_project_general_settings(self, project_general_settings: EntityProjectGeneralSettings,
                                                  check_permission: bool = True):
        """
        Update project general settings

        @param project_general_settings:
        @param check_permission
        """
        self.logger.info("Going to update project account settings")
        # check if user has permission to such action
        if check_permission and self.auth_validator.validate(ActionType.UPDATE_PROJECT_SETTINGS,
                                                             {"settingsType": "general"}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"The user {self.user_isid} does not have access to update project general settings")
        if self.entity_project:
            self.entity_project.set_description(project_general_settings.description)
            self.entity_project.set_display_name(project_general_settings.display_name)
        # if running through dml_generator there is no self.entity_project and we need to define it
        else:
            self.entity_project = EntitySubject(subject_id=project_general_settings.project_id,
                                                subject_type=SubjectTypesEnum.project,
                                                display_name=project_general_settings.display_name,
                                                description=project_general_settings.description)
        subject = EntitySubject.to_metadb_object(self.entity_project)
        self.project_settings_metadata_provider.insert_or_update_project_general_settings(
            project_general_settings.to_metadb_object(), self.user_isid, subject)

    def get_project_general_settings(self):
        """
        Get project general settings
        """
        self.logger.info("Going to retrieve project general settings")
        # check if user has permission to such action
        if self.auth_validator.validate(ActionType.READ_PROJECT_SETTINGS,
                                        {"settingsType": "general"}) == PermissionEffectsEnum.allow:
            project_general_settings = EntityProjectGeneralSettings.from_metadb_object(
                self.project_settings_metadata_provider.get_project_general_settings(
                    self.project_id))
            subject_details = self.subjects_management.get_subject(self.project_id)
            project_general_settings.set_description(subject_details.description)
            project_general_settings.set_display_name(subject_details.display_name)
            return project_general_settings
        raise AuthorizationError(
            f"The user {self.user_isid} does not have access to read project general settings")

    def get_project_environment(self, project_id: str = None):
        """
        Get project environment

        @return: environment of project. Default is dev
        """
        self.logger.info("Going to retrieve project environment")
        if not project_id:
            project_id = self.project_id
        project_general_settings = EntityProjectGeneralSettings.from_metadb_object(
            self.project_settings_metadata_provider.get_project_general_settings(
                project_id))
        return project_general_settings.environment if project_general_settings.environment else "dev"

    def get_aws_region(self):
        """
        Get aws region for current project
        This method does not have any authorization checks, as it only collects the aws region for current project,
        which is needed as part of secret manager initialization of secret management class
        """
        aws_region = EntityProjectAccountSettings.from_metadb_object(
            self.project_settings_metadata_provider.get_project_account_settings(
                project_id=self.project_id, account_type=ProjectAccountTypesEnum.aws)). \
            account_details.get('awsRegion', 'us-east-1')
        return aws_region
