from sqlalchemy import and_

from middleware.api.common.helpers import SortAndPaginate
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.metadatabase.model.difw_metadb_model import Objects, Components
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.objects_metadata_provider import ObjectsMetadataProvider


class PipelinesMetadataProvider(ObjectsMetadataProvider):
    """
    Database client which served actions related with pipelines
    """

    def get_pipeline_acl(self, pipeline_name, pipeline_version: str = "1.0.0", user_id: str = ""):
        """
        Get pipeline ACLs

        @param pipeline_name:
        @param pipeline_version:
        @param user_id:

        @return: list of pipeline ACLs
        """
        return self.get_objects_acl(pipeline_name, pipeline_version, user_id)

    def get_pipeline_dag_name(self, pipeline_name, pipeline_version: str = "1.0.0", user_id: str = ""):
        """
        Get DAG name of pipeline

        @param pipeline_name:
        @param pipeline_version:
        @param user_id:

        @return: dag id/dag name of pipeline
        """
        return self.get_objects_dag_name(pipeline_name, pipeline_version, user_id)

    # pylint: disable=too-many-function-args
    def update_pipeline_assigned_acl_list(self, pipeline_name: str, acls: [EntityACL],
                                          user_id: str, pipeline_version: str = "1.0.0"):
        """
        removes the existing shared acl either for the given pipeline and recreate the new acl.

        @param pipeline_name:
        @param pipeline_version:
        @param acls: acls which are going to be assigned
        @param user_id:

        """
        self.update_object_assigned_acl_list(object_name=pipeline_name, acls=acls,
                                             user_id=user_id, object_version=pipeline_version,
                                             object_type=ObjectTypesEnum.pipeline,
                                             relation_type=ObjectsACLRelationTypesEnum.shared)

    def update_pipeline_enable_flag(self, pipeline_name, user_id: str, pipeline_version: str = "1.0.0",
                                    enabled: bool = ""):
        """
        Update enabled flag for pipeline

        @param pipeline_name:
        @param pipeline_version:
        @param enabled: enabled flag
        @param user_id:
        """
        self.update_object_enable_flag(pipeline_name, user_id, pipeline_version, enabled)

    def exists_pipeline(self, pipeline_name, pipeline_version: str = "1.0.0", user_id: str = ""):
        """
        Check if pipeline with the specific name and version exists

        @param pipeline_name:
        @param pipeline_version:
        @param user_id:

        @return: flag indicates if pipeline either exists or not
        """
        return self.exists_object(pipeline_name, pipeline_version, user_id, ObjectTypesEnum.pipeline)

    def get_pipeline(self, pipeline_name: str, pipeline_version: str = "1.0.0", user_id: str = ""):
        """
        Get pipeline from DB

        @param pipeline_name:
        @param pipeline_version:
        @param user_id:

        @return: Object DB entity
        """
        return self.get_object(pipeline_name, pipeline_version, ObjectTypesEnum.pipeline, user_id)

    # pylint: disable=too-many-arguments
    def get_pipelines(
            self,
            user_id: str,
            subject_ids: list,
            pipeline_name: str = None,
            is_enabled: bool = None,
            owner: str = None,
            sort_and_paginate: SortAndPaginate = None,
            project_id: str = None,
            pipeline_version: str = "1.0.0"
    ):
        """
        Get pipelines from DB
        @param user_id:
        @param subject_ids:
        @param pipeline_name:
        @param is_enabled:
        @param owner:
        @param sort_and_paginate:
        @param pipeline_version: placeholder for future versioning implementation
        @param project_id:
        @return: Object DB entity
        """
        self.logger.info(f"User {user_id} is going to retrieve pipelines of version {pipeline_version}")

        return self.get_objects(
            user_id=user_id,
            subject_ids=subject_ids,
            object_name=pipeline_name,
            is_enabled=is_enabled,
            owner=owner,
            project_id=project_id,
            sort_and_paginate=sort_and_paginate,
            object_version=pipeline_version,
            object_type=ObjectTypesEnum.pipeline
        )

    def insert_or_update_pipeline(self, pipeline_object: Objects, pipeline_components: [Components],
                                  is_update=False, user_id: str = ""):
        """
        Insert or update pipeline into DB

        @param pipeline_object: object to update or insert
        @param pipeline_components: associate components with pipeline object
        @param is_update: flag indicates if update or create is needed
        @param user_id: id of user which is performing action

        @return: Object DB entity
        """
        self.logger.info(f"User {user_id} is going to insert pipeline with name {pipeline_object.OBJECT_FULL_NAME}")
        # if we are creating new pipeline, but there was once pipeline with same name after which some of its tables
        # were left behind, we delete them otherwise we may run into data conflict
        if not is_update:
            self.delete_unmapped_pipeline_tables(user_id)
        new_components_name_id_pair, all_components_name_item_pair = \
            self.insert_new_components(pipeline_components, user_id)
        try:
            self.logger.info(
                f"User {user_id} is going to insert/update pipeline with name {pipeline_object.OBJECT_FULL_NAME} ")

            # ==========================================================================================================
            # AUDIT COLUMNS ENRICHMENT
            # ==========================================================================================================

            self._object_audit_columns_enrich(pipeline_object, pipeline_components, is_update, user_id)

            # ==========================================================================================================
            # ASSIGN CORRECT RELATIONS
            # ==========================================================================================================

            self._relation_object_enrich(pipeline_object, new_components_name_id_pair,
                                         all_components_name_item_pair)

            # ==========================================================================================================
            # SAVE OBJECT INTO DB
            # ==========================================================================================================

            if is_update:
                return self.update_record(pipeline_object, user_id)
            return self.insert_record(pipeline_object, user_id)
        # pylint: disable=bare-except
        # OperationalError exception is raised for operational errors,
        # such as issues with the database connection or transaction problems
        except Exception as exception:
            # delete the inserted  records in the components table
            Components.delete_many(self.session, Components.COMPONENT_ID.in_(new_components_name_id_pair.values()))
            raise exception

    def delete_pipeline(self, pipeline_name: str, user_id: str, pipeline_version: str = "1.0.0", commit=True):
        """
        Delete pipeline.

        @param pipeline_name:
        @param user_id:
        @param pipeline_version:
        @param commit:

        @return: deleted pipeline obj
        """
        return self.delete_object(pipeline_name, user_id, pipeline_version, commit, ObjectTypesEnum.pipeline)

    def delete_unmapped_pipeline_tables(self, user_id: str):
        """
        Delete pipeline tables which do not have parent object
        @param user_id:
        """
        self.logger.info(f"User {user_id} is going to delete unmapped pipelines")
        Objects.delete_many(
            self.session,
            filter_condition=and_(Objects.OBJECT_TYPE == ObjectTypesEnum.pipeline_table,
                                  Objects.PARENT_OBJECT_FULL_NAME.is_(None)),
            commit=False
        )
        return self.commit()

    def get_pipelines_list_by_name(self, user_id: str, list_of_pipelines_names: list, pipeline_version: str = "1.0.0"):
        """
        Get pipelines from DB
        @param user_id:
        @param list_of_pipelines_names:
        @param pipeline_version: placeholder for future versioning implementation

        @return: Object DB entity
        """
        self.logger.info(f"User {user_id} is going to retrieve pipelines with names {list_of_pipelines_names}"
                         f" of version {pipeline_version}")
        # when versioning will be added, we should also add filter on pipeline_version
        dynamic_query = self.session.query(Objects, Objects.OBJECT_FULL_NAME.in_(list_of_pipelines_names))
        return dynamic_query.all()
