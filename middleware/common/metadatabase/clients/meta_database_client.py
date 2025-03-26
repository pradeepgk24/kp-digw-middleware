import datetime
import logging
import os
from sqlalchemy.exc import IntegrityError

from middleware.api.common.helpers import SortAndPaginate
from middleware.common.helpers.exception import EntityConflictError
from middleware.common.metadatabase.clients.database_client import DatabaseClient
from middleware.common.metadatabase.connectors.difw_metadb_connector import DifwMetadbConnector
from middleware.common.metadatabase.model.difw_metadb_model import BaseTableModel, Components, Objects


class MetaDatabaseClient(DatabaseClient):
    """
    DB client for DIFW metadDB
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        metadb_connector = DifwMetadbConnector(self.logger)
        self.connector_engine = metadb_connector.init_connection_engine(
            self._secret_manager_connection,
            self._lambda_secrets_manager)
        self.session = metadb_connector.create_new_session()
        self.logger.info(f"New session with id {id(self.session)} for client {self.__class__.__name__} was created,...")
        self.set_log_level()

    @staticmethod
    def set_log_level() -> None:
        """
        Set the log level from the environment variable SQLALCHEMY_LOG_LEVEL, the default value is ERROR
        """
        log_level = os.environ.get("SQLALCHEMY_LOG_LEVEL", "ERROR")
        logger = logging.getLogger('sqlalchemy')
        logger.setLevel(log_level)

    def commit(self):
        """
        Commit all changes within session
        """
        self.session.commit()

    def insert_or_update_record(self, record_object: BaseTableModel, user_id: str, commit: bool = True):
        """
        Insert or update DB object

        :param record_object: object to insert or update
        :param user_id: user performing the action
        :param commit: flag specifying whether to commit the transaction or not

        :return: inserted or updated object
        """
        self.logger.info(
            f"User {user_id} is going to insert or update {record_object.__tablename__} "
            f"with ids {record_object.get_pk_values()}")
        db_result = record_object.get_unique(self.session)
        # check existence of records. If exists then update, if does not exist then create new
        if not db_result:
            return self.insert_record(record_object, user_id, commit)
        return self.update_record(record_object, user_id)

    def insert_record(self, record_object: BaseTableModel, user_id: str, commit=True):
        """
        Insert new DB record

        :param record_object: object to insert
        :param user_id: user performing the action
        :param commit: flag indicate if the record should be commit or not

        :return: inserted object
        """
        self.logger.info(f"User {user_id} is going to insert {record_object.__tablename__} "
                         f"with ids {record_object.get_pk_values()}")
        try:
            self.enrich_with_creation_audit_columns(record_object, user_id)
            return record_object.insert(self.session, commit)
        except IntegrityError as integrity_error:
            self.session.rollback()
            raise EntityConflictError(
                f"There was a problem with inserting record into table {record_object.__tablename__},"
                f" it is possible that record with same name already exists or attributes are misspecified.") \
                from integrity_error

    def update_record(self, record_object: BaseTableModel, user_id: str, commit: bool = True):
        """
        Insert existing DB record

        :param record_object: object to insert
        :param user_id: user performing the action
        :param commit: flag indicates if run commit or not

        :return: inserted object
        """
        self.logger.info(f"User {user_id} is going to update {record_object.__tablename__} "
                         f"with ids {record_object.get_pk_values()}")
        self.enrich_with_updating_audit_columns(record_object, user_id)
        return record_object.update(self.session, commit)

    def delete_record(self, record_object: BaseTableModel, user_id: str):
        """
        Delete existing DB record

        :param record_object: object to delete
        :param user_id: user performing the action

        :return: deleted object
        """
        self.logger.info(f"User {user_id} is going to delete {record_object.__tablename__} "
                         f"with ids {record_object.get_pk_values()}")
        return record_object.delete(self.session)

    @staticmethod
    def enrich_with_creation_audit_columns(db_model_table: BaseTableModel, user_id):
        """
        Enrich base table model with audit columns for creation
        """
        if hasattr(db_model_table, "CREATOR_ID"):
            current_epoch_time = datetime.datetime.now()
            db_model_table.CREATOR_ID = user_id
            db_model_table.LAST_MODIFIED_ID = user_id
            db_model_table.CREATED_TIME = current_epoch_time
            db_model_table.LAST_MODIFIED_TIME = current_epoch_time

    @staticmethod
    def enrich_with_updating_audit_columns(db_model_table: BaseTableModel, user_id):
        """
        Enrich base table model with audit columns for updating
        """
        if hasattr(db_model_table, "LAST_MODIFIED_ID"):
            current_epoch_time = datetime.datetime.now()
            db_model_table.LAST_MODIFIED_ID = user_id
            db_model_table.LAST_MODIFIED_TIME = current_epoch_time

    @staticmethod
    def enrich_object_component_with_id(db_model_table: BaseTableModel, component_id):
        """
        Enrich base table model with component id for creation
        """
        if hasattr(db_model_table, "COMPONENT_ID"):
            db_model_table.COMPONENT_ID = component_id

    @staticmethod
    def process_get_entries_and_count(sort_and_paginate: SortAndPaginate, query):
        """
        Approach with using count() and all() in one call to database proved to provide unnecessarily complex
        sql_alchemy outputs, it is possible to use it, however for the sake of clarity of code, approach utilizing
        2 separate calls for count() and all() is used. If it will be inefficient in the future, it is possible to
        re-implement it
        :param sort_and_paginate:
        :param query:
        """
        if sort_and_paginate:
            return query.offset((sort_and_paginate.page_number - 1) *
                                sort_and_paginate.page_size).limit(sort_and_paginate.page_size).all(), query.count()
        return query.all(), query.count()

    def insert_new_components(self, components: [Components], user_id: str):
        """
        insert component in order to generate autoincremental ID.

        :param components:
        :param user_id:

        :return: pair of component names and associated component Ids and pair of all components
        """
        self.logger.info("Start method insert_or_update_components")
        component_name_id_pair = {}
        all_components_name_item_pair = {}
        for component in components:
            all_components_name_item_pair[component.COMPONENT_NAME] = component
            # enhance insert audit columns of related component record
            if not component.COMPONENT_ID:
                component_name = component.COMPONENT_NAME
                self.enrich_with_creation_audit_columns(component, user_id)
                pipeline_component_object = self.insert_or_update_record(component, user_id)
                component_name_id_pair[component_name] = pipeline_component_object.COMPONENT_ID
        return component_name_id_pair, all_components_name_item_pair

    def _object_audit_columns_enrich(self, object_db_instance: Objects, objects_components: [Components],
                                     is_update=False, user_id: str = ""):
        """
        Enrich audit columns for DB object

        :param object_db_instance: object to enrich
        :param objects_components: associate components with object
        :param is_update: flag indicates if update or create is needed
        :param user_id: id of user which is performing action
        """
        if object_db_instance.rel_objects_acl:
            # enhance insert audit columns of related component record
            for acl in object_db_instance.rel_objects_acl:
                # do not update ACL, add audit columns only in case of update
                if not is_update:
                    self.enrich_with_creation_audit_columns(acl, user_id)
                else:
                    # for audit columns of acls when updating
                    self.enrich_with_updating_audit_columns(acl, user_id)

        # loop all objects_components and enrich it with update columns
        for object_step in objects_components:
            if is_update:
                self.enrich_with_updating_audit_columns(object_step, user_id)

    def _relation_object_enrich(self, object_db_instance: Objects, new_components_name_id_pair: dict,
                                all_components_name_item_pair: dict):
        """
        Enrich relation columns for DB object
        :param object_db_instance: object to enrich
        :param new_components_name_id_pair: pair of (component name of component id) which has been recently created
        :param all_components_name_item_pair: pair of (component name of component) of all component
        """
        # assign correct id to object component
        if object_db_instance.rel_object_components:
            # enhance insert audit columns of related component record
            # Iterate through the list of dictionaries and update 'COMPONENT_ID' using values from input_list
            for _, item in enumerate(object_db_instance.rel_object_components):
                if item.COMPONENT_ID is None:
                    self.enrich_object_component_with_id(item,
                                                         new_components_name_id_pair[item.COMPONENT_NAME])
                item.rel_component = all_components_name_item_pair[item.COMPONENT_NAME]

            # loop again assign relations in hierarchy
            for _, item in enumerate(object_db_instance.rel_object_components):
                for component_hierarchy_item in list(item.rel_child_components_hierarchy) + \
                                                list(item.rel_parent_components_hierarchy):
                    component_hierarchy_item.CHILD_COMPONENT_ID = \
                        None if not component_hierarchy_item.intern_child_object_component_reference else \
                            component_hierarchy_item.intern_child_object_component_reference.COMPONENT_ID
                    component_hierarchy_item.PARENT_COMPONENT_ID = \
                        None if not component_hierarchy_item.intern_parent_object_component_reference else \
                            component_hierarchy_item.intern_parent_object_component_reference.COMPONENT_ID

        # loop tables and check references between tables and components
        if object_db_instance.rel_children_objects:
            for table_object in object_db_instance.rel_children_objects:
                for step_table in table_object.rel_object_components:
                    if step_table.COMPONENT_ID is None:
                        self.enrich_object_component_with_id(
                            step_table,
                            all_components_name_item_pair[step_table.COMPONENT_NAME].COMPONENT_ID)
                    step_table.rel_component = all_components_name_item_pair[step_table.COMPONENT_NAME]

    def __del__(self):
        """
        Methods calls when instance is destruct
        """
        # close session at the end
        self.logger.info(f"Going to close connection with id {id(self.session)} ...")
        self.session.close()
