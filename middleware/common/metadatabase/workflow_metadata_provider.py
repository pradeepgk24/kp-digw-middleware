# pylint: skip-file
# pragma: no cover

# TODO - tmp skip because of pylint issues which will be resolved in next PR

from middleware.api.common.helpers import SortAndPaginate
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.metadatabase.model.difw_metadb_model import Objects, Components
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.objects_metadata_provider import ObjectsMetadataProvider


class WorkflowsMetadataProvider(ObjectsMetadataProvider):
    """
    Database client which served actions related with workflows
    """

    def get_workflow_acl(self, workflow_name, workflow_version: str = "1.0.0", user_id: str = ""):
        """
        Get workflow ACLs

        @param workflow_name:
        @param workflow_version:
        @param user_id:

        @return: list of workflow ACLs
        """
        return self.get_objects_acl(workflow_name, workflow_version, user_id, ObjectTypesEnum.workflow)

    def get_workflow_dag_name(self, workflow_name, workflow_version: str = "1.0.0", user_id: str = ""):
        """
        Get DAG name of workflow

        @param workflow_name:
        @param workflow_version:
        @param user_id:

        @return: dag id/dag name of workflow
        """
        return self.get_objects_dag_name(workflow_name, workflow_version, user_id, ObjectTypesEnum.workflow)

    def update_workflow_assigned_acl_list(self, workflow_name: str, acls: [EntityACL],
                                          user_id: str, workflow_version: str = "1.0.0"):
        """
        removes the existing shared acl either for the given workflow and recreate the new acl.

        @param workflow_name:
        @param workflow_version:
        @param acls: acls which are going to be assigned
        @param user_id:

        """
        self.update_object_assigned_acl_list(object_name=workflow_name, acls=acls, user_id=user_id,
                                             object_version=workflow_version, object_type=ObjectTypesEnum.workflow,
                                             relation_type=ObjectsACLRelationTypesEnum.shared)

    def update_workflow_enable_flag(self, workflow_name, user_id: str, workflow_version: str = "1.0.0",
                                    enabled: bool = ""):
        """
        Update enabled flag for workflow

        @param workflow_name:
        @param workflow_version:
        @param enabled: enabled flag
        @param user_id:
        """
        self.update_object_enable_flag(workflow_name, user_id, workflow_version, enabled, ObjectTypesEnum.workflow)

    def exists_workflow(self, workflow_name, workflow_version: str = "1.0.0", user_id: str = ""):
        """
        Check if workflow with the specific name and version exists

        @param workflow_name:
        @param workflow_version:
        @param user_id:

        @return: flag indicates if workflow either exists or not
        """
        return self.exists_object(workflow_name, workflow_version, user_id, ObjectTypesEnum.workflow)

    def get_workflow(self, workflow_name: str, workflow_version: str = "1.0.0", user_id: str = ""):
        """
        Get workflow from DB

        @param workflow_name:
        @param workflow_version:
        @param user_id:

        @return: Object DB entity
        """
        return self.get_object(workflow_name, workflow_version, ObjectTypesEnum.workflow, user_id)

    # pylint: disable=too-many-arguments
    def get_workflows(
            self,
            user_id: str,
            subject_ids: list,
            workflow_name: str = None,
            is_enabled: bool = None,
            owner: str = None,
            sort_and_paginate: SortAndPaginate = None,
            project_id: str = None,
            workflow_version: str = "1.0.0"
    ):
        """
        Get workflows from DB
        @param user_id:
        @param subject_ids:
        @param workflow_name:
        @param is_enabled:
        @param owner:
        @param project_id:
        @param sort_and_paginate:
        @param workflow_version: placeholder for future versioning implementation

        @return: list of Object DB entities
        """
        self.logger.info(f"User {user_id} is going to retrieve workflows of version {workflow_version}")
        return self.get_objects(
            user_id=user_id,
            subject_ids=subject_ids,
            object_name=workflow_name,
            is_enabled=is_enabled,
            owner=owner,
            project_id=project_id,
            sort_and_paginate=sort_and_paginate,
            object_version=workflow_version,
            object_type=ObjectTypesEnum.workflow
        )

    def delete_workflow(self, workflow_name: str, user_id: str, workflow_version: str = "1.0.0", commit=True):
        """
        Delete workflow.

        @param workflow_name:
        @param user_id:
        @param workflow_version:
        @param commit:

        @return: deleted workflow obj
        """
        return self.delete_object(workflow_name, user_id, workflow_version, commit, ObjectTypesEnum.workflow)

    def insert_or_update_workflow(self, workflow_object: Objects, workflow_components: [Components],
                                  is_update=False, user_id: str = ""):
        """
        Insert or update workflow into DB

        @param workflow_object: object to update or insert
        @param workflow_components: associate components with workflow object
        @param is_update: flag indicates if update or create is needed
        @param user_id: id of user which is performing action

        @return: Object DB entity
        """
        self.logger.info(f"User {user_id} is going to insert workflow with name {workflow_object.OBJECT_FULL_NAME}")
        # components need to be insert first
        new_components_name_id_pair, all_components_name_item_pair = \
            self.insert_new_components(workflow_components, user_id)
        try:
            self.logger.info(
                f"User {user_id} is going to insert/update workflow with name {workflow_object.OBJECT_FULL_NAME} ")

            # ==========================================================================================================
            # WORKFLOW AUDIT COLUMNS ENRICHMENT
            # ==========================================================================================================

            self._object_audit_columns_enrich(workflow_object, workflow_components, is_update, user_id)

            # ==========================================================================================================
            # ASSIGN CORRECT RELATIONS TO WORKFLOW
            # ==========================================================================================================

            self._relation_object_enrich(workflow_object, new_components_name_id_pair,
                                         all_components_name_item_pair)

            # ==========================================================================================================
            # SAVE OBJECT INTO DB
            # ==========================================================================================================

            if is_update:
                return self.update_record(workflow_object, user_id)
            return self.insert_record(workflow_object, user_id)
        # pylint: disable=bare-except
        # OperationalError exception is raised for operational errors,
        # such as issues with the database connection or transaction problems
        except Exception as exception:
            # delete the inserted  records in the components table
            Components.delete_many(self.session, Components.COMPONENT_ID.in_(new_components_name_id_pair.values()))
            raise exception

