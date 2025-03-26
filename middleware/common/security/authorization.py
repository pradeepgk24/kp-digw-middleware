import re

from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.metadatabase.objects_metadata_provider import ObjectsMetadataProvider
from middleware.common.metadatabase.permissions_metadata_provider import PermissionMetadataProvider


class Authorization:
    """
    General authorization page
    """

    SUBJECT_TYPE_KEY = "subjectType"
    SUBJECT_ID_KEY = "subjectId"
    SUBJECT_DISPLAY_NAME_KEY = "displayName"

    # higher order mean higher priority
    SUBJECT_HIERARCHY = [
        SubjectTypesEnum.project,  # priority 2 - SUBJECT_PROJECT permission take precedence over
        # SUBJECT_OBJECTS_ACL permission
        SubjectTypesEnum.group,  # priority 3 - SUBJECT_GROUP permission take precedence over
        # SUBJECT_PROJECT permission
        SubjectTypesEnum.user  # priority 4 - SUBJECT_USER permission take precedence over
        # SUBJECT_GROUP permission
    ]

    def __init__(self, logger, metadatabase_connection, lambda_secrets_manager):
        self.logger = logger
        self.lambda_secrets_manager = lambda_secrets_manager
        self.metadatabase_connection = metadatabase_connection
        self.permission_metadata_provider = PermissionMetadataProvider(logger, metadatabase_connection,
            lambda_secrets_manager)
        self._objects_metadata_provider = None

    @property
    def objects_metadata_provider(self):
        """
        objects_metadata_provider property
        """
        if self._objects_metadata_provider is None:
            self._objects_metadata_provider = ObjectsMetadataProvider(
                self.logger,
                self.metadatabase_connection,
                self.lambda_secrets_manager
            )

        return self._objects_metadata_provider
    @staticmethod
    def check_and_get_regex(value):
        """
        Check if the value is the regular expression

        :param value: regular expression
        :return: Match object from re library if value is regex otherwise return None
        """
        try:
            if not re.compile(r"[A-Za-z0-9-_]+").fullmatch(value):
                return re.compile(value)
        except re.error:
            pass
        return None

    def evaluate_effect_hierarchy(self, evaluated_effects):
        """

        :param evaluated_effects:
        :return:
        """
        self.logger.info(f"Going to evaluated the following results/effect "
                         f"from {evaluated_effects} based on subject hierarchy")
        # default is deny
        result_effect = PermissionEffectsEnum.deny
        for subject_type in Authorization.SUBJECT_HIERARCHY:
            if subject_type in evaluated_effects:
                result_effect = evaluated_effects[subject_type]
        return result_effect