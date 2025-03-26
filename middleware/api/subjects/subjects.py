import json
from middleware.api.common.http_method_utils import create_error_response
from middleware.api.common.helpers import get_env_or_header_value, SortAndPaginate, convert_to_bool
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.common.entity_management.subjects_management import SubjectManagement
from middleware.common.entity_management.entities.entity_subject import EntitySubject, SubjectTypesEnum
from middleware.common.helpers.exception import BadRequest


class SubjectsLambda(AWSLambdaEventHandler):
    """
    Lambda class for Subjects API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.subject_management = SubjectManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects, api_connection=get_env_or_header_value(
                event=self.event, env_name='MSD_INTERNAL_API_SECRET', header_name='msd-api-connection',
                logger=self.logger))

    def check_selected_subjects(self):
        """
        ignore subjects check for user availability call
        :return:
        """
        if self.event.http_method == "GET" and self.event.resource.endswith("/subjects/useravailability"):
            self.logger.warning("Checking of subjects header skip for user availability call")
        else:
            super().check_selected_subjects()

    def _invoke_check_user_availability(self):
        """
        Invoke method call user availability

        :return: API response of user availability
        """
        self.logger.info("Calling _invoke_check_user_availability")
        assigned_projects = self.subject_management.check_user_availability(
            self.assigned_group_ids,
            self.user_isid,
            self.display_name)
        return {'statusCode': 200, 'body': json.dumps(assigned_projects)}

    def _invoke_insert_subject(self):
        """
        Invoke method call insert subject.
        Currently, we can insert only subjects of type group only.

        :return: API response of insert subject
        """
        self.logger.info("Calling _invoke_insert_subject")
        # check if the subject that needs to be inserted is of type group, if the type is not group raise an error
        if self.event.json_body['subjectType'] != SubjectTypesEnum.group.value:
            raise BadRequest("Only allowed subject type to add is group")
        subject = EntitySubject(subject_type=self.event.json_body['subjectType'],
                                subject_id=self.event.json_body['subjectId']
                                )
        self.subject_management.insert_subject(subject)
        return {'statusCode': 201, 'body': json.dumps({"result": "created",
                                                       "details": f"Subject with id {subject.subject_id} was created"})}

    def _invoke_delete_subject(self):
        """
        Invoke method call delete subject
        Currently, we can delete only subjects of type group only.

        :return: API response of delete subject
        """
        self.logger.info("Calling _invoke_delete_subject")
        subject = self.subject_management.get_subject(self.event.path_parameters['subjectId'])
        if subject.subject_type != SubjectTypesEnum.group:
            raise BadRequest("Only allowed subject type to delete is group")
        self.subject_management.delete_subject(self.event.path_parameters['subjectId'])
        return {'statusCode': 200, 'body': json.dumps({"result": "deleted",
                                                       "details": f"Subject with "
                                                                  f"id {self.event.path_parameters['subjectId']} was "
                                                                  f"deleted"})}

    def _invoke_enable_or_disable_subject(self):
        """
        Invoke method call patch(enable/disable) subject

        :return: API response of partial update of subject
        """
        self.logger.info("Calling _invoke_enable_or_disable_subject")
        enable_or_disable_flag = 'enabled' if convert_to_bool(self.event.json_body['isEnabled']) else 'disabled'
        self.subject_management.enable_or_disable_subject(self.event.path_parameters['subjectId'],
                                                          convert_to_bool(self.event.json_body['isEnabled']))
        return {'statusCode': 200, 'body': json.dumps({"result": f"subject {enable_or_disable_flag}",
                                                       "details": f"Subject with id "
                                                                  f"{self.event.path_parameters['subjectId']} "
                                                                  f"was {enable_or_disable_flag}"})}

    def _invoke_get_subjects(self):
        """
        Invoke method call get subjects...

        :return: API response of get subjects
        """
        self.logger.info("Calling _invoke_get_subjects")
        subject_type = self.event.query_string_parameters.get('subjectType', None)
        sort_and_paginate = SortAndPaginate(self.event.query_string_parameters)
        subject_type = SubjectTypesEnum.project if subject_type == "project" else SubjectTypesEnum.group \
            if subject_type == "group" else SubjectTypesEnum.user if subject_type == "user" else None

        subjects, total_count = self.subject_management.get_subjects(
            subject_type=subject_type,
            get_children=convert_to_bool(self.event.query_string_parameters.get('getChildren', False)),
            enabled=self.event.query_string_parameters.get('isEnabled', None),
            display_name=self.event.query_string_parameters.get('displayName', None),
            sort_and_paginate=sort_and_paginate,
            parent_subject_id=self.event.query_string_parameters.get('parentSubjectId', None)
        )
        return {'statusCode': 200, 'body': json.dumps(
            self.create_list_response(subjects, sort_and_paginate, total_count))}

    def _invoke_get_subject(self):
        """
        Invoke method call get subject

        :return: API response of get subject
        """
        self.logger.info("Calling _invoke_get_permissions")
        response = self.subject_management.get_subject(self.event.path_parameters['subjectId'],
                                                       convert_to_bool(
                                                           self.event.query_string_parameters.get('getChildren',
                                                                                                  False)),
                                                       convert_to_bool(
                                                           self.event.query_string_parameters.get('getParents',
                                                                                                  False))
                                                       )
        return {'statusCode': 200, 'body': json.dumps(response.to_json_dict())}

    # pylint: disable=too-many-return-statements
    def invoke(self):
        """
        Invoke lambda function logic

        :return:
        """
        # ******************************** CHECK USER AVAILABILITY CALL *********************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/subjects/useravailability"):
            return self._invoke_check_user_availability()
        # *******************************  INSERT  SUBJECT CALL   ***************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/subjects"):
            return self._invoke_insert_subject()
        # ******************************* DELETE SUBJECT CALL *******************************************************
        if self.event.http_method == "DELETE" and self.event.resource.endswith("/subjects/{subjectId}"):
            return self._invoke_delete_subject()
        # ****************************** ENABLE OR DISABLE SUBJECT CALL *********************************************
        if self.event.http_method == "PATCH" and self.event.resource.endswith("/subjects/{subjectId}"):
            return self._invoke_enable_or_disable_subject()
        # ****************************** GET SUBJECTS CALL **********************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/subjects"):
            return self._invoke_get_subjects()
        # ****************************** GET SUBJECT CALL ***********************************************************
        if self.event.http_method == "GET" and self.event.resource.endswith("/subjects/{subjectId}"):
            return self._invoke_get_subject()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct subjects method was chosen")
