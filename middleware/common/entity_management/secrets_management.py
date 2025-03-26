import json
from middleware.common.entity_management.entities.entity_secret import EntitySecret
from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.entity_management.entity_management import EntityManagement
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.metadatabase.model.types.secrets_acl_relation_types_enum import SecretsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.metadatabase.secrets_metadata_provider import SecretsMetadataProvider
from middleware.common.security.action_type import ActionType
from middleware.common.helpers.exception import AuthorizationError, NoDataError, EntityConflictError
from middleware.api.common.helpers import paginate_entries, SortAndPaginate
from common.secrets.secrets_manger import SecretsManager


# pylint: disable=too-many-instance-attributes
class SecretsManagement(EntityManagement):
    """
    Secrets management
    """

    # pylint: disable=duplicate-code
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._secret_manager = None
        self._secrets_metadata_provider = None
        self._aws_region = None
        if kwargs.get('project_id'):
            self.project_id = kwargs.get('project_id')

    # pylint: disable=import-outside-toplevel,cyclic-import
    @property
    def aws_region(self):
        """
        Property aws_region - which needs to be passed in as part of secret manager
        """
        if self._aws_region is None:
            # local import to get around the circular import, however still get raised in pylint
            from middleware.common.entity_management.project_settings_management import ProjectSettingsManagement
            self._aws_region = ProjectSettingsManagement(
                logger=self.logger,
                metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
                selected_subjects=self.selected_subjects,
                project_id=self.project_id
            ).get_aws_region()
        return self._aws_region

    @property
    def secrets_metadata_provider(self):
        """
        Secret metadata provider property
        """
        if self._secrets_metadata_provider is None:
            self._secrets_metadata_provider = SecretsMetadataProvider(self.logger, self.metadatabase_connection,
                                                                      self.lambda_secrets_manager)
        return self._secrets_metadata_provider

    @property
    def secret_manager(self):
        """
        Secret manager property
        """
        if self._secret_manager is None:
            self._secret_manager = SecretsManager(region_name=self.aws_region,
                                                  access_key_id=self.aws_access_key,
                                                  secret_access_key=self.aws_secret_key,
                                                  aws_session_token=self.aws_session_token)
        return self._secret_manager

    def create_secret(self, secret: EntitySecret, check_permission=True, do_not_raise_entity_conflict_if_exists=True):
        """
        Creates  secrets in AWS secret manager and Metadata Database if they do not exist.

        @param secret: secret to create
        @param check_permission: Flag indicates whether check permissions or not
        @param do_not_raise_entity_conflict_if_exists: Flag indicates whether skip creation on aws SM if exists,
         default is True, it is possible to rewrite recently deleted SM
        @return:
        """
        secret_name = secret.secret_name
        self.logger.info(f"Going to generate aws secret manager name for secret - {secret_name}")
        # Validate create secret permission
        self.logger.info(f"Going to validate create secret permission for user {self.user_isid}")
        if check_permission and self.auth_validator.validate(
                ActionType.CREATE_SECRET, {}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"The user {self.user_isid} does not have create access to secret - {secret_name}")
        # Generate AWS Secret manager name
        secret_manager_name = secret_name if \
            secret.secret_manager_name is None else secret.secret_manager_name
        self.logger.info(
            f"Generated secret manager name is {secret_manager_name}")
        # Check if secrets already exist in either AWS secret manager or  MetaDB
        self.logger.info(
            f"Going to verify secrets existence for secret {secret_name} in AWS secrets manager and Metadata DB")
        secret_in_meta_db = self.secrets_metadata_provider.get_secret(secret_name, self.user_isid)
        if secret_in_meta_db:
            self.logger.warning(f"The secrets with name {secret_name} already exists in MetaDB")
            raise EntityConflictError(f"The secrets with name {secret_name} already exists in MetaDB")
        secret_in_aws_sm = self.secret_manager.describe_secrets(secret_manager_name)
        if secret_in_aws_sm:
            self.logger.warning(f"The AWS SM with name {secret_manager_name} already exists and "
                                f"was recently deleted - {bool(secret_in_aws_sm.get('DeletedDate', None))}")
            if do_not_raise_entity_conflict_if_exists:
                if secret_in_aws_sm.get('DeletedDate', None):
                    # restore if its going to be deleted
                    self.secret_manager.restore_secret(secret_manager_name)
                if secret.items:
                    # update in case there are items
                    self.logger.info(f"Going to update items for secret {secret_name}")
                    self.secret_manager.update_secret(secret_manager_name, json.dumps(secret.items))
            else:
                raise EntityConflictError(f"The AWS SM with name {secret_manager_name} already exists")

        # Create and store secrets in AWS Secrets Manager
        if not secret_in_aws_sm:
            self.logger.info("Going to create secrets in AWS secrets manager and MetadataDB")
            self.secret_manager.create_secrets(secret_manager_name, json.dumps(secret.items))

        # Store secrets details to MetaDB
        # add owners
        secret.add_acl(EntitySubject(subject_id=self.project_id, subject_type=SubjectTypesEnum.project),
                       SecretsACLRelationTypesEnum.owner)
        secret.add_acl(EntitySubject(subject_id=self.user_isid, subject_type=SubjectTypesEnum.user),
                       SecretsACLRelationTypesEnum.owner)
        secret.secret_manager_name = secret_manager_name
        # insert it into DB
        return EntitySecret.from_metadb_object(
            self.secrets_metadata_provider.insert_secret(secret.to_metadb_object(), self.user_isid))

    def get_secret(self, secret_name, get_values, check_permission=True, raise_no_data_error=True):
        """
        Gets the secret details.

        @param secret_name:
        @param get_values
        @param check_permission: flag indicates if permission should be checked
        @param raise_no_data_error: flag indicates if raise no data error if there is no secret
        @return:
        """
        # Get secrets from DB.
        self.logger.info(
            f"Going to get the secrets details for secret {secret_name} from Metadata DB, "
            f"with flag get_values={get_values}")

        db_secret = self.secrets_metadata_provider.get_secret(secret_name, self.user_isid)
        if not db_secret:
            if raise_no_data_error:
                raise NoDataError(f"The secret with name {secret_name} does not exists")
            return None
        entity_secret = EntitySecret.from_metadb_object(db_secret)
        # Validate if the user has read secret Permission
        self.logger.info(f"Going to validate read secret permissions on {secret_name} for user {self.user_isid}")
        if check_permission and self.auth_validator.validate(
                ActionType.READ_SECRET,
                {"secretName": secret_name},
                acl_relation_list=entity_secret.acl) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"The user {self.user_isid} does not have access to read secret - {secret_name}")
        if not self.secret_manager.get_secret(entity_secret.secret_manager_name):
            if raise_no_data_error:
                raise NoDataError(f"The secret with name {secret_name} exists but associated secret manager with name "
                                  f"{entity_secret.secret_manager_name} does not exists. "
                                  f"Please contact administrator of project AWS account")
            return None
        # if not check permission, then user can see the values by default and no need to validate read secret items
        if not check_permission:
            can_see_values = True
        else:
            # check if user has read secret items permissions assigned, if he has them assigned only
            # then the secret values will be visible
            can_see_values = self.auth_validator.validate(
                ActionType.READ_SECRET_ITEMS,
                {"secretName": secret_name},
                acl_relation_list=entity_secret.acl) == PermissionEffectsEnum.allow
        for secret_item_key, secret_item_value in self.secret_manager.get_secret_string_data(
                entity_secret.secret_manager_name).items():
            if get_values and not can_see_values:
                secret_item_value = 'No permission to read secret items'
            elif not get_values:
                secret_item_value = "***********"
            entity_secret.items[secret_item_key] = secret_item_value
        return entity_secret

    def get_secrets(self, secret_name: str = None, sort_and_paginate: SortAndPaginate = None, check_permission=True,
                    raise_no_data_error=True):
        """
        Gets the secrets and gets the pagination, it is necessary to do it here, since there because of the checking of
        readSecret permissions we may filter additional entries from the query and as such, the pagination is needed to
        do afterwards
        @param secret_name: optional, filtering on substring of secrets
        @param sort_and_paginate:
        @param check_permission: flag indicates if permission should be checked
        @param raise_no_data_error: flag indicates if raise no data error if there is no secret
        @return:
        """
        # Get secrets from DB.
        self.logger.info(
            f"Going to get the secrets for project {self.project_id} from Metadata DB")
        entity_secrets = EntitySecret.from_metadb_objects(
            self.secrets_metadata_provider.get_secrets(self.user_isid, self.project_id, secret_name,
                                                       sort_and_paginate))
        # Validate if the user has read secret Permission
        self.logger.info(f"Going to validate read secret permissions on obtained secrets for user {self.user_isid}")
        secrets_list = []
        for secret in entity_secrets:
            if check_permission and self.auth_validator.validate(
                    ActionType.READ_SECRET,
                    {"secretName": secret.secret_name},
                    acl_relation_list=secret.acl) == PermissionEffectsEnum.deny:
                continue
            secrets_list.append(secret)
        total_count = len(secrets_list)
        secrets_list = [ct.to_json_dict() for ct in secrets_list]
        secrets_list = paginate_entries(secrets_list, sort_and_paginate)
        if not secrets_list and raise_no_data_error:
            raise NoDataError("Secrets not found")
        return secrets_list, total_count

    def update_secret(self, secret: EntitySecret, check_permission=True):
        """
        Update secret in AWS secret manager and Metadata Database if it does not exist.
        We load secret from DB based on secret.secret_name given, we can not overwrite it, since we would lose
        the items for update
        @param secret: secret to create
        @param check_permission: Flag indicates whether check permissions or not
        @return:
        """
        secret_name = secret.secret_name
        self.logger.info(f"Going to retrieve secret with {secret_name} from DB")
        secret_from_db = EntitySecret.from_metadb_object(
            self.secrets_metadata_provider.get_secret(secret_name, self.user_isid))
        if not secret_from_db:
            raise NoDataError(f"The secret with name {secret_name} does not exists")
        # Validate update secret permission
        self.logger.info(f"Going to validate update secret permission for user {self.user_isid}")
        if check_permission and self.auth_validator.validate(
                ActionType.UPDATE_SECRET,
                {"secretName": secret_from_db.secret_name},
                acl_relation_list=secret_from_db.acl) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} "
                f"has no permission to update secret with name {secret_name}")
        # if user wants to change description in DB
        if secret.description:
            secret_from_db.description = secret.description

        # if user wants to change AWS SM in DB.
        if secret.secret_manager_name:
            secret_from_db.secret_manager_name = secret.secret_manager_name
            # in case if user wants to update/change the aws secret manager then we are aiming to create new secret with
            # the given new name and the old secret inb AWS SM will not be disturbed.
            secret_manager_name = secret.secret_manager_name
        else:
            secret_manager_name = secret_from_db.secret_manager_name

        self.secrets_metadata_provider.update_secret(secret_from_db.to_metadb_object(), self.user_isid)
        # Check if secrets already exist in either AWS secret manager or  MetaDB
        self.logger.info(
            f"Going to verify secrets existence for secret {secret_name} in AWS secrets manager")
        secret_in_aws_sm = self.secret_manager.describe_secrets(secret_manager_name)
        # if user wanted to only change description - secret.items is None, we should not rewrite exisitng entries
        if secret_in_aws_sm and secret.items:
            self.logger.info(f"The AWS SM with name {secret_manager_name} exists, will proceed to"
                             f" update the secrets")
            self.secret_manager.update_secret(secret_manager_name, json.dumps(secret.items))
        # Create and store secrets in AWS Secrets Manager
        elif not secret_in_aws_sm:
            self.logger.info("Going to create and save secrets in AWS secrets manager")
            self.secret_manager.create_secrets(secret_manager_name, json.dumps(secret.items))
        return secret_name

    def delete_secret(self, secret_name: str, check_permission: bool = True, delete_secret_manager: bool = False):
        """
        Delete secret in AWS secret manager and Metadata Database if it exists.

        @param secret_name: secret to create
        @param check_permission:
        @param delete_secret_manager:
        @return:
        """
        self.logger.info(f"Going to retrieve secret with {secret_name} from DB")
        secret = self.secrets_metadata_provider.get_secret(secret_name, self.user_isid)
        secret_from_db = EntitySecret.from_metadb_object(secret)
        if secret_from_db is None:
            raise NoDataError(f"Secret with name {secret_name} not found")
        # Validate update secret permission
        self.logger.info(f"Going to validate update secret permission for user {self.user_isid}")
        if check_permission and self.auth_validator.validate(
                ActionType.DELETE_SECRET,
                {"secretName": secret_from_db.secret_name},
                acl_relation_list=secret_from_db.acl) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id}"
                f" has no permission to delete secret with name {secret_name}")

        # Check if secrets already exist in either AWS secret manager or  MetaDB
        self.logger.info(
            f"Going to verify secrets existence for secret {secret_name} in AWS secrets manager and Metadata DB")
        secret_manager_name = secret_from_db.secret_manager_name
        # check the existence of secret in AWS secret manager only if delete secret manager flag is set to true
        if delete_secret_manager:
            secret_in_aws_sm = self.secret_manager.describe_secrets(secret_manager_name)
            if secret_in_aws_sm:
                self.logger.warning(f"The AWS SM with name {secret_manager_name} exists, will proceed with "
                                    f"deletion of the secret in AWS")
                self.secret_manager.delete_secret(secret_manager_name)
        # Deleting in database
        self.logger.info(f"Going to delete secret with name {secret_name} in DB")
        return self.secrets_metadata_provider.delete_secret(secret, self.user_isid)

    def get_secret_by_sm_name(self, secret_manager_name):
        """
        Get secret by secret manager name
        @param secret_manager_name: name of secret manager name
        @return: EntitySecret object
        """
        self.logger.info(
            f"Going to get the secrets details for secret_manager_name= {secret_manager_name} from Metadata DB")
        return EntitySecret.from_metadb_objects(
            self.secrets_metadata_provider.get_secret_by_sm_name(secret_manager_name, self.user_isid)
        )

    def check_secret_existence(self, secret_name: str) -> bool:
        """
        Check secret existence, return True if secret does exist, else raises NoDataError

        @param secret_name: name of secret
        """
        self.logger.info(f"User {self.user_isid} starts method check_secret_existence"
                         f" with pipeline_name={secret_name}")
        exists = self.secrets_metadata_provider.exists_secret(secret_name, self.user_isid)
        if not exists:
            raise NoDataError(f"Secret with name {secret_name} does not exist")
        return True
