import os

from middleware.api.common.helpers import SortAndPaginate
from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.metadatabase.subjects_metadata_provider import SubjectsMetadataProvider
from middleware.common.metadatabase.model.difw_metadb_model import Subjects, SubjectTypesEnum
from middleware.common.helpers.exception import EntityConflictError, NoDataError, EntityDisabledError, \
    AuthorizationError
from middleware.common.entity_management.entity_management import EntityManagement
from middleware.common.api_clients.msd_api.msd_api_client import MSDApiClient
from middleware.common.security.action_type import ActionType
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum


class SubjectManagement(EntityManagement):
    """
    Subject management

    """

    # pylint: disable=too-many-arguments
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._api_connection = kwargs.get('api_connection')
        self._auth_validator = None
        self._auth_management = None
        self._subjects_metadata_provider = None

    @property
    def subjects_metadata_provider(self):
        """
        subjects metadata provider property
        """
        if self._subjects_metadata_provider is None:
            self._subjects_metadata_provider = SubjectsMetadataProvider(self.logger,
                                                                        self.metadatabase_connection,
                                                                        self.lambda_secrets_manager)
        return self._subjects_metadata_provider

    # pylint: disable=too-many-branches,too-many-locals
    def check_user_availability(self, assigned_group_ids, login_user_isid, display_name):
        """
        Check uf login user is assigned in group which is onboard in DIFW UI

        param assigned_group_ids:
        param login_user_isid:
        param display_name:

        :return: tuple (the list of project where user belongs to, additional message). If the list is empty, it means
        that user is not part of any group and project
        """
        # check if session login user is present in SUBJECTS entity and is enabled in MetaDB
        user = EntitySubject.from_metadb_object(
            self.subjects_metadata_provider.get_subject(login_user_isid, login_user_isid))
        # check if user exists and is enabled in MetaDB.
        if user and not user.is_enabled:
            raise EntityDisabledError(
                f"the {user.subject_type} with id {login_user_isid} is disabled.Please contact administrator")

        enabled_groups = []
        groups = EntitySubject.from_metadb_objects(
            self.subjects_metadata_provider.get_subjects_by_subject_ids(assigned_group_ids, login_user_isid))
        # filter out the disabled group
        for group in groups:
            if group.is_enabled:
                enabled_groups.append(group)
        # if no groups are left after filtering disabled groups, raise error.
        if not enabled_groups:
            raise NoDataError(f"user {login_user_isid} is not part of any enabled groups")

        project_groups = {}
        listed_groups = set()
        # if login user is there, then first remove all hierarchies. So, that we can sync-up the hierarchies with AD
        if user:
            # remove all child subject hierarchies
            self.subjects_metadata_provider.delete_subject_child_from_hierarchy(login_user_isid)
        # for each group check the project where the group belongs to
        for group in enabled_groups:
            # get all parents of group. The parent of group are Projects
            group_parents = EntitySubject.from_metadb_objects(
                self.subjects_metadata_provider.get_subject_parents_in_hierarchy(group.subject_id, login_user_isid))
            for project in group_parents:
                # filter disabled projects if any
                if project.is_enabled:
                    # append the groups that are listed in some projects in the Meta DB.
                    listed_groups.add(group)
                    if project.subject_id in project_groups:
                        project_groups[project.subject_id].append(group.subject_id)
                    else:
                        project_groups[project.subject_id] = [group.subject_id]
        # check if at least any group is onboarded in some project
        if not project_groups or not groups:
            # return only empty list with info that on-boarding process is needed
            raise NoDataError(f"the user {login_user_isid} does not belong to any on boarded groups/projects")

        # if login user is not there, then add it into DB
        if not user:
            # insert user
            try:
                subject_to_be_inserted = Subjects(SUBJECT_ID=login_user_isid, SUBJECT_TYPE=SubjectTypesEnum.user,
                                                  DISPLAY_NAME=display_name,
                                                  DESCRIPTION='', IS_ENABLED=True)
                EntitySubject.from_metadb_object(
                    self.subjects_metadata_provider.insert_subject(subject_to_be_inserted,
                                                                   self.user_isid))
            except EntityConflictError:
                return f"the user {login_user_isid} has been deactivated by Admin"
        # insert user into hierarchy under only the listed groups
        self.subjects_metadata_provider.insert_subject_hierarchy(login_user_isid, list(listed_groups)
                                                                 )
        result_object = []
        for projects in project_groups:
            result_object.append({
                "projectId": projects,
                "groups": project_groups[projects]
            })
        # return list of projects where user is on-board together with the groups belonging to project
        # and user is assigned there
        return {"projects": result_object}

    def get_subject(self, subject_id: str, get_children: bool = False, get_parents: bool = False):
        """
        Get the details of the given subject_id.

        param subject_id:
        param get_children, if set to true will retrieve the whole children in hierarchy recursively.
        param get_parents, if set to true will retrieve the subject parents for a given subject id.
        """

        self.logger.info(f" user {self.user_isid} is going to get details of subject {subject_id} ")
        subject_details = EntitySubject.from_metadb_object(
            self.subjects_metadata_provider.get_subject(self.user_isid, subject_id))

        # raise error if the subject does not  exist in DB.
        if not subject_details:
            raise NoDataError(f"Subject with id {subject_id} does not exist")

        # if flag set to True then get whole children hierarchy recursively for given subject.
        if get_children:
            self.get_children_recursively([subject_details], self.user_isid)

        # if flag set to True then get subject parents for a given subject.
        if get_parents:
            self.get_parents_recursively([subject_details], self.user_isid, get_children)
        return subject_details

    def insert_subject(self, subject: EntitySubject):
        """
        Insert the Subject.

        :param subject:
        :param region:
        :return:
        """
        # check permission only for group. User is created automatically if it is assigned within AD and the
        # project is created during on-boarding process and raise authorization error if user does not have rights.
        self.logger.info(f"Going to validate create subjects permission for user {self.user_isid}")
        if self.auth_validator.validate(ActionType.CREATE_SUBJECT,
                                        {"subjectType": subject.subject_type}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"user {self.user_isid} does not have access to create subjects of type {subject.subject_type.value}")
        # check if the subject already exists in metaDB
        self.logger.info("Going to validate the existence of subject before it is created in MetaDB")
        check_subject_existence = EntitySubject.from_metadb_object(
            self.subjects_metadata_provider.get_subject(self.user_isid, subject.subject_id))
        self.logger.info("Going to initiate the MSD API client with the given input parameters")
        msd_api_client = MSDApiClient(os.environ['MSD_INTERNAL_API_URL'],
                                      lambda_secrets_manager=self.lambda_secrets_manager,
                                      secret_manager_connection=self._api_connection)
        # Make an MSD API call to get the subject details from AD
        self.logger.info("getting the group details from Merck internal directory")
        subject_details = msd_api_client.get_security_group_by_name(subject.subject_id)
        if not subject_details:
            raise NoDataError("The group does not belongs to any MSD SG group")
        if subject_details.displayName:
            subject.set_display_name(subject_details.displayName)
        # if subject exist in MetaDB then add the hierarchy details into DB
        if not check_subject_existence:
            self.logger.info("skipping insert subject call as the subject is existing in DB already in subjects Entity")
            EntitySubject.from_metadb_object(
                self.subjects_metadata_provider.insert_subject(subject.to_metadb_object(), self.user_isid))
        # Add subject under project
        self.subjects_metadata_provider.insert_subject_hierarchy(subject.subject_id,
                                                                 [EntitySubject(subject_id=self.project_id,
                                                                                subject_type=SubjectTypesEnum.project)])

    def delete_subject(self, subject_id):
        """
        Deletes the subject of type group.

        param subject_id:
        """
        subject = self.get_subject(subject_id)
        # validate delete subject permissions for user.
        self.logger.info(f"Going to validate delete subjects permission for user {self.user_isid}")
        if self.auth_validator.validate(ActionType.DELETE_SUBJECT,
                                        {"subjectType": subject.subject_type.value, "subjectId": subject.subject_id}
                                        ) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"user {self.user_isid} does not have access to delete subjects of type {subject.subject_type.value}")
        # remove the subject hierarchy details and permissions tagged to user, if there are any permissions tagged to
        # Subject as well
        self.logger.info(f"going to remove subject details for subject - {subject_id}")
        return self.subjects_metadata_provider.delete_subject(subject.to_metadb_object(), self.user_isid)

    def enable_or_disable_subject(self, subject_id, enable=True):
        """
        Performs Partial update (Enable/Disable) of subject.

        :param subject_id- subject id to b enabled or disabled.
        :param enable:
        """
        self.logger.info(f"Going to {'enable' if enable else 'disable'} subject with id {subject_id}")
        subject = self.get_subject(subject_id)
        # validate if user has update permissions if not raise auth error
        self.logger.info(f"Going to validate update subjects permission for user {self.user_isid}")
        if self.auth_validator.validate(ActionType.UPDATE_SUBJECT,
                                        {"subjectType": subject.subject_type.value,
                                         "subjectId": subject_id}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"user {self.user_isid} does not have access to update subject {subject_id}")
        subject.set_is_enabled(enable)
        self.logger.info(f"Going to perform partial update of subject {subject_id}")
        return EntitySubject.from_metadb_object(
            self.subjects_metadata_provider.update_subject(subject.to_metadb_object(),
                                                           self.user_isid))

    def get_children_recursively(self, subjects: list, user_isid: str):
        """
        loop all children and find recursively whole children in hierarchy
        :param subjects:
        :param user_isid:
        :return:
        """
        for subject in subjects:
            # do not need to check for subject type user, as user has no children at all ,
            # so we do not have to make DB call
            if subject.subject_type != SubjectTypesEnum.user:
                children = EntitySubject.from_metadb_objects(
                    self.subjects_metadata_provider.get_subject_children_in_hierarchy(subject.subject_id, user_isid))
                subject.set_children(children)
                self.get_children_recursively(children, user_isid)

    def get_parents_recursively(self, subjects: list, user_isid: str, get_children: bool = False):
        """
        Get the subject parents for the given subject id.

        :param subjects:
        :param user_isid:
        :param get_children:
        :return:
        """

        for subject in subjects:
            # do not need to check for subject type project, as project has no more parents ,
            # so we do not have to make DB call
            if subject.subject_type != SubjectTypesEnum.project:
                parents = EntitySubject.from_metadb_objects(
                    self.subjects_metadata_provider.get_subject_parents_in_hierarchy(subject.subject_id, user_isid))
                subject.set_parents(parents)
                # check if children should be added - will not cycle, as get_children call does not call parents
                if get_children:
                    # set children for each of the parent retrieved
                    self.get_children_recursively(parents, user_isid)
                self.get_parents_recursively(parents, user_isid)

    def get_subjects(self, subject_type: SubjectTypesEnum = None, get_children: bool = False, enabled: bool = None,
                     display_name: str = None, sort_and_paginate: SortAndPaginate = None,
                     parent_subject_id: str = None):
        """
        Get subjects
        :param subject_type: type of subject you want to retrieve from DB if not specified will retrieve all the
        subjects where user has read access
        :param get_children: flag, if true will return subject children hierarchy
        :param enabled: optional parameter, if set to true will retrieve subjects that are currently on DB, if set to
        false will get you all the disabled subjects from DB.
        :param display_name: optional parameter , substring of display name of subject
        :param sort_and_paginate:
        :param parent_subject_id:
        :return: list of EntitySubjects
        """
        self.logger.info(f"Going to retrieve subjects of type {subject_type}")
        # Get all Subjects from DB based on subject type sent from request.if subject type is none then we will
        # retrieve all the subjects from DB.
        subjects, total_count = self.subjects_metadata_provider.get_subjects(
            self.user_isid, subject_type, display_name, enabled, sort_and_paginate, parent_subject_id)
        entity_subjects = EntitySubject.from_metadb_objects(subjects)
        if not entity_subjects:
            raise NoDataError("There are no subjects which match your search criteria")
        if get_children:
            self.get_children_recursively(entity_subjects, self.user_isid)
        entity_subjects = [ct.to_json_dict() for ct in entity_subjects]
        return entity_subjects, total_count
