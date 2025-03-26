from middleware.api.common.helpers import paginate_entries, SortAndPaginate
from middleware.common.entity_management.entities.entity_component_template import EntityComponentTemplate
from middleware.common.entity_management.entity_management import EntityManagement
from middleware.common.entity_management.project_settings_management import ProjectSettingsManagement
from middleware.common.helpers.exception import AuthorizationError, NoDataError
from middleware.common.metadatabase.component_templates_metadata_provider import ComponentTemplateMetadataProvider
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.security.action_type import ActionType


class ComponentTemplatesManagement(EntityManagement):
    """
    component templates management
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._project_settings_management = None
        self._component_templates_metadata_provider = None
        self._secret_management = None
        self.refresh_aws_tokens(self.project_settings_management)

    @property
    def project_settings_management(self):
        """
        project settings management property
        """
        if self._project_settings_management is None:
            self._project_settings_management = ProjectSettingsManagement(
                logger=self.logger, metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
                selected_subjects=self.selected_subjects)
        return self._project_settings_management

    @property
    def component_templates_metadata_provider(self):
        """
        component_template_provider property
        """
        if self._component_templates_metadata_provider is None:
            self._component_templates_metadata_provider = ComponentTemplateMetadataProvider(
                self.logger, self.metadatabase_connection, self.lambda_secrets_manager)
        return self._component_templates_metadata_provider

    def get_component_template(self, template_id: int = None):
        """
        Get component template detail

        :param template_id:

        :return: EntityComponentTemplate
        """
        self.logger.info(f"Going to retrieve component template with id {template_id}")
        entity_component_template = EntityComponentTemplate.from_metadb_object(
            self.component_templates_metadata_provider.get_component_template(
                template_id, self.user_isid))
        if entity_component_template is None:
            raise NoDataError(f"Component template with id {template_id} does not exist")
        if self.auth_validator.validate(
                ActionType.READ_COMPONENT_TEMPLATE,
                {"componentTemplateName": entity_component_template.template_name},
                acl_relation_list=entity_component_template.acl) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} has no permission "
                f"to read component template with ID {template_id}")
        return entity_component_template

    def get_component_templates(self, template_name: str = None, component_category: list = None,
                                component_type: list = None, sort_and_paginate: SortAndPaginate = None,
                                limited_view: bool = False):
        """
        Get component templates
        :param template_name: optional, filter on substring component template name
        :param component_category: optional, filter on category inside of given list
        :param component_type:
        :param sort_and_paginate: dictionary containing possible sorting and pagination info
        :param limited_view:
        :return: list of EntityComponentTemplate
        """
        self.logger.info("Going to retrieve component templates")
        # get from DB all templates where selected subjects are owner of templates or it is shared with them
        component_templates = EntityComponentTemplate.from_metadb_objects(
            self.component_templates_metadata_provider.
            get_component_templates(self.user_isid, self.selected_subject_ids, template_name, component_category,
                                    component_type, sort_and_paginate))
        # if there are no templates then raise no data error
        if not component_templates:
            raise NoDataError("There are no component templates, which you can view based on given filters")
        self.logger.info(f"Validating read permissions of user {self.user_isid}.")

        component_templates_result = []
        for template in component_templates:
            if self.auth_validator.validate(
                    ActionType.READ_COMPONENT_TEMPLATE,
                    {"componentTemplateName": template.template_name},
                    acl_relation_list=template.acl) == PermissionEffectsEnum.deny:
                continue
            component_templates_result.append(template)
        total_count = len(component_templates_result)
        component_templates_result_list = [ct.to_json_dict(limited_view) for ct in component_templates_result]
        component_templates_result = paginate_entries(component_templates_result_list, sort_and_paginate)
        if not component_templates_result:
            raise NoDataError("There are no component templates, which you can view based on given filters")
        return component_templates_result, total_count

    def delete_component_templates(self, template_id: int = None):
        """
        Delete component templates

        :param template_id:

        :return: deleted EntityComponentTemplate
        """
        self.logger.info(f"Going to delete component template with id {template_id}")
        component_template_to_delete = EntityComponentTemplate.from_metadb_object(
            self.component_templates_metadata_provider.get_component_template(
                template_id, self.user_isid
            ))
        if component_template_to_delete is None:
            raise NoDataError(f"Component template with id {template_id} does not exist")
        # if user is owner of template, then you have rights to delete it
        if self.auth_validator.validate(
                ActionType.DELETE_COMPONENT_TEMPLATE,
                {"componentTemplateName": component_template_to_delete.template_name},
                acl_relation_list=component_template_to_delete.acl) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} has no permission "
                f"to delete component template with ID {template_id}")
        return EntityComponentTemplate.from_metadb_object(
            self.component_templates_metadata_provider.delete_component_template(template_id=template_id,
                                                                                 user_id=self.user_isid))

    def insert_component_template(self, component_template: EntityComponentTemplate):
        """
        Create component templates

        :param component_template:
        :return: created template represented by object EntityComponentTemplate
        """
        if self.auth_validator.validate(
                ActionType.CREATE_COMPONENT_TEMPLATE, {}) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} has no permission "
                f"to create component template")
        # add owner into component
        component_template.acl.extend(self.create_component_templates_owner_acls())
        # insert component template, if there is any conflict error, the error will be returned and transaction reverted
        component_template_to_insert = EntityComponentTemplate.from_metadb_object(
            self.component_templates_metadata_provider.insert_component_template(
                component_template.to_metadb_object(),
                self.user_isid))
        return component_template_to_insert

    def update_component_template(self, component_template: EntityComponentTemplate):
        """
        Update component templates

        :param component_template:

        :return: list of EntityComponentTemplate
        """
        self.logger.info(f"Going to update component template with id {component_template.template_id}")
        component_template_to_update = EntityComponentTemplate.from_metadb_object(
            self.component_templates_metadata_provider.get_component_template(
                component_template.template_id, self.user_isid
            ))
        if component_template_to_update is None:
            raise NoDataError(f"Component template with id {component_template.template_id} does not exists in db")
        if self.auth_validator.validate(
                ActionType.UPDATE_COMPONENT_TEMPLATE,
                {"componentTemplateName": component_template.template_name},
                acl_relation_list=component_template_to_update.acl) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} has no permission "
                f"to update component template with ID {component_template.template_id}")
        return EntityComponentTemplate.from_metadb_object(
            self.component_templates_metadata_provider.update_component_template(
                component_template.to_metadb_object(), self.user_isid))

    def update_component_template_sharing(self, template_id: int, acls: list):
        """
        Update component templates sharing

        :param template_id:
        :param acls:
        :return: list of EntityComponentTemplate
        """
        self.logger.info(f"Going to update component template sharing with id {template_id}")
        component_template_to_update = EntityComponentTemplate.from_metadb_object(
            self.component_templates_metadata_provider.get_component_template(template_id, self.user_isid))
        if component_template_to_update is None:
            raise NoDataError(f"Component template with id {template_id} does not exists in db")
        if self.auth_validator.validate(
                ActionType.UPDATE_COMPONENT_TEMPLATE,
                {"componentTemplateName": component_template_to_update.template_name},
                acl_relation_list=component_template_to_update.acl) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"User {self.user_isid} under group {self.group_id} and project {self.project_id} has no permission "
                f"to update component template with ID {template_id}")
        # delete old shared and insert new acl
        self.component_templates_metadata_provider.delete_and_insert_into_component_templates_acl(
            component_template_to_update, self.user_isid, acls)
        return component_template_to_update

    def check_component_template_existence(self, component_template_name: str) -> bool:
        """
        Check component template existence, return True if component template with same name does exists,
        else raises NoDataError

        :param component_template_name: name of component template name.

        """
        self.logger.info(f"User {self.user_isid} starts method check_component_template_existence"
                         f" with component template name={component_template_name}")
        exists = self.component_templates_metadata_provider.exists_component_template(component_template_name,
                                                                                      self.user_isid)
        if not exists:
            raise NoDataError(
                f"component template with name {component_template_name} does not exist")
        return True
