import json
import re
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.helpers import get_env_or_header_value, convert_to_bool
from middleware.api.common.http_method_utils import create_error_response
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.common.entity_management.infrastructure_management import InfrastructureManagement
from middleware.common.helpers.exception import AuthTokenError, BadRequest


# pylint: disable=too-many-branches
class InfrastructureLambda(AWSLambdaEventHandler):
    """
    Lambda class for Infrastructure API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.infrastructure_management = InfrastructureManagement(
            logger=self.logger,
            metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name="METADATA_CONNECTION", header_name="metadata-connection", logger=self.logger
            ),
            lambda_secrets_manager=self.lambda_secrets_manager,
            user_isid=self.user_isid,
            selected_subjects=self.selected_subjects,
            api_connection=get_env_or_header_value(
                event=self.event,
                env_name="MSD_INTERNAL_API_SECRET",
                header_name="msd-api-connection",
                logger=self.logger,
            ),
        )

    def _invoke_get_presigned_url(self):
        """
        Invoke method call for getting the presigned url

        @return API response of presigned url
        """
        if "bucketType" not in self.event.json_body and "bucketName" not in self.event.json_body:
            raise BadRequest(
                "Both bucketType and bucketName are missing in the request body, "
                "passing either one of them is mandatory."
            )

        self.logger.info("Calling _invoke_get_presigned_url")
        presigned_url = self.infrastructure_management.generate_presigned_url(
            key=self.event.json_body["targetS3Key"],
            bucket_type=self.event.json_body.get("bucketType", None),
            file_name=self.event.json_body["fileName"],
            bucket_name=self.event.json_body.get("bucketName", None)
        )
        return {"statusCode": 200, "body": json.dumps(presigned_url)}

    def _get_available_groups(self):
        """
        Invoke method call for getting the available groups for the UI project.

        @return API response of available groups response
        """
        self.logger.info("Calling _get_available_groups")
        exclude_onboarded_groups = convert_to_bool(
            self.event.query_string_parameters.get("excludeOnboardedGroups", None)
        )
        sg_list = self.infrastructure_management.return_security_groups(
            exclude_onboarded_groups=exclude_onboarded_groups
        )
        return {"statusCode": 200, "body": json.dumps({"items": sg_list.items})}

    # pylint: disable=broad-except
    def _invoke_get_or_refresh_token(self):
        """
        Invoke method call for getting the authentication token for the UI project

        Steps are:
            * take the refresh token from the self.event.json.body
        @return API response with authentication token
        """
        self.logger.info("Calling _get_or_refresh_token")
        response = None
        try:
            response = self.infrastructure_management.get_or_refresh_token(
                json_body=self.event.json_body,
                query_string_parameters=self.event.query_string_parameters,
                redis_client=self.redis_client,
            )
        except Exception as exception:
            if re.findall("Error fetching token", exception.args[0]):
                self.logger.error(f"error getting refresh token: {exception}")
                raise AuthTokenError("Error getting oauth token") from exception
        if not response:
            raise AuthTokenError("Missing the response from the API call for the get or refresh auth token")
        return {"statusCode": 200, "body": json.dumps(response)}

    def _invoke_revoke_token(self):
        """
        Invoke method call for revoking the authentication token for the UI project
        @return API response
        """
        self.logger.info("Calling _invoke_revoke_token")
        self.infrastructure_management.revoke_token(headers=self.event.headers, redis_client=self.redis_client)
        return {"statusCode": 200, "body": json.dumps({"result": "success", "details": "Token was revoked"})}

    def _invoke_send_email(self):
        """
        Invoke method call for sending email via merck email service api
        @return API response
        """
        self.logger.info("Calling _invoke_send_email")
        self.infrastructure_management.send_email(headers=self.event.headers, json_body=self.event.json_body)
        return {
            "statusCode": 200,
            "body": json.dumps(
                {"result": "success", "details": f"Email sent to mail: {self.event.json_body.get('recipient')}"}
            ),
        }

    def _invoke_get_project_onboard_and_groups_information(self):
        """
        Invoke method call for getting projects underlying groups and onboard information
        @return API response
        """
        self.logger.info("Calling _invoke_get_project_onboard_and_groups_information")
        projects_information = self.infrastructure_management.get_project_onboard_and_groups_information()
        return {"statusCode": 200, "body": json.dumps(projects_information)}

    def _invoke_s3_object_add(self):
        """
        Invoke method call for adding s3 object into specified bucket and folder given by prefix
        @return API response
        """
        self.logger.info("Calling _invoke_s3_object_add")
        response = self.infrastructure_management.s3_object_add(json_body=self.event.json_body)
        return {"statusCode": 200, "body": json.dumps({"result": "success", "details": response})}

    def _invoke_s3_objects_remove(self):
        """
        Invoke method call for removing s3 objects in specified bucket and given paths,
        removes all nested objects
        @return API response
        """
        self.logger.info("Calling _invoke_s3_objects_remove")
        response = self.infrastructure_management.s3_objects_remove(json_body=self.event.json_body)
        return {"statusCode": 200, "body": json.dumps({"result": "Deleted", "details": response})}

    def _invoke_s3_upload_file(self):
        """
        Invoke method call for upload of s3 object in specified bucket and specific path,
        for this we provide presigned URL
        @return API response
        """
        self.logger.info("Calling _invoke_s3_upload_file")
        presinged_url = self.infrastructure_management.s3_obtain_presigned_url(
            json_body=self.event.json_body, is_upload=True
        )
        return {"statusCode": 200, "body": json.dumps(presinged_url)}

    def _invoke_s3_download_file(self):
        """
        Invoke method call for download of s3 file in specified bucket and specific path,
        for this we provide presigned URL back to UI
        @return API response
        """
        self.logger.info("Calling _invoke_s3_download_file")
        presinged_url = self.infrastructure_management.s3_obtain_presigned_url(
            json_body=self.event.json_body, is_upload=False
        )
        return {"statusCode": 200, "body": json.dumps(presinged_url)}

    def _invoke_s3_calculate_total_size(self):
        """
        Invoke method call for calculating of total size of selected s3 objects
        @return API response
        """
        self.logger.info("Calling _invoke_s3_calculate_total_size")
        json_body = self.event.json_body
        if not self.event.json_body.get("path", {}).get("bucketName") or not self.event.json_body.get("path", {}).get(
            "objectsPath"
        ):
            raise BadRequest("Bucket name or paths of objects for which size is to be calculated are missing")
        total_size = self.infrastructure_management.s3_calculate_total_size(json_body=json_body)
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "result": "Success",
                    "totalSize": total_size,
                    "details": f"Total size of selected objects is {total_size} bytes",
                }
            ),
        }

    def _invoke_s3_move_objects(self):
        """
        Invoke method call for moving selected objects into different location
        @return API response
        """
        self.logger.info("Calling _invoke_s3_move_objects")
        new_path = self.infrastructure_management.s3_copy_or_move_objects(json_body=self.event.json_body, delete=True)
        return {
            "statusCode": 200,
            "body": json.dumps({"result": "Success", "details": f"Objects were moved to {new_path}"}),
        }

    def _invoke_s3_copy_objects(self):
        """
        Invoke method call for copying selected objects into new location
        @return API response
        """
        self.logger.info("Calling _invoke_s3_copy_objects")
        new_path = self.infrastructure_management.s3_copy_or_move_objects(json_body=self.event.json_body, delete=False)
        return {
            "statusCode": 200,
            "body": json.dumps({"result": "Success", "details": f"Objects were copied to {new_path}"}),
        }

    def _invoke_s3_rename_object(self):
        """
        Invoke method call for renaming selected object
        @return API response
        """
        self.logger.info("Calling _invoke_s3_rename_object")
        new_name = self.infrastructure_management.s3_rename_object(json_body=self.event.json_body)
        return {
            "statusCode": 200,
            "body": json.dumps({"result": "Success", "details": f"Object was renamed to {new_name}"}),
        }

    def _invoke_s3_browse(self):
        """
        Invoke method call for s3 browsing logic, main call to open and travel inside the
        s3 browser
        @return API response
        """
        self.logger.info("Calling _invoke_s3_browse")
        items = self.infrastructure_management.s3_browse(json_body=self.event.json_body)
        return {"statusCode": 200, "body": json.dumps(items)}

    # pylint: disable=too-many-return-statements
    def invoke(self):
        """
        Invoke lambda function logic

        @return method call
        """
        # ******************************** GET PRESIGNED URL CALL *********************************************
        if self.event.http_method == "POST" and self.event.resource.endswith(
            "/infrastructure/s3/presignedurl/generate"
        ):
            return self._invoke_get_presigned_url()
        # *******************************  GET AVAILABLE GROUPS ***********************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/infrastructure/groups"):
            return self._get_available_groups()
        # *******************************  AUTH TOKEN *********************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/token"):
            return self._invoke_get_or_refresh_token()
        # *******************************  REVOKE TOKEN *******************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/revoke"):
            return self._invoke_revoke_token()
        # *******************************  SEND EMAIL *********************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/email/send"):
            return self._invoke_send_email()
        # *******************************  GET PROJECTS, GROUPS AND ONBOARD INFORMATION  *****************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/infrastructure/projects"):
            return self._invoke_get_project_onboard_and_groups_information()
        # *******************************  BROWSE S3 - OBTAIN OBJECTS ************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/s3/browse"):
            return self._invoke_s3_browse()
        # *******************************  S3 browser manipulation actions         **********************************
        # *******************************  ADD OBJECT TO S3 *********************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/s3/object/add"):
            return self._invoke_s3_object_add()
        # *******************************  REMOVE OBJECT FROM S3 *****************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/s3/object/remove"):
            return self._invoke_s3_objects_remove()
        # *******************************  UPLOAD OBJECT FROM S3 *****************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/s3/object/upload"):
            return self._invoke_s3_upload_file()
        # *******************************  DOWNLOAD OBJECT FROM S3 *****************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/s3/object/download"):
            return self._invoke_s3_download_file()
        # *******************************  CALCULATE TOTAL SIZE OF OBJECTS FROM S3 *************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/s3/object/size"):
            return self._invoke_s3_calculate_total_size()
        # *******************************  MOVE OBJECTS IN S3 *************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/s3/object/move"):
            return self._invoke_s3_move_objects()
        # *******************************  COPY OBJECTS IN S3 *************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/s3/object/copy"):
            return self._invoke_s3_copy_objects()
        # *******************************  RENAME OBJECTS IN S3 *************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/infrastructure/s3/object/rename"):
            return self._invoke_s3_rename_object()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method"
        )
        return create_error_response("No correct infrastructure method was chosen")
