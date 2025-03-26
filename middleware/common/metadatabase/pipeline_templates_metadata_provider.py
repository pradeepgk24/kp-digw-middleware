from sqlalchemy import and_

from middleware.api.common.helpers import SortAndPaginate, add_order_to_query
from middleware.common.metadatabase.model.difw_metadb_model import Objects, ObjectsACL, Components
from middleware.common.metadatabase.model.types.object_status_enum import ObjectStatusEnum
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.objects_metadata_provider import ObjectsMetadataProvider


class PipelineTemplateMetadataProvider(ObjectsMetadataProvider):
    """
    Database client which served actions related with pipeline templates
    """

    def get_pipeline_template(self, pipeline_template_name: str, pipeline_template_version: str, user_id: str):
        """
        Get pipeline templates form DB

        @param pipeline_template_name:
        @param pipeline_template_version:
        @param user_id:

        @return: PipelineTemplate obj
        """
        self.logger.info(f"User {user_id} is going to retrieve pipeline template with name {pipeline_template_name}")
        return self.get_object(pipeline_template_name, pipeline_template_version, ObjectTypesEnum.pipeline_template,
                               user_id)

    def check_pipeline_template_exists(self, pipeline_template_name, pipeline_template_version: str = "1.0.0",
                                       user_id: str = ""):
        """
        Check if pipeline template with the specific name and version exists
        @param pipeline_template_name:
        @param pipeline_template_version:
        @param user_id:
        @return: flag indicates if pipeline exists  either exists or not
        """
        self.logger.info(f"User {user_id} is going to check if pipeline template with name {pipeline_template_name} "
                         f"and version {pipeline_template_version} exists")
        return self.exists_object(pipeline_template_name, pipeline_template_version, user_id,
                                  ObjectTypesEnum.pipeline_template)

    def _enrich_pipeline_template_with_audit_columns(self, pipeline_template_object: Objects,
                                                     pipeline_template_components: [Components],
                                                     user_id: str, is_update=False):
        """
        Enrich audit columns for pipeline template DB object
        @param pipeline_template_object: object to enrich
        @param pipeline_template_components: associate components with pipeline object
        @param user_id: id of user which is performing action
        @param is_update: flag indicates if update or create is needed
        """
        if pipeline_template_object.rel_objects_acl:
            # enhance insert audit columns of related component record
            for acl in pipeline_template_object.rel_objects_acl:
                if is_update:
                    self.enrich_with_updating_audit_columns(acl, user_id)
                else:
                    self.enrich_with_creation_audit_columns(acl, user_id)

        # loop all pipeline_components and enrich it with update columns
        for pipeline_template_step in pipeline_template_components:
            if is_update:
                self.enrich_with_updating_audit_columns(pipeline_template_step, user_id)
            # in case it is creation, the audit columns are enrichment within method insert_new_components

    def insert_or_update_pipeline_template(self, pipeline_template_object: Objects,
                                           pipeline_template_components: [Components], user_id: str,
                                           is_update=False, ):
        """
        Insert or update pipeline templates into DB

        @param pipeline_template_object: object to update or insert
        @param pipeline_template_components: associate components with pipeline object
        @param user_id: id of user which is performing action
        @param is_update: flag indicates if update or create is needed


        @return: Object DB entity
        """
        self.logger.info(
            f"User {user_id} is going to insert pipeline template with name "
            f"{pipeline_template_object.OBJECT_FULL_NAME}")
        new_components_name_id_pair, all_components_name_item_pair = \
            self.insert_new_components(pipeline_template_components, user_id)
        try:
            self.logger.info(
                f"User {user_id} is going to insert/update pipeline template with name "
                f"{pipeline_template_object.OBJECT_FULL_NAME} ")

            # enrich with audit columns
            self._enrich_pipeline_template_with_audit_columns(pipeline_template_object, pipeline_template_components,
                                                              user_id,
                                                              is_update)
            # assign relations
            self._relation_object_enrich(pipeline_template_object, new_components_name_id_pair,
                                         all_components_name_item_pair)

            # insert/update to DB
            if is_update:
                # in case of update we need to reapply owners back to the acl
                return self.update_record(pipeline_template_object, user_id)
            return self.insert_record(pipeline_template_object, user_id)
        # pylint: disable=bare-except
        # OperationalError exception is raised for operational errors,
        # such as issues with the database connection or transaction problems
        except Exception as exception:
            # delete the inserted  records in the components table
            Components.delete_many(self.session, Components.COMPONENT_ID.in_(new_components_name_id_pair.values()))
            raise exception

    def delete_pipeline_template(self, pipeline_template_name: str, pipeline_template_version: str, user_id: str):
        """
        Delete pipeline template

        @param pipeline_template_name:
        @param pipeline_template_version:
        @param user_id:
        @return: deleted pipeline template obj
        """
        self.logger.info(f"User {user_id} is going to delete pipline template with  {pipeline_template_name} ")
        return self.delete_object(object_name=pipeline_template_name, user_id=user_id,
                                  object_version=pipeline_template_version,
                                  object_type=ObjectTypesEnum.pipeline_template)

    def update_pipeline_template_assigned_acl_list(self, pipeline_template_name: str, new_assigned_acls: list,
                                                   user_id: str, pipeline_template_version: str = "1.0.0"):
        """
        update the pipeline_template acls with new values for relationship shared_template

        @param pipeline_template_name
        @param new_assigned_acls - list of new acls that will be added to Objects ACL
        @param user_id:
        @param pipeline_template_version
        """
        self.update_object_assigned_acl_list(object_name=pipeline_template_name,
                                             acls=new_assigned_acls,
                                             user_id=user_id,
                                             object_version=pipeline_template_version,
                                             object_type=ObjectTypesEnum.pipeline_template,
                                             relation_type=ObjectsACLRelationTypesEnum.shared_template)

    def get_pipeline_templates(self, user_id: str, pipeline_template_name: str = None, status: str = None,
                               subject_ids: list = None, sort_and_paginate: SortAndPaginate = None):
        """
        Gets all pipeline templates from DB.

        @param user_id: logon user isid
        @param pipeline_template_name:
        @param status:
        @param subject_ids:
        @param sort_and_paginate:

        @return:  pipeline templates Object DB entity
        """
        self.logger.info(f"user {user_id} is going to retrieve all pipeline templates from DB")
        dynamic_query = self.session.query(Objects). \
            join(ObjectsACL, Objects.OBJECT_FULL_NAME == ObjectsACL.OBJECT_FULL_NAME). \
            filter(and_(Objects.OBJECT_TYPE == ObjectTypesEnum.pipeline_template.value,
                        ObjectsACL.SUBJECT_ID.in_(subject_ids)))

        # filter the data on basis of status of pipeline template
        if status == ObjectStatusEnum.drafted.value:
            dynamic_query = dynamic_query.filter(Objects.IS_DRAFT.is_(True))
        elif status == ObjectStatusEnum.readyToUse.value:
            dynamic_query = dynamic_query.filter(Objects.IS_DRAFT.is_not(True))
        # if pipeline_template_name is given (or substring) then filter the data based on substring
        if pipeline_template_name:
            dynamic_query = dynamic_query.filter(Objects.OBJECT_FULL_NAME.ilike(f"%{pipeline_template_name}%"))
        if sort_and_paginate and sort_and_paginate.sorted_conversion:
            dynamic_query = add_order_to_query(dynamic_query, Objects, sort_and_paginate.sorted_conversion)

        return dynamic_query.all()
