from sqlalchemy import and_

from middleware.api.common.helpers import SortAndPaginate
from middleware.common.metadatabase.clients.meta_database_client import MetaDatabaseClient
from middleware.common.metadatabase.model.difw_metadb_model import ObjectsACL, Objects, Components, \
    ComponentTemplates, ComponentsTemplatesACL
from middleware.common.metadatabase.model.types.component_templates_acl_relation_types_enum import \
    ComponentTemplatesACLRelationTypesEnum
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum


class GlobalObjectsMetadataProvider(MetaDatabaseClient):
    """
    Database client which served actions related with global objects search
    """

    def get_global_objects(self, user_id: str, object_type: ObjectTypesEnum, object_name: str = None,
                           excluded_projects: list = None, current_project: str = None,
                           sort_and_paginate: SortAndPaginate = None):
        """
        Get global objects from DB
        @param user_id: user_id of the user
        @param object_type: ObjectTypesEnum of objects type to be retrieved
        @param object_name: used for regex filtration on object_name
        @param current_project: if populated obtain only objects from given project
        @param excluded_projects: if given do not obtain objects from these projects
        @param sort_and_paginate: if given do pagination logic
        @return: Object DB entities
        """
        self.logger.info(f"User {user_id} is going to retrieve global objects of type {object_type}")
        dynamic_query = self.session.query(Objects). \
            join(ObjectsACL, Objects.OBJECT_FULL_NAME == ObjectsACL.OBJECT_FULL_NAME).filter(
            Objects.OBJECT_TYPE == object_type)
        # substring filtration on object_name
        if object_name:
            dynamic_query = dynamic_query.filter(ObjectsACL.OBJECT_FULL_NAME.ilike(f"%{object_name}%"))
        # if current_project is true, the cross_project_search was false, we want to obtain only current project objects
        if current_project:
            dynamic_query = dynamic_query.filter(ObjectsACL.SUBJECT_ID == current_project)
        # it is possible that project owner is populated, but we want to exclude some additional owner
        # with which the object was shared, so for this it needs to be if and not elif
        if excluded_projects:
            dynamic_query = dynamic_query.filter(and_(ObjectsACL.RELATION_TYPE == ObjectsACLRelationTypesEnum.owner,
                                                      ObjectsACL.SUBJECT_ID.notin_(excluded_projects)))
        # add order so we can order it in DB
        objects_out, total_count = self.process_get_entries_and_count(sort_and_paginate, dynamic_query)

        return objects_out, total_count

    def get_global_component_templates(self, user_id: str, component_template_name: str = None,
                                       current_project: str = None, excluded_projects: list = None,
                                       sort_and_paginate: SortAndPaginate = None):
        """
        Get component templates from DB
        @param user_id: user_id of the user
        @param component_template_name: used for regex filtration on component_template_name
        @param excluded_projects: if given do not obtain objects from these projects
        @param current_project: if populated obtain only component templates from given project
        @param sort_and_paginate: if given do pagination logic
        @return: Component Templates DB entities
        """
        self.logger.info(f"User {user_id} is going to retrieve global objects of type component template")
        dynamic_query = self.session.query(ComponentTemplates). \
            join(Components, Components.COMPONENT_NAME == ComponentTemplates.TEMPLATE_NAME). \
            join(ComponentsTemplatesACL, ComponentsTemplatesACL.TEMPLATE_NAME == ComponentTemplates.TEMPLATE_NAME)
        # if given filter on component template name
        if component_template_name:
            dynamic_query = dynamic_query.filter(ComponentTemplates.TEMPLATE_NAME.ilike(f"%{component_template_name}%"))
        # if populated obtain only components which are accessible by current project
        if current_project:
            dynamic_query = dynamic_query.filter(ComponentsTemplatesACL.SUBJECT_ID == current_project)
        # it is possible that project owner is populated, but we want to exclude some additional owner
        # with which the component was shared, so for this it needs to be if and not elif
        if excluded_projects:
            dynamic_query = dynamic_query.filter(
                and_(ComponentsTemplatesACL.RELATION_TYPE == ComponentTemplatesACLRelationTypesEnum.owner,
                     ComponentsTemplatesACL.SUBJECT_ID not in excluded_projects))
        component_templates_out, total_count = self.process_get_entries_and_count(sort_and_paginate, dynamic_query)

        return component_templates_out, total_count
