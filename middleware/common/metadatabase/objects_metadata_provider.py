from sqlalchemy import func, update, and_
from sqlalchemy.orm import aliased

from middleware.api.common.helpers import SortAndPaginate, add_order_to_query
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.metadatabase.clients.meta_database_client import MetaDatabaseClient
from middleware.common.metadatabase.model.difw_metadb_model import ObjectsACL, ObjectProperties, Objects
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum


class ObjectsMetadataProvider(MetaDatabaseClient):
    """
    Database client which serves actions related to objects.
    """

    def get_objects_acl(self, object_name: str, object_version: str = "1.0.0", user_id: str = "",
                        object_type: ObjectTypesEnum = ObjectTypesEnum.pipeline):
        """
        Get objects ACLs

        @param object_name:
        @param object_version:
        @param user_id:
        @param object_type

        @return: list of object ACLs
        """
        self.logger.info(f"User {user_id} is going to get objects ACL for object {object_name} "
                         f"and version {object_version}")
        return self.session.query(ObjectsACL).filter(
            and_(ObjectsACL.OBJECT_FULL_NAME == f"{object_name}.{object_type.value}",
                 ObjectsACL.OBJECT_VERSION == object_version)
        ).all()

    def get_objects_dag_name(self, object_name: str, object_version: str = "1.0.0", user_id: str = "",
                             object_type: ObjectTypesEnum = ObjectTypesEnum.pipeline):
        """
        Get DAG name of object

        @param object_name:
        @param object_version:
        @param user_id:
        @param object_type:

        @return: dag id/dag name of object
        """
        self.logger.info(f"User {user_id} is going to get DAG name for object {object_name} "
                         f"and version {object_version}")

        dag_id_property = ObjectProperties(
            OBJECT_FULL_NAME=f"{object_name}.{object_type.value}",
            OBJECT_VERSION=object_version,
            PROPERTY_NAME="dagId"
        ).get_unique(self.session)
        if not dag_id_property:
            return None
        return dag_id_property.PROPERTY_STRING_VALUE

    def update_schedule(self, object_name: str, schedule_cron: str, user_id: str, object_version: str = "1.0.0",
                        object_type: ObjectTypesEnum = ObjectTypesEnum.pipeline):
        """
        Update schedule property in DB

        @param object_name:
        @param object_version:
        @param schedule_cron: schedule/cron
        @param user_id:
        @param object_type:
        """
        self.logger.info(f"User {user_id} is going to update scheduler for object with name {object_name} "
                         f"and version {object_version}")
        ObjectProperties(
            OBJECT_FULL_NAME=f"{object_name}.{object_type.value}",
            OBJECT_VERSION=object_version,
            PROPERTY_NAME="schedule",
            PROPERTY_STRING_VALUE=schedule_cron
        ).update(self.session)

    def update_object_enable_flag(self, object_name: str, user_id: str, object_version: str = "1.0.0",
                                  enabled: bool = "", object_type: ObjectTypesEnum = ObjectTypesEnum.pipeline):
        """
        Update enabled flag for object

        @param object_name:
        @param object_version:
        @param enabled: enabled flag
        @param user_id:
        @param object_type:
        """
        self.logger.info(f"User {user_id} is going to update enable flag for object with name {object_name} "
                         f"and version {object_version}")
        self.session.execute(
            update(Objects).
            where(and_(Objects.OBJECT_FULL_NAME == f"{object_name}.{object_type.value}",
                       Objects.OBJECT_VERSION == object_version)).
            values({
                Objects.IS_ENABLED: enabled
            })
        )
        self.session.commit()

    def update_object_assigned_acl_list(self, object_name: str, acls: [EntityACL],
                                        user_id: str, object_version: str = "1.0.0",
                                        object_type: ObjectTypesEnum = ObjectTypesEnum.pipeline,
                                        relation_type: ObjectsACLRelationTypesEnum =
                                        ObjectsACLRelationTypesEnum.shared):
        """
        Removes the existing shared ACL of same relation type and for the given object and recreates the new ACL.

        @param object_name:
        @param object_version:
        @param acls: acls which are going to be assigned
        @param user_id:
        @param object_type:
        @param relation_type:
        """
        # Get all ACLs for the given subject which have relation type as shared
        self.logger.info("Going to remove the existing ACLs")
        ObjectsACL.delete_many(
            self.session,
            filter_condition=and_(
                ObjectsACL.OBJECT_FULL_NAME == f"{object_name}.{object_type.value}",
                ObjectsACL.RELATION_TYPE == relation_type,
                ObjectsACL.OBJECT_VERSION == object_version
            ),
            commit=False
        )
        self.logger.info("Going to recreate the new ACLs")
        for acl in acls:
            acl_to_insert_update = ObjectsACL(
                OBJECT_FULL_NAME=f"{object_name}.{object_type.value}",
                OBJECT_VERSION=object_version,
                SUBJECT_ID=acl.subject.subject_id,
                RELATION_TYPE=acl.relation_type
            )
            self.enrich_with_updating_audit_columns(acl_to_insert_update, user_id)
            self.insert_record(acl_to_insert_update, user_id, commit=False)
        # Issue commit on session only if the whole transaction is complete.
        self.commit()

    # pylint: disable=not-callable
    def exists_object(self, object_name: str, object_version: str = "1.0.0", user_id: str = "",
                      object_type: ObjectTypesEnum = ObjectTypesEnum.pipeline):
        """
        Check if object with the specific name and version exists

        @param object_name:
        @param object_version:
        @param user_id:
        @param object_type:

        @return: flag indicates if object either exists or not
        """
        self.logger.info(f"User {user_id} is going to check if object with name {object_name} "
                         f"and version {object_version} exists")

        object_count = self.session.query(func.count(Objects.OBJECT_FULL_NAME)).filter(
            and_(func.lower(Objects.OBJECT_FULL_NAME) == f"{object_name}.{object_type.value}".lower(),
                 Objects.OBJECT_VERSION == object_version)
        ).scalar()
        return object_count > 0

    def get_object(self, object_name: str, object_version: str = "1.0.0",
                   object_type: ObjectTypesEnum = ObjectTypesEnum.pipeline, user_id: str = ""):
        """
        Get object from DB

        @param object_name:
        @param object_version:
        @param object_type:
        @param user_id:

        @return: Object DB entity
        """
        self.logger.info(f"User {user_id} is going to retrieve object with name {object_name}")
        return Objects(
            OBJECT_FULL_NAME=f"{object_name}.{object_type.value}",
            OBJECT_VERSION=object_version
        ).get_unique(self.session)

    # pylint: disable=too-many-arguments
    def get_objects(
            self,
            user_id: str,
            subject_ids: list,
            object_name: str = None,
            is_enabled: bool = None,
            owner: str = None,
            project_id: str = None,
            sort_and_paginate: SortAndPaginate = None,
            object_version: str = "1.0.0",
            object_type: ObjectTypesEnum = ObjectTypesEnum.pipeline
    ):
        """
        Get objects from DB
        @param user_id: user_id of the user
        @param subject_ids: ids of subjects, for which the object is accessible
        @param object_name: used for regex filtration on object_name
        @param is_enabled: if given will return the objects with correct is_enabled state
        @param owner: if given exact filtration on name of owner
        @param project_id: if given exact filtration on project
        @param sort_and_paginate: pagination logic
        @param object_version: placeholder for future versioning implementation
        @param object_type: which type of objects to be returned

        @return: Object DB entities
        """
        self.logger.info(f"User {user_id} is going to retrieve objects of version {object_version}")
        # When versioning is added, we should also add a filter on object_version
        dynamic_query = self.session.query(Objects). \
            join(ObjectsACL, Objects.OBJECT_FULL_NAME == ObjectsACL.OBJECT_FULL_NAME). \
            filter(and_(ObjectsACL.SUBJECT_ID.in_(subject_ids), Objects.OBJECT_TYPE == object_type.value))

        if object_name:
            dynamic_query = dynamic_query.filter(
                ObjectsACL.OBJECT_FULL_NAME.ilike(f"%{object_name}%"))

        if is_enabled is not None:
            dynamic_query = dynamic_query.filter(Objects.IS_ENABLED == is_enabled)

        # If owner and project_id are given, then we need to filter the objects with joined ACLs
        if owner and project_id:
            owner_objects_acl = aliased(ObjectsACL)
            dynamic_query = dynamic_query.join(
                owner_objects_acl,
                and_(
                    Objects.OBJECT_FULL_NAME == owner_objects_acl.OBJECT_FULL_NAME,
                    owner_objects_acl.RELATION_TYPE == ObjectsACLRelationTypesEnum.owner,
                    owner_objects_acl.SUBJECT_ID == owner
                )
            )

            project_objects_acl = aliased(ObjectsACL)
            dynamic_query = dynamic_query.join(
                project_objects_acl,
                and_(
                    Objects.OBJECT_FULL_NAME == project_objects_acl.OBJECT_FULL_NAME,
                    project_objects_acl.RELATION_TYPE == ObjectsACLRelationTypesEnum.owner,
                    project_objects_acl.SUBJECT_ID == project_id
                )
            )
        else:  # If only owner or project_id is given, then we need to filter over joined ACLs yet
            if owner:
                dynamic_query = dynamic_query.filter(
                    and_(
                        ObjectsACL.SUBJECT_ID == owner,
                        ObjectsACL.RELATION_TYPE == ObjectsACLRelationTypesEnum.owner
                    )
                )
            elif project_id:
                dynamic_query = dynamic_query.filter(
                    and_(
                        ObjectsACL.SUBJECT_ID == project_id,
                        ObjectsACL.RELATION_TYPE == ObjectsACLRelationTypesEnum.owner
                    )
                )

        if sort_and_paginate and sort_and_paginate.sorted_conversion:
            dynamic_query = add_order_to_query(dynamic_query, Objects, sort_and_paginate.sorted_conversion)

        return dynamic_query.all()

    def delete_object(self, object_name: str, user_id: str, object_version: str = "1.0.0", commit=True,
                      object_type: ObjectTypesEnum = ObjectTypesEnum.pipeline):
        """
        Delete object.

        @param object_name:
        @param user_id:
        @param object_version:
        @param commit:
        @param object_type:

        @return: deleted object obj
        """
        self.logger.info(f"User {user_id} is going to delete object of type {object_type} with name {object_name}")
        return Objects(
            OBJECT_FULL_NAME=f"{object_name}.{object_type.value}",
            OBJECT_VERSION=object_version
        ).delete(self.session, commit)
