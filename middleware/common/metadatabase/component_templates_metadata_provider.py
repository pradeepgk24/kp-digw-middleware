from sqlalchemy import and_, func

from middleware.api.common.helpers import SortAndPaginate, add_order_to_query
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.metadatabase.clients.meta_database_client import MetaDatabaseClient
from middleware.common.metadatabase.model.difw_metadb_model import ComponentTemplates, ComponentsTemplatesACL, \
    Components
from middleware.common.metadatabase.model.types.component_templates_acl_relation_types_enum import \
    ComponentTemplatesACLRelationTypesEnum


class ComponentTemplateMetadataProvider(MetaDatabaseClient):
    """
    Database client which served actions related with component templates
    """

    def get_component_templates(self, user_id: str, subject_ids: list, template_name: str, component_category: list,
                                component_type: list, sort_and_paginate: SortAndPaginate):

        """
        Gets component templates from DB which can be somehow accessible for user or selected subjects.
        Get all templates based on relation and subject ids
        :param user_id: logon user isid
        :param subject_ids:
        :param template_name: component template name
        :param component_category: list of categories
        :param component_type: list of categories
        :param sort_and_paginate:
        :return:
        """
        self.logger.info(
            f"User {user_id} going to get all component templates details based on ACL relation for "
            f"subjects = {subject_ids}")
        dynamic_query = self.session.query(ComponentTemplates). \
            join(Components, Components.COMPONENT_NAME == ComponentTemplates.TEMPLATE_NAME). \
            join(ComponentsTemplatesACL, ComponentsTemplatesACL.TEMPLATE_NAME == ComponentTemplates.TEMPLATE_NAME). \
            filter(ComponentsTemplatesACL.SUBJECT_ID.in_(subject_ids))
        if component_category:
            dynamic_query = dynamic_query.filter(Components.COMPONENT_TYPE_CATEGORY.in_(component_category))
        if component_type:
            dynamic_query = dynamic_query.filter(Components.COMPONENT_TYPE_NAME.in_(component_type))
        if template_name:
            dynamic_query = dynamic_query.filter(ComponentTemplates.TEMPLATE_NAME.ilike(f"%{template_name}%"))
        if sort_and_paginate and sort_and_paginate.sorted_conversion:
            dynamic_query = add_order_to_query(dynamic_query, Components, sort_and_paginate.sorted_conversion)
        return dynamic_query.all()

    def get_component_template(self, template_id: int, user_id: str):
        """
        Get component templates form DB

        :param user_id:
        :param template_id:

        :return: ComponentTemplates obj
        """
        self.logger.info(f"User {user_id} is going to retrieve template with id {template_id} ")
        return ComponentTemplates(TEMPLATE_ID=template_id).get_unique(self.session)

    def delete_component_template(self, template_id: int, user_id: str):
        """
        Delete component template

        :param user_id:
        :param template_id:
        :return: deleted ComponentTemplates obj
        """
        self.logger.info(f"User {user_id} is going to delete template with id {template_id} ")
        return ComponentTemplates(TEMPLATE_ID=template_id).delete(self.session)

    def insert_component_template(self, component_template: ComponentTemplates, user_id: str):
        """
        Add component template

        :param user_id:
        :param component_template:

        :return: inserted component template
        """
        self.logger.info(
            f"User {user_id} is going to insert component template with name {component_template.TEMPLATE_NAME} ")
        if component_template.rel_component:
            # enhance insert audit columns of related component record
            self.enrich_with_creation_audit_columns(component_template.rel_component, user_id)
        if component_template.rel_component_templates_acl:
            # enhance insert audit columns of related component record
            for acl in component_template.rel_component_templates_acl:
                self.enrich_with_creation_audit_columns(acl, user_id)
        component_template = self.insert_record(component_template, user_id)
        return component_template

    def update_component_template(self, component_template: ComponentTemplates, user_id: str):
        """
        Update component template

        :param user_id:
        :param component_template:

        :return: updated component template
        """
        self.logger.info(
            f"User {user_id} is going to update component template with name {component_template.TEMPLATE_NAME}")
        if component_template.rel_component:
            # enhance insert audit columns of related component record
            self.enrich_with_updating_audit_columns(component_template.rel_component, user_id)
        if component_template.rel_component_templates_acl:
            for acl in component_template.rel_component_templates_acl:
                self.enrich_with_updating_audit_columns(acl, user_id)
        return self.update_record(component_template, user_id)

    def delete_and_insert_into_component_templates_acl(self, component_template: ComponentTemplates, user_id: str,
                                                       acls: [EntityACL]):
        """
        Update component template sharing
        Replace existing shared ACLs with new one from request
        :param user_id:
        :param component_template:
        :param acls:
        :return: updated component template
        """
        self.logger.info(
            f"User {user_id} is going to rewrite ACLs for component template with id {component_template.template_id}")
        self.logger.info(f"User {user_id} is going to delete template with id {component_template.template_id} ")
        list_of_acl_to_remove = ComponentsTemplatesACL.get_many(
            self.session, and_(ComponentsTemplatesACL.TEMPLATE_ID == component_template.template_id,
                               ComponentsTemplatesACL.RELATION_TYPE == ComponentTemplatesACLRelationTypesEnum.shared))

        self.logger.info("Going to remove the existing acls")
        for existing_acl in list_of_acl_to_remove:
            existing_acl.delete(self.session, commit=False)
        for acl in acls:
            new_shard = ComponentsTemplatesACL(
                TEMPLATE_ID=component_template.template_id,
                TEMPLATE_NAME=component_template.template_name,
                SUBJECT_ID=acl.subject.subject_id,
                RELATION_TYPE=ComponentTemplatesACLRelationTypesEnum.shared)
            self.enrich_with_creation_audit_columns(new_shard, user_id)
            self.insert_record(new_shard, user_id, commit=False)
        return self.commit()

    # pylint: disable=E1102(not-callable)
    def exists_component_template(self, component_template_name: str, user_id: str = ""):
        """
        Check if component_template  with the specific name exists in MetaDB.

        :param component_template_name:
        :param user_id:

        :return: flag indicates if component template either exists or not
        """
        self.logger.info(f"User {user_id} is going to check if component template with name "
                         f"{component_template_name} exists")
        component_template_count = self.session.query(func.count(ComponentTemplates.TEMPLATE_NAME)). \
            filter(ComponentTemplates.TEMPLATE_NAME == component_template_name).scalar()
        return component_template_count > 0
