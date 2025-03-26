from sqlalchemy import and_
from sqlalchemy.orm import aliased

from middleware.api.common.helpers import SortAndPaginate, add_order_to_query
from middleware.common.metadatabase.clients.meta_database_client import MetaDatabaseClient
from middleware.common.metadatabase.model.difw_metadb_model import Subjects, SubjectsHierarchy
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum


class SubjectsMetadataProvider(MetaDatabaseClient):
    """
    Database client which served actions related with subjects
    """

    def delete_subject(self, subject: Subjects, user_id: str):
        """
        Delete subject

        :param subject: subject to delete
        :param user_id: logon user isid
        """
        self.delete_record(subject, user_id)

    def insert_or_update_subject(self, subject: Subjects, user_id: str):
        """
        Insert or update subject

        :param subject: subject which will be either created or updated
        :param user_id: user who create/update the subject

        :return: inserted or updated subject
        """
        return self.insert_or_update_record(subject, user_id)

    def update_subject(self, subject: Subjects, user_id: str):
        """
        Update existing subject

        :param subject:
        :param user_id: user who update the subject
        :return: updated subject
        """
        return self.update_record(subject, user_id)

    def insert_subject(self, subject: Subjects, user_id: str):
        """
        Insert new subject

        :param subject:
        :param user_id: - user who insert the subject
        """
        return self.insert_record(subject, user_id)

    def get_subjects_by_subject_ids(self, subject_ids, user_id: str):
        """
        Get subjects from DB based on inputted subject ids.

        :param subject_ids: list of subject Ids
        :param user_id:

        :return: list of subjects
        """
        self.logger.info(f"User {user_id} is going to get subject details of subjects with ids {subject_ids}")
        return Subjects.get_many(self.session, and_(Subjects.SUBJECT_ID.in_(subject_ids)))

    def get_subject(self, user_id: str, subject_id: str):
        """
        Get subject from DB

        :param user_id:
        :param subject_id:

        :return: subject
        """
        self.logger.info(f"User {user_id} is going to retrieve subject with id {subject_id} ")
        return Subjects(SUBJECT_ID=subject_id).get_unique(self.session)

    def get_subject_parents_in_hierarchy(self, subject_id: str, user_id: str):
        """
        Get the subject parents in hierarchy

        :param subject_id:
        :param user_id:

        :return: list of parent subjects
        """
        self.logger.info(
            f"User {user_id} is going to retrieve subject parents for subject with ID = {subject_id} ")
        dynamic_query = self.session.query(Subjects). \
            join(SubjectsHierarchy, and_(Subjects.SUBJECT_ID == SubjectsHierarchy.PARENT_ID)). \
            filter(and_(SubjectsHierarchy.CHILD_ID == subject_id))
        return dynamic_query.all()

    def get_subject_children_in_hierarchy(self, subject_id: str, user_id: str):
        """
        Get the subject parents in hierarchy

        :param subject_id:
        :param user_id:

        :return: list of children subjects
        """
        self.logger.info(
            f"User {user_id} is going to retrieve subject children for subject with ID = {subject_id} ")
        # removing the existing functionality of fetching children details using rel_children_subject , as
        # using relation is applying filters incorrectly to fetch data which is yielding incorrect results
        # so have to build custom query here to achieve the functionality.
        dynamic_query = self.session.query(Subjects). \
            join(SubjectsHierarchy, and_(Subjects.SUBJECT_ID == SubjectsHierarchy.CHILD_ID)). \
            filter(and_(SubjectsHierarchy.PARENT_ID.in_([subject_id])))
        return dynamic_query.all()

    def delete_subject_child_from_hierarchy(self, subject_id: str):
        """
        deletes the subject hierarchy for a given subject

        :param subject_id:
        """
        self.logger.info(f"Going to delete subject hierarchy for subject - {subject_id} ")
        return SubjectsHierarchy.delete_many(self.session, SubjectsHierarchy.CHILD_ID == subject_id)

    def insert_subject_hierarchy(self, subject_child_id: str, subject_parents: list):
        """
        Insert subject hierarchy

        :param subject_child_id:
        :param subject_parents: (list of subjects)
        :return:
        """
        self.logger.info(f"Inserting the hierarchy for child {subject_child_id}")
        for parent in subject_parents:
            SubjectsHierarchy(PARENT_ID=parent.subject_id, CHILD_ID=subject_child_id).insert(self.session)

    def get_subjects(self, user_id: str, subject_type: SubjectTypesEnum = None, display_name: str = None,
                     enabled: bool = None, sort_and_paginate: SortAndPaginate = None, parent_subject_id: str = None):
        """
        Gets all subjects from DB.

        :param user_id: logon user isid
        :param subject_type: type of subject you want to retrieve it can be one among project, group , user
        :param display_name
        :param enabled
        :param sort_and_paginate:
        :param parent_subject_id:
        :return:
        """
        self.logger.info(f"user {user_id} is going to retrieve the subjects of type"
                         f" {subject_type if subject_type else 'project, group and user'} from DB, specific for "
                         f"{parent_subject_id if parent_subject_id else 'no parent'}")

        if parent_subject_id:
            sh_1 = aliased(SubjectsHierarchy)
            sh_2 = aliased(SubjectsHierarchy)
            query1 = self.session.query(sh_2.CHILD_ID, Subjects.SUBJECT_TYPE, Subjects.DISPLAY_NAME,
                                        sh_1.PARENT_ID, Subjects.IS_ENABLED, Subjects.DESCRIPTION,
                                        Subjects.SUBJECT_ID) \
                .join(sh_2, sh_1.CHILD_ID == sh_2.PARENT_ID, isouter=True) \
                .join(Subjects, sh_2.CHILD_ID == Subjects.SUBJECT_ID)

            query2 = self.session.query(sh_1.CHILD_ID, Subjects.SUBJECT_TYPE, Subjects.DISPLAY_NAME,
                                        sh_1.PARENT_ID, Subjects.IS_ENABLED, Subjects.DESCRIPTION,
                                        Subjects.SUBJECT_ID) \
                .join(sh_2, sh_1.CHILD_ID == sh_2.PARENT_ID, isouter=True) \
                .join(Subjects, sh_1.CHILD_ID == Subjects.SUBJECT_ID)
            query1 = query1.filter(sh_1.PARENT_ID == parent_subject_id)
            query2 = query2.filter(sh_1.PARENT_ID == parent_subject_id)
            if subject_type:
                query1 = query1.filter(and_(Subjects.SUBJECT_TYPE == subject_type))
                query2 = query2.filter(and_(Subjects.SUBJECT_TYPE == subject_type))
            dynamic_query = query1.union(query2)
        else:
            dynamic_query = self.session.query(Subjects)
            if subject_type:
                dynamic_query = dynamic_query.filter(and_(Subjects.SUBJECT_TYPE == subject_type))
        # filter on Is_Enabled - if true/false, return only with the same flag value
        if enabled is not None:
            # pylint: disable=singleton-comparison
            dynamic_query = dynamic_query.filter(Subjects.IS_ENABLED == True) if enabled else dynamic_query.filter(
                Subjects.IS_ENABLED == False)
        # if display_name is given (or substring)
        if display_name:
            dynamic_query = dynamic_query.filter(Subjects.DISPLAY_NAME.ilike(f"%{display_name}%"))
        if sort_and_paginate and sort_and_paginate.sorted_conversion:
            dynamic_query = add_order_to_query(dynamic_query, Subjects, sort_and_paginate.sorted_conversion)

        subjects, total_count = self.process_get_entries_and_count(sort_and_paginate, dynamic_query)
        return subjects, total_count
