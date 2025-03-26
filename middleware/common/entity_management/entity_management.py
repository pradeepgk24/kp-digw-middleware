from abc import ABCMeta

from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.metadatabase.model.types.component_templates_acl_relation_types_enum import \
    ComponentTemplatesACLRelationTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.security.authorization_validator import AuthorizationValidator
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.entity_management.entities.entity_acl import EntityACL


class EntityManagement(metaclass=ABCMeta):
    """
    Main entity management class
    """

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=duplicate-code
    def __init__(self, *args, **kwargs):
        self.logger = kwargs['logger']
        self.lambda_secrets_manager = kwargs['lambda_secrets_manager']
        self.user_isid = kwargs['user_isid']
        self.selected_subjects = kwargs.get('selected_subjects')
        self.metadatabase_connection = kwargs['metadatabase_connection']
        self.aws_access_key = kwargs.get('aws_access_key')
        self.aws_secret_key = kwargs.get('aws_secret_key')
        self.aws_session_token = kwargs.get('aws_session_token')
        self._auth_validator = None
        self.entity_project = EntitySubject.filter_subjects_by_type(SubjectTypesEnum.project, self.selected_subjects,
                                                                    uselist=False)
        self.project_id = self.entity_project.subject_id if self.entity_project is not None else None
        group = EntitySubject.filter_subjects_by_type(SubjectTypesEnum.group, self.selected_subjects, uselist=False)
        self.group_id = group.subject_id if group is not None else None

        if self.selected_subjects:
            self.selected_subject_ids = [subject.subject_id for subject in self.selected_subjects]

    def create_objects_owner_acls(self):
        """
        Create acl owners for objects. Owner is always the project and the user

        :return: list of owners
        """
        return [
            EntityACL(EntitySubject(subject_id=self.user_isid, subject_type=SubjectTypesEnum.user),
                      ObjectsACLRelationTypesEnum.owner),
            EntityACL(EntitySubject(subject_id=self.project_id, subject_type=SubjectTypesEnum.project),
                      ObjectsACLRelationTypesEnum.owner)
        ]

    def create_component_templates_owner_acls(self):
        """
        Create acl owners for objects. Owner is always the project and the user

        :return: list of owners
        """
        return [
            EntityACL(EntitySubject(subject_id=self.user_isid, subject_type=SubjectTypesEnum.user),
                      ComponentTemplatesACLRelationTypesEnum.owner),
            EntityACL(EntitySubject(subject_id=self.project_id, subject_type=SubjectTypesEnum.project),
                      ComponentTemplatesACLRelationTypesEnum.owner)
        ]

    def refresh_aws_tokens(self, project_settings_management):
        """
        Refresh AWS tokens
        """
        aws_access_key, aws_secret_key, aws_session_token = \
            project_settings_management.get_project_aws_account_access_info()
        self.set_aws_tokens(aws_access_key, aws_secret_key, aws_session_token)

    @property
    def auth_validator(self):
        """
        Auth validator property
        """
        if self._auth_validator is None:
            self._auth_validator = AuthorizationValidator(self.logger, self.metadatabase_connection,
                                                          self.lambda_secrets_manager, self.user_isid,
                                                          self.selected_subjects)
        return self._auth_validator

    def set_aws_tokens(self, aws_access_key, aws_secret_key, aws_session_token):
        """
        Set aws tokens

        @param aws_access_key: aws access key
        @param aws_secret_key: aws secret key
        @param aws_session_token: aws session key
        """
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_session_token = aws_session_token
