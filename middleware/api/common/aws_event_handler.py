from abc import abstractmethod
from math import ceil
import redis

from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.security.authorization_validator import AuthorizationValidator
from middleware.common.security.authorization import Authorization
from middleware.api.common.helpers import get_env_or_header_value, SortAndPaginate, get_redis_key
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.common.helpers.exception import AuthTokenError, BadRequest
from common.secrets.secrets_manger import SecretsManager


# pylint: disable=too-many-instance-attributes
class AWSLambdaEventHandler:
    """
    Abstract class for the aws lambda events
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager: SecretsManager):
        self.project_id = None
        self.logger = logger
        self.event = event
        self.context = context
        self.lambda_secrets_manager = lambda_secrets_manager
        self.redis_client = self.return_redis_client()
        self._auth_validator = None
        self.user_isid = None
        self.assigned_group_ids = None
        self.display_name = None
        self.selected_subjects = None
        # list of subjects which the which login subject  is representing
        self.framework_version = self.event.headers.get("difw-core-version")
        self.set_and_check_subjects()

    def should_check_token_groups(self) -> bool:
        """
        Check if we are using calls which should not require checking of validity of tokens
        the following endpoints does not require check
        - /infrastructure/token         - for obtaining tokens
        - /logging                      - for logging
        - /infrastructure/email/send    - for sending onboarding request email
        - /infrastructure/projects      - for obtaining projects, groups and onboard information
        """
        return any(
            self.event.resource.endswith(endpoint)
            for endpoint in [
                "/infrastructure/token",
                "/logging",
                "/infrastructure/email/send",
                "/infrastructure/projects",
                "/errorhandler",
            ]
        )

    def set_selected_subjects(self):
        """
        Replace the user isid in the selected subject, this needs to be called everywhere except token API
        """
        self.selected_subjects = self.create_subjects_object_from_pair(
            self.replace_user_in_selected_subjects(self.event.headers["subjects"].split(","))
        )

    def check_valid_access_token(self):
        """
        Check the access token validity, access token is taken from the HTTP header access_token

        The steps would be to check the Redis with the key equal to the access token. This check should be
        done for all API calls except the /infrastructure/token call

        Also set the user_isid from the redis record
        """
        access_token = self.event.headers.get("authtoken")
        if not access_token:
            raise AuthTokenError("Access token is missing in the header")
        redis_access_token = get_redis_key(key=access_token, redis_client=self.redis_client)
        if not redis_access_token:
            raise AuthTokenError("Access token is not valid")

        self.user_isid = redis_access_token["isid"]
        self.display_name = redis_access_token["given_name"] + " " + redis_access_token["family_name"]
        self.assigned_group_ids = redis_access_token["securityGroups"]

    @property
    def auth_validator(self):
        """
        get auth validator
        """
        if self._auth_validator is None:
            self._auth_validator = AuthorizationValidator(
                self.logger,
                get_env_or_header_value(
                    event=self.event,
                    env_name="METADATA_CONNECTION",
                    header_name="metadata-connection",
                    logger=self.logger,
                ),
                self.lambda_secrets_manager,
                self.user_isid,
                self.selected_subjects,
            )
        return self._auth_validator

    def return_redis_client(self):
        """
        Set the redis client to be used for the validation of the token
        """
        redis_credentials = get_env_or_header_value(
            event=self.event, env_name="REDIS_CONNECTION", header_name="redis-connection", logger=self.logger
        )
        redis_connection = self.lambda_secrets_manager.get_secret_string_data(redis_credentials)
        if redis_connection is None:
            raise Exception(f"There is no SM with name {redis_connection} with Redis credentials")
        self.logger.info(
            f"Going to connect to Redis using following connection:"
            f"Host: {redis_connection['host']}"
            f"Port: {redis_connection['port']}"
        )

        return redis.StrictRedis(
            host=redis_connection["host"],
            port=redis_connection["port"],
            db=0,
            ssl=True,
            username=redis_connection["user"],
            password=redis_connection["password"],
        )

    def check_selected_subjects(self):
        """
        Check if there are all mandatory subjects in selected subjects
        """
        self.logger.info("Checking selected subjects ......")
        # check if group and project are present in token
        project_subject_is_present = False
        group_subject_is_present = False
        for subject in self.selected_subjects:
            project_subject_is_present = project_subject_is_present or subject.subject_type == SubjectTypesEnum.project
            group_subject_is_present = group_subject_is_present or subject.subject_type == SubjectTypesEnum.group

        if not project_subject_is_present:
            raise BadRequest("Your project identifier is missing. Please check 'subject' header in API")

        if not group_subject_is_present:
            raise BadRequest("Your group identifier is missing. Please check 'subject' header in API")

    def set_and_check_subjects(self):
        """
        Check and set the subjects
        """
        if not self.should_check_token_groups():
            self.check_valid_access_token()
            self.set_selected_subjects()
            self.auth_validator.check_rights_of_user_against_subjects(self.assigned_group_ids)
            self.check_selected_subjects()
            project = EntitySubject.filter_subjects_by_type(
                SubjectTypesEnum.project, self.selected_subjects, uselist=False
            )
            self.project_id = project.subject_id if project is not None else None

    # pylint: disable=no-member
    def run_lambda(self):
        """
        Invoke the lambda function

        :return:
        """
        self.logger.info(
            "Invoking with following event attributes:\n"
            f"Method:{self.event.http_method}\n"
            f"Resource:{self.event.resource}\n"
            f"Path:{self.event.path}\n"
            f"Path parameters:{self.event.path_parameters}\n"
            f"Query parameters:{self.event.query_string_parameters}\n"
        )
        response = self.invoke()
        # TODO - https://issues.merck.com/browse/NGA-3514 place holder for clearing cache
        self.logger.debug(f"The following response is going to be return:\n {response}")
        return response

    @staticmethod
    def create_subjects_object_from_pair(subject_pairs):
        """
        Create subject list from request query parameter "subjects"

        :param subject_pairs: query parameters. subject_pairs in form "subjectType,subjectId"
        :return:
        """
        subjects = []
        for subject in subject_pairs:
            subject_attrs = subject.split(":")
            subjects.append(EntitySubject(subject_attrs[1], SubjectTypesEnum.from_str(subject_attrs[0])))
        return subjects

    @staticmethod
    def create_subjects_object(body):
        """
        Create subject list from request body

        :param body:
        :return:
        """
        subjects = []
        for subject in body.get("subjects", []):
            subjects.append(
                EntitySubject(
                    subject[Authorization.SUBJECT_ID_KEY],
                    SubjectTypesEnum.from_str(subject[Authorization.SUBJECT_TYPE_KEY]),
                    subject.get(Authorization.SUBJECT_DISPLAY_NAME_KEY),
                )
            )
        return subjects

    @abstractmethod
    def invoke(self):
        """
        invoke function specific logic here
        :return:
        """

    # pylint: disable=cell-var-from-loop
    def create_list_response(self, items: list, sort_and_paginate: SortAndPaginate, total_count: int):
        """
        :param items:
        :param sort_and_paginate:
        :param total_count:
        :return:
        """
        page_size = sort_and_paginate.page_size
        page_number = sort_and_paginate.page_number
        page_count = ceil(total_count / page_size)
        self.logger.info(
            f"Item response page information: totalCount={total_count},"
            f" page_count={page_count},page_size={page_size}"
        )
        return {
            "items": items,
            "totalCount": total_count,
            "pageNumber": page_number,
            "pageCount": page_count,
            "pageSize": page_size,
        }

    def replace_user_in_selected_subjects(self, list_of_subjects: list):
        """
        Function to replace user from subjects header with self.user_isid value
        :param list_of_subjects:
        :return: corrected list of subjects
        """
        list_of_subjects_corrected = []
        for sub in list_of_subjects:
            if sub.startswith(SubjectTypesEnum.user.value):
                sub = sub.split(":")[0] + ":" + self.user_isid
            list_of_subjects_corrected.append(sub)
        return list_of_subjects_corrected