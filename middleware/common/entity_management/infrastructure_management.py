import concurrent.futures
import copy
import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from common.api_clients.common.api_client import ApiObjectModel
from common.helpers.exception import NoDataError
from middleware.api.common.helpers import set_redis_key, delete_redis_key, SortAndPaginate, convert_to_bool
from middleware.common.api_clients.msd_api.msd_api_client import MSDApiClient
from middleware.common.entity_management.components_management import ComponentsManagement
from middleware.common.entity_management.entities.entity_project_account_settings import EntityProjectAccountSettings
from middleware.common.entity_management.entity_management import EntityManagement
from middleware.common.entity_management.subjects_management import SubjectManagement
from middleware.common.entity_management.project_settings_management import ProjectSettingsManagement
from middleware.common.helpers.datetime_formatter import from_datetime_to_str
from middleware.common.metadatabase.infrastructure_metadata_provider import InfrastructureMetadataProvider
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.helpers.exception import AuthTokenError, FailedConnectionError, AuthorizationError, BadRequest
from middleware.common.security.action_type import ActionType


# pylint: disable=too-many-instance-attributes, too-many-public-methods
class InfrastructureManagement(EntityManagement):
    """
    Infrastructure API
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._api_connection = kwargs.get("api_connection")
        self._msd_api_client = self._setup_msd_api_client()
        self._subjects_management = SubjectManagement(*args, **kwargs)
        self._project_settings_management = None
        self._aws_account_settings = None
        self._infrastructure_metadata_provider = None
        self._components_management = None

    @property
    def aws_account_settings(self) -> EntityProjectAccountSettings:
        """
        get aws account settings
        """
        if not self._aws_account_settings:
            self._aws_account_settings = self.project_settings_management.get_project_account_settings(
                account_type=ProjectAccountTypesEnum.aws, check_permission=False, raise_not_found_error=True
            )
        return self._aws_account_settings

    def _setup_msd_api_client(self):
        """
        Set up the MSD API client
        """
        msd_internal_api_url = os.environ.get("MSD_INTERNAL_API_URL", "iapi-test.merck.com")
        msd_internal_api_secret = self._api_connection

        self.logger.info(
            f"Creating MSD Api client:\n "
            f"MSD_INTERNAL_API_URL={msd_internal_api_url}\n"
            f"MSD_INTERNAL_API_SECRET={msd_internal_api_secret}"
        )

        return MSDApiClient(
            api_url=msd_internal_api_url,
            lambda_secrets_manager=self.lambda_secrets_manager,
            secret_manager_connection=msd_internal_api_secret,
        )

    @property
    def project_settings_management(self):
        """
        project settings management property
        """
        if self._project_settings_management is None:
            self._project_settings_management = ProjectSettingsManagement(
                logger=self.logger,
                metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager,
                user_isid=self.user_isid,
                selected_subjects=self.selected_subjects,
            )
        return self._project_settings_management

    @property
    def components_management(self):
        """
        components management property
        """
        if self._components_management is None:
            self._components_management = ComponentsManagement(
                logger=self.logger,
                metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager,
                user_isid=self.user_isid,
                selected_subjects=self.selected_subjects,
            )
        return self._components_management

    @property
    def infrastructure_metadata_provider(self):
        """
        infrastructure metadata provider property
        """
        if self._infrastructure_metadata_provider is None:
            self._infrastructure_metadata_provider = InfrastructureMetadataProvider(
                self.logger, self.metadatabase_connection, self.lambda_secrets_manager
            )
        return self._infrastructure_metadata_provider

    def generate_presigned_url(self, key: str, file_name: str, bucket_type: str = None, bucket_name: str = None) -> str:
        """
        Generate presigned using presigned_post method URL for uploading the files into S3
        @param key: key of the file we want to upload
        @param file_name: name of the file
        @param bucket_type: bucket type into which user wants to upload the file
        @param bucket_name: if given, we are selecting uploading file in target bucket
        @return: presinged URL
        """
        self.logger.info("Going to generate presigned URL")
        # refresh tokens for presigned URL
        self.refresh_aws_tokens(self.project_settings_management)
        if not bucket_name:
            if bucket_type == "data_bucket":
                bucket_name = self.aws_account_settings.account_details["dataBucket"]
            elif bucket_type == "resource_bucket":
                bucket_name = self.aws_account_settings.account_details["resourcesBucket"]
            else:
                raise Exception("The allowed bucket_type values are either data_bucket or resource_bucket")
        # if the key was passed with trailing / we need not add it between key and filename
        object_key = f"{key}{file_name}" if key.endswith("/") else f"{key}/{file_name}"
        region_name = self.project_settings_management.get_aws_region()
        self.logger.info(f"Presigned URL parameters: bucket={bucket_name}, key={object_key}")
        presigned_url = boto3.client(
            "s3",
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            aws_session_token=self.aws_session_token,
            region_name=region_name,
            config=Config(signature_version="s3v4", region_name=region_name),
        ).generate_presigned_post(Bucket=bucket_name, Key=object_key, ExpiresIn=3600)
        self.logger.info("Got presigned URL: %s", presigned_url)
        return presigned_url

    def return_security_groups(self, exclude_onboarded_groups):
        """
        Return the list of the security groups applied with the filter
        """
        self.logger.info("Going to retrieve security groups")
        sg_prefix = os.environ.get("MSD_INTERNAL_API_SG_PREFIX", "")
        security_groups = self._msd_api_client.get_security_groups(security_group_filter=sg_prefix)

        self.logger.info(f"Security groups retrieving data:\n MSD_INTERNAL_API_SG_PREFIX={sg_prefix}")
        self.logger.info(f"Retrieved SG from API: {security_groups}")

        if exclude_onboarded_groups:
            onboarded_groups, _ = self._subjects_management.get_subjects(subject_type=SubjectTypesEnum.group)
            # exclude the groups which are provisioned in the meta db
            for group in onboarded_groups:
                for idx, security_group in enumerate(security_groups.items):
                    if security_group["name"] == group["subjectId"]:
                        security_groups.items.pop(idx)
        # check present of display name
        for _, security_group in enumerate(security_groups.items):
            if not security_group["displayName"]:
                security_group["displayName"] = security_group["name"]
        self.logger.info(f"Filtered SG which will be return in response: {security_groups}")
        return security_groups

    def revoke_token(self, headers: dict, redis_client):
        """
        Revoke the token using the Authentication API

        @param headers: API gateway proxy event headers
        @param redis_client: redis client to use for deletion of the key
        @return: API response for the token revoke action
        """
        access_token = headers["authtoken"]
        delete_redis_key(key=access_token, redis_client=redis_client)
        return self._msd_api_client.revoke_token(access_token=access_token)

    # pylint: disable=inconsistent-return-statements
    def get_or_refresh_token(self, json_body: dict, query_string_parameters: dict, redis_client) -> dict[str]:
        """
        Get or refresh token from the Authentication API

        @param json_body: Api gateway proxy event json body
        @param query_string_parameters: Api gateway proxy event query string parameters
        @param redis_client: redis client
        @return: Dictionary representation of the API authentication call
        @rtype: Dictionary
        """
        self.logger.info("Calling _get_or_refresh_token")
        grant_type = query_string_parameters.get("grant_type")
        if not grant_type:
            raise AuthTokenError("Missing grant type for refresh token api call")
        self.logger.info(f"grant_type is {grant_type}")
        refresh = grant_type == "refresh_token"
        if refresh:
            token = json_body.get("refresh_token")
        else:
            token = json_body.get("code")
        if not token:
            raise AuthTokenError("Missing the refresh_token or code in the body of the API call")

        response = self.get_user_token(token=token, refresh=refresh)
        if not response:
            raise AuthTokenError("Missing the response from the API call for the get or refresh auth token")
        response = response.as_dict()

        # get the user info
        user_info = self.get_user_info(token=response["access_token"])
        if not user_info:
            raise AuthTokenError("Missing the response from API call for the get of the user info")
        response.update(user_info.as_dict())
        response_copy = copy.deepcopy(response)

        # get the security groups of the user
        groups_res = self.get_user_security_groups(isid=response["isid"])
        if not groups_res:
            raise AuthTokenError("Missing the response from the API call for the get of the user groups")
        groups = [group["name"] for group in groups_res.as_dict()["items"]]

        # add the groups to the redis record
        response_copy["securityGroups"] = groups
        self.logger.info("Setting redis key ")
        set_redis_key(token_info=response_copy, redis_client=redis_client)
        return response

    def get_user_token(self, token: str, refresh: bool = False) -> ApiObjectModel:
        """
        Get or refresh the user token from the Authentication API

        @param token: Authentication token
        @param refresh: refresh indication
        @return: user token
        """
        return self._msd_api_client.get_or_refresh_token(token=token, refresh=refresh)

    def get_user_info(self, token: str) -> ApiObjectModel:
        """
        Get the user information from the Authentication API, using the get_user_info method

        @param token: the access token from the Authentication API
        @return: ApiObjectModel representing the user information from the Authentication API
        @rtype: ApiObjectModel
        """
        return self._msd_api_client.get_user_info(token=token)

    def get_user_security_groups(self, isid: str) -> ApiObjectModel:
        """
        Return the list of the groups for the isid

        @param isid: the isid of the user
        @return: ApiObjectModel representing list of the security groups of the user
        @rtype: ApiObjectModel
        """
        return self._msd_api_client.get_security_group_by_isid(isid=isid)

    def send_email(self, headers: dict, json_body: dict) -> ApiObjectModel:
        """
        Send email

        @param headers: the access token from the Authentication API
        @param json_body: request of the body from which
        @return: ApiObjectModel representing the user information from the Authentication API
        @rtype: ApiObjectModel
        """
        # first prepare headers of the request
        headers_for_request = {
            "Accept": "application/problem+json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {headers.get('authtoken')}",
        }
        # body of request needs to be of following format
        body_request = {
            "subject": json_body["subject"],
            "body": {"contentType": "text", "content": json_body["content"]},
            "toRecipients": SortAndPaginate.clean_and_relist_listed_strings(json_body["recipient"]),
            "ccRecipients": [],
        }
        return self._msd_api_client.send_email(headers=headers_for_request, data=body_request)

    def get_project_onboard_and_groups_information(self) -> dict:
        """
        This method call is for getting project - groups and onboard information
        It is somewhat optimal as we are returning only the values from DB and not objects with relationships
        @rtype: dict
        """
        output_dict = {}
        # get_projects_and_groups returns entries/tuples in which the order is given via the with_entities call
        list_of_entries = self.infrastructure_metadata_provider.get_project_onboard_and_groups_information()
        # entry is of format (project_id, properties, group_id)
        for project_id, properties, group_id in list_of_entries:
            # if project is not yet in output dictionary we input it there with empty list of groups
            if not output_dict.get(project_id):
                output_dict[project_id] = {"groups": []}
            # Extract onboardEmail and onboardMessage if they exist in properties
            if "onboardEmail" in properties:
                output_dict[project_id]["onboardEmail"] = properties["onboardEmail"]

            if "onboardMessage" in properties:
                output_dict[project_id]["onboardMessage"] = properties["onboardMessage"]
            # last we want to extract all groups which are under specified project
            if group_id not in output_dict[project_id]["groups"]:
                output_dict[project_id]["groups"].append(group_id)
        return output_dict

    def obtain_s3_resource(self, attributes) -> boto3.resource:
        """
        obtains s3 resource from components management, else raises error if the connection is invalid
        @param: attributes - connection attributes of s3 connector, needed for passing of the aws_assume_role
        @rtype boto3.resource
        @return boto3.resource instance of s3
        """
        self.logger.info("Starting method obtain_s3_resource to obtain s3_resource from components_management")
        s3_resource = self.components_management.create_s3_resource(attributes)
        if not s3_resource:
            raise FailedConnectionError("Connection error during S3 connection, revalidate aws account settings")
        return s3_resource

    def s3_object_add(self, json_body: dict) -> str:
        """
        add object - empty folder - to s3 with given path, autocorrects the key to end with / if it does not
        @param: json_body
        @rtype: string
        @return: str message with info about added object
        """
        self.logger.info("Starting s3_object_add method")
        bucket_name = json_body.get("path", {}).get("bucketName")
        object_path = json_body.get("path", {}).get("objectPath")
        # if input did not have trailing /, we add it, as it is only possible to add folder
        # which needs to end with /
        if not object_path.endswith("/"):
            object_path += "/"
        if (
            self.auth_validator.validate(
                ActionType.WRITE_S3_OBJECTS, {"s3Bucket": bucket_name, "s3ObjectKey": object_path}
            )
            == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"The user {self.user_isid} within group {self.group_id} and project {self.project_id}"
                f" does not have permission to write s3 object - missing writeS3Objects permissions"
            )
        s3_resource = self.obtain_s3_resource(json_body.get("attributes"))
        self.logger.info(f"Creating object in bucket {bucket_name} and path {object_path}")
        s3_resource.meta.client.put_object(Bucket=bucket_name, Key=object_path)
        return f"Folder with path: {object_path} in bucket: {bucket_name} was added successfully."

    def s3_objects_remove(self, json_body: dict) -> str:
        """
        remove objects from s3, which paths were passed in the objectsPath,
        removes all objects which are nested in given objects
        @param: json_body
        @rtype: string
        @return: str message with info about removed object
        """
        self.logger.info("Starting s3_objects_remove method")
        if self.auth_validator.validate(ActionType.REMOVE_S3_OBJECTS, {}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"The user {self.user_isid} within group {self.group_id} and project {self.project_id}"
                f" does not have permission to remove s3 object - missing removeS3Objects permission"
            )
        s3_resource = self.obtain_s3_resource(json_body.get("attributes"))
        bucket_name = json_body.get("path", {}).get("bucketName")
        # as is possible to delete several keys, we need to extract it from the request
        objects_path_list = SortAndPaginate.clean_and_relist_listed_strings(
            json_body.get("path", {}).get("objectsPath")
        )
        # as it is possible to pass more than one path to be deleted, we need to go thought them all
        for object_path in objects_path_list:
            # if passed object_path is for object - does not end with /, we need to delete only that one object,
            # if we are deleting s3 object, which is alone it the folder, the folder gets removed also,
            # as there are no keys in s3 for it anymore
            # if it is folder, we need to delete all nested object first
            if object_path.endswith("/"):
                self.logger.info(f"Beginning of nested s3 objects given by prefix path {object_path}")
                try:
                    # obtain all keys inside specified object - we are calling it without delimiter
                    objects = s3_resource.meta.client.list_objects_v2(Bucket=bucket_name, Prefix=object_path).get(
                        "Contents"
                    )
                except ClientError as exc:
                    self.logger.info(f"Error while listing objects, with error message {exc.response['Error']['Code']}")
                    raise FailedConnectionError(
                        "Connection error during S3 connection, revalidate the connection"
                    ) from exc
                if not objects:
                    raise NoDataError("No objects, which should be deleted based on the inputs were found.")
                # extract the object keys of all nested objects
                object_keys = [{"Key": obj["Key"]} for obj in objects]
                # delete all nested objects
                s3_resource.meta.client.delete_objects(Bucket=bucket_name, Delete={"Objects": object_keys})
            # Delete the object itself
            s3_resource.meta.client.delete_object(Bucket=bucket_name, Key=object_path)
        return f"Objects with paths: {objects_path_list} in bucket: {bucket_name} were removed successfully."

    def s3_obtain_presigned_url(self, json_body: dict, is_upload: bool = True) -> str:
        """
        method for obtaining presigned url for uploading or downloading file to/from s3
        this method uses the method for generate_presigned_url, however as it past, we need separate call if it is
        download - for download we leverage the generate_presigned_url with get_object inside
        @param: json_body
        @param: is_upload - bool to differentiate between upload and download call
        @rtype: string
        @return: str with url info
        """
        self.logger.info(
            f"Starting s3_obtain_presigned_url method for obtaining presigned url "
            f" as part of upload request {is_upload} or download request {not is_upload}"
        )
        bucket_name = json_body.get("path", {}).get("bucketName")
        key = json_body.get("path", {}).get("objectPath")
        file_name = json_body.get("path", {}).get("objectName")
        if (
            self.auth_validator.validate(ActionType.WRITE_S3_OBJECTS, {"s3Bucket": bucket_name, "s3ObjectKey": key})
            == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"The user {self.user_isid} within group {self.group_id} and project {self.project_id}"
                f" does not have permission to upload or download s3 object - missing writeS3Objects permission"
            )
        if is_upload:
            # method of the infrastructure management class, which uses generate_presinged_post method of s3 client
            url = self.generate_presigned_url(bucket_name=bucket_name, key=key, file_name=file_name)
        else:
            s3_resource = self.obtain_s3_resource(attributes=json_body.get("attributes"))
            # method for generating of presigned url from s3 client for download
            url = s3_resource.meta.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": key, "ResponseContentDisposition": "attachment"},
                ExpiresIn=3600,
            )
        self.logger.info("Got presigned URL: %s", url)
        return url

    def s3_calculate_total_size(self, json_body: dict) -> int:
        """
        method for obtaining total size of objects passed in via path
        @param: json_body
        @rtype: int
        @return: total size of objects in bytes
        """
        self.logger.info("Starting s3_calculate_total_size method")
        bucket_name = json_body.get("path", {}).get("bucketName")
        objects_paths = SortAndPaginate.clean_and_relist_listed_strings(json_body.get("path", {}).get("objectsPath"))
        if (
            self.auth_validator.validate(ActionType.WRITE_S3_OBJECTS, {"s3Bucket": bucket_name, "s3ObjectKey": ""})
            == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"The user {self.user_isid} within group {self.group_id} and project {self.project_id}"
                f" does not have permission to calculate size of s3 objects - missing writeS3Objects permission"
            )
        s3_resource = self.obtain_s3_resource(json_body.get("attributes"))
        if len(objects_paths) == 1:
            total_size = self.compute_size_for_path(s3_resource, bucket_name, objects_paths[0])
        else:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                total_size = sum(
                    list(
                        executor.map(
                            lambda path: self.compute_size_for_path(s3_resource, bucket_name, path), objects_paths
                        )
                    )
                )
        return total_size

    @staticmethod
    def compute_size_for_path(s3_resource: boto3.resource, bucket_name: str, object_path: str) -> int:
        """
        method which will count size of all objects, which are under path/key in s3
        @param s3_resource boto3 s3 resource
        @param bucket_name name of the bucket
        @param object_path path of the object
        @return: size of the objects in bytes
        @rtype: int
        """
        truncated = True
        args_for_call = {"Bucket": bucket_name, "Prefix": object_path}
        size = 0
        while truncated:
            response = s3_resource.meta.client.list_objects_v2(**args_for_call)
            truncated = response.get("IsTruncated", False)
            for key in response.get("Contents", {}):
                size += key.get("Size", 0)
            if truncated:
                args_for_call.update({"ContinuationToken": response.get("NextContinuationToken")})
        return size

    # pylint: disable=too-many-locals
    def s3_copy_or_move_objects(self, json_body: dict, delete: bool = False) -> str:
        """
        method for copying or moving files in s3 bucket into new location
        @param: json_body
        @param: delete - bool flag if the original objects should be deleted after copy
        @rtype:  string
        @return: new common paths
        """
        self.logger.info(f"Starting s3_copy_or_move_objects method with delete flag equal to {delete}")
        bucket_name = json_body.get("path", {}).get("bucketName")
        new_path = json_body.get("path", {}).get("newPath")
        if (
            self.auth_validator.validate(ActionType.WRITE_S3_OBJECTS, {"s3Bucket": bucket_name, "s3ObjectKey": ""})
            == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"The user {self.user_isid} within group {self.group_id} and project {self.project_id}"
                f" does not have permission to copy or move s3 objects - missing writeS3Objects permission"
            )
        if not new_path.endswith("/"):
            raise BadRequest(
                f"New location {new_path} should be folder and as such end with '/', please input correct location."
            )
        s3_resource = self.obtain_s3_resource(json_body.get("attributes"))
        objects_paths = SortAndPaginate.clean_and_relist_listed_strings(json_body.get("path", {}).get("objectsPath"))

        # we need to parse the new_path param as it may contain full URI path
        path_parse = new_path
        if path_parse.startswith("s3://"):
            path_parse = path_parse[len("s3://") :]
        new_bucket = path_parse.split("/")[0]
        # extract the remaining object path
        new_objects_path = "/".join(path_parse.split("/")[1:])
        for object_path in objects_paths:
            # if object_path did not end with /, object_path_split[-1] is not "",
            # it is not folder, no need to list objects with this key,
            # and we can go and copy it into target location
            object_path_split = object_path.split("/")
            if object_path_split[-1]:
                self.copy_object_from_s3_with_delete(
                    s3_resource=s3_resource,
                    bucket_name_old=bucket_name,
                    bucket_name_new=new_bucket,
                    prefix=object_path,
                    new_path=new_objects_path,
                    key_name=object_path,
                    delete=delete,
                )
                # go for next object_path
                continue
            # otherwise the object_path is folder and we need to look inside it and collect underlying objects
            truncated = True
            # first args for call, as we do not yet have continuation token for first call
            args_for_call = {"Bucket": bucket_name, "Prefix": object_path}
            # if there is more than 1000 keys in target s3 location, we need to cycle though them
            while truncated:
                # obtain the underlying objects
                response = s3_resource.meta.client.list_objects_v2(**args_for_call)
                truncated = response.get("IsTruncated", False)
                contents = response.get("Contents", [])
                # if there is only one key, no need to use thread pool executor
                if len(contents) == 1:
                    self.copy_object_from_s3_with_delete(
                        s3_resource=s3_resource,
                        bucket_name_old=bucket_name,
                        bucket_name_new=new_bucket,
                        prefix=object_path,
                        new_path=new_objects_path,
                        key_name=contents[0].get("Key"),
                        delete=delete,
                    )
                else:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        # as it is static method without return, we are not assigned the value to anything
                        # pylint: disable=expression-not-assigned
                        [
                            executor.submit(
                                self.copy_object_from_s3_with_delete,
                                s3_resource=s3_resource,
                                bucket_name_old=bucket_name,
                                bucket_name_new=new_bucket,
                                prefix=object_path,
                                new_path=new_objects_path,
                                key_name=key.get("Key"),
                                delete=delete,
                            )
                            for key in response.get("Contents", {})
                        ]
                # need for update of next token is only in case that the response was truncated
                if truncated:
                    args_for_call.update({"ContinuationToken": response.get("NextContinuationToken")})
        return new_path

    @staticmethod
    def copy_object_from_s3_with_delete(
        s3_resource, bucket_name_old: str, bucket_name_new: str, prefix: str, new_path: str, key_name: str, delete: bool
    ):
        """
        function for copying objects from s3 to other location, with delete flag set to True -
        objects will be copied and deleted from the original location
        @param: s3_resource - created s3 resource in which we are copying file
        @param: bucket_name_old - name of source bucket
        @param: bucket_name_new - name of target bucket
        @param: prefix - common prefix of the file to be
        @param: new_path - new target file for copying
        @param: key_name - name of the key to be copied
        @param: delete - bool flag if the original objects should be deleted after copy
        """
        # location from which we are copying is bucket name and key of the object
        location = bucket_name_old + "/" + key_name
        # we have key, first we need to remove prefix from it, however if prefix is folder, we need to add
        # last part of it, because we were copying/moving whole folder there
        # if the key-name is only object - the following line will equal ''
        name_after_prefix = key_name[len(prefix) :]
        if name_after_prefix:
            # if it is not '', we were manipulating some objects in some folder, so we need to add the last part of the
            # path to the value of the new key, as the prefix endswith /, the folder name is the second last element
            folder_name = prefix.split("/")[-2] + "/"
            new_name_key = new_path + folder_name + name_after_prefix
        else:
            # if name_after_prefix was '', we were moving only some file directly and as such key_name has the full path
            # we need to keep only the last part
            new_name_key = new_path + key_name.split("/")[-1]
        try:
            # copy object into new location
            s3_resource.Object(bucket_name_new, new_name_key).copy_from(CopySource=location)
            if delete:
                s3_resource.Object(bucket_name_old, key_name).delete()
        except ClientError as exc:
            raise NoDataError("Can not locate specified file to be renamed, please revalidate") from exc

    # pylint: disable=no-member
    def s3_rename_object(self, json_body: dict) -> str:
        """
        method for renaming object
        @param: json_body
        @rtype: string
        @return: new name of the renamed s3 object
        """
        self.logger.info("Starting s3_rename_object method")
        new_name = json_body.get("path", {}).get("objectName")
        bucket_name = json_body.get("path", {}).get("bucketName")
        object_path = json_body.get("path", {}).get("objectPath")
        if (
            self.auth_validator.validate(
                ActionType.WRITE_S3_OBJECTS, {"s3Bucket": bucket_name, "s3ObjectKey": object_path}
            )
            == PermissionEffectsEnum.deny
        ):
            raise AuthorizationError(
                f"The user {self.user_isid} within group {self.group_id} and project {self.project_id}"
                f" does not have permission to rename s3 object - missing writeS3Objects permission"
            )
        s3_resource = self.obtain_s3_resource(json_body.get("attributes"))
        # boto s3 does not have simple rename feature, so we will copy with new name and remove old file
        location = bucket_name + "/" + object_path
        # we extract prefix from object_path - as we need it for inputting of new_name key
        path_index = object_path.rfind("/")
        prefix = object_path[: path_index + 1]
        # add prefix before the new_name
        new_name_key = prefix + new_name
        try:
            # copy old file under new name in same location
            s3_resource.Object(bucket_name, new_name_key).copy_from(CopySource=location)
        except ClientError as exc:
            raise NoDataError("Can not locate specified file to be renamed, please revalidate") from exc
        # delete old file
        s3_resource.Object(bucket_name, object_path).delete()
        return new_name

    def s3_browse(self, json_body: dict):
        """
        Return objects in current s3 browser location specified by params in body of request
        Process flow depends on additionalFiltering
        1. bucketsOnly: True -> list of all available s3 buckets will be returned
        2. with given bucketName - will return objects in s3 by given prefix - in root adjusted by it
            prefix filters objects from bucket root
                - prefix = 'folder1/' will return objects from folder1
                - prefix = 'test-' will return objects starting with test- from root
                - prefix = 'folder1/test-' will return objects from folder1 starting with test-
            if there were more than 10 objects, also nextToken is returned, by adding this to request
            as startToken, you can obtain continuing objects
        @param: json_body - body of the request
        @return dictionary of objects containing information
        @rtype dictionary
        """
        self.logger.info(f"User {self.user_isid} is starting s3_browse method, with request {json_body}")
        s3_resource = self.obtain_s3_resource(json_body.get("attributes"))
        # if bucket name was passed in, we want to obtain the paths inside it
        additional_filtering = json_body.get("additionalFiltering", {})

        # if bucketsOnly is True we obtain only names of possible buckets
        if convert_to_bool(additional_filtering.get("bucketsOnly")):
            self.logger.info("Request was made to return only buckets")
            # it is possible to filtrate bucket names on string
            filtration = additional_filtering.get("bucketFiltration", "")
            output_names = [
                {"name": bucket.get("Name")}
                for bucket in s3_resource.meta.client.list_buckets().get("Buckets")
                if filtration in bucket.get("Name")
            ]
            if not output_names:
                raise NoDataError(
                    "There are no buckets in your aws account, which satisfy filtration condition to "
                    f"contain {filtration}"
                )
            return {"items": output_names}
        # prefix is for filtrating and also 'changing' folders - example folder1/data will return all objects in
        # folder1 starting with 'data'
        bucket_name = additional_filtering.get("bucketName", None)
        # check if bucket_name was not passed, it is bad request as it is not bucketsOnly request, which would be above
        if not bucket_name:
            raise BadRequest(
                "Bucket name was not specified while not passing the 'bucketsOnly': true, revalidate request please"
            )
        prefix = additional_filtering.get("prefix", "")
        # how many keys should be returned from the s3
        max_keys = int(additional_filtering.get("maxKeys", 10))
        # we need to pass arguments like this, since we can not pass None or '' as value for ContinuationToken
        args_for_call = {"Bucket": bucket_name, "Delimiter": "/", "Prefix": prefix, "MaxKeys": max_keys}
        # beginning of pagination, if we get in request property startToken, we want to obtain objects starting from
        # that location, if given, we add it to the args
        continuation_token = additional_filtering.get("startToken", "")
        if continuation_token:
            args_for_call.update({"ContinuationToken": continuation_token})
        self.logger.info(f"Arguments for obtaining of objects from selected bucket are: {args_for_call}")
        try:
            objects_in_s3 = s3_resource.meta.client.list_objects_v2(**args_for_call)
        except ClientError as exc:
            raise NoDataError(
                f"Issue with connection to defined path. Please recheck the existence of "
                f"bucket {bucket_name} and prefix {prefix}, if given"
            ) from exc
        object_keys = []
        for obj in objects_in_s3.get("CommonPrefixes", {}):
            # for response to be easier parsable on FE, we return also keys with unknown values, which mimic s3 console
            object_keys.append(
                {
                    "key": obj.get("Prefix"),
                    "objectType": "folder",
                    "fileType": None,
                    "last_modified": None,
                    "size": None,
                }
            )
        for obj in objects_in_s3.get("Contents", {}):
            # we are converting date to str, keeping it in iso8601 format - "yyyy-mm-dd hh:mm:ss+00:00"
            last_modified = from_datetime_to_str(obj.get("LastModified"))
            split_array = obj.get("Key").split(".")
            # we return type as last part after the . in key, if file does not contain ., we return None
            type_of_key = split_array[-1] if len(split_array) > 1 else None
            # we convert size to str for better handling
            size = obj.get("Size")
            object_keys.append(
                {
                    "key": obj.get("Key"),
                    "objectType": "file",
                    "fileType": type_of_key,
                    "last_modified": last_modified,
                    "size": size,
                }
            )
        dict_out = {"name": bucket_name, "objects": {"path": prefix, "keys": object_keys}}
        # if property IsTruncated is False, there is no more objects, after these selected in the S3 bucket
        # and as such, we do not have token for next page to be returned
        if objects_in_s3.get("IsTruncated"):
            self.logger.info(
                "There are more than 10 objects in the S3, response is truncated, enhancing response with nextToken"
            )
            dict_out["objects"].update({"nextToken": objects_in_s3.get("NextContinuationToken")})
        dict_out = {"items": [dict_out]}
        return dict_out
