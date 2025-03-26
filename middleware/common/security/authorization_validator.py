import re
from typing import List

from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_permission import EntityPermission
from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.metadatabase.component_templates_metadata_provider import ComponentTemplateMetadataProvider
from middleware.common.metadatabase.model.types.component_templates_acl_relation_types_enum import \
    ComponentTemplatesACLRelationTypesEnum
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.metadatabase.model.types.secrets_acl_relation_types_enum import SecretsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.security.action_type import ActionType
from middleware.common.security.authorization import Authorization
from middleware.common.helpers.exception import AuthorizationError


# pylint: disable=no-else-return
# pylint: disable=too-many-public-methods
class AuthorizationValidator(Authorization):
    """
    Auth validator class
    """
    TEMP_JWKS_FILE_NAME = "/tmp/public.json"

    def __init__(self, logger, metadatabase_connection, lambda_secrets_manager, user_isid, selected_subjects):
        super().__init__(logger, metadatabase_connection, lambda_secrets_manager)
        self.user_isid = user_isid
        self.selected_subjects = selected_subjects
        project = EntitySubject.filter_subjects_by_type(SubjectTypesEnum.project, selected_subjects, uselist=False)
        self.project_id = project.subject_id if project is not None else None
        self._component_template_metadata_provider = None
        # if user is not part of selected subjects, add it there
        if user_isid not in [subject.subject_id for subject in self.selected_subjects]:
            self.selected_subjects.append(EntitySubject(self.user_isid, SubjectTypesEnum.user))

    @property
    def component_template_metadata_provider(self):
        """
        _component_template_metadata_provider property
        """
        if self._component_template_metadata_provider is None:
            self._component_template_metadata_provider = ComponentTemplateMetadataProvider(self.logger,
                                                                                           self.metadatabase_connection,
                                                                                           self.lambda_secrets_manager)
        return self._component_template_metadata_provider

    @staticmethod
    def camel_to_snake(input_string):
        """
        Convert camel case string to snake case string

        @param input_string:  input string you want to convert
        @return:
        """
        input_string = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', input_string)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', input_string).lower()

    def _validate_permission(self, input_action_detail: dict, action_type: ActionType):
        """
        Validate if input_permission match criteria of assigned_permissions and
        return the effect related with matching assigned_permission

        @param input_action_detail: input action detail
        @param action_type: action type
        @return: effect of assigned permission matching the criteria from input permission. By default, it is deny
        """
        self.logger.info(
            f"Going to evaluate permission with detail {input_action_detail} and action type {action_type.value}")
        result_effect = PermissionEffectsEnum.deny
        self.selected_subjects = sorted(self.selected_subjects,
                                        key=lambda x: {'user': 1, 'group': 2, 'project': 3}.get(x.subject_type.value))
        for subject in self.selected_subjects:
            # get only permissions which are relevant for your subject and master owner of permission is project
            assigned_permissions = EntityPermission.from_metadb_objects(
                self.permission_metadata_provider.get_assigned_permissions_with_action_types(
                    user_id=self.user_isid,
                    subject_id=subject.subject_id,
                    action_type=action_type.value,
                    project_id=self.project_id))
            self.logger.info(f"assigned permissions for subject - {assigned_permissions}")
            self.logger.info(f"Validate permission {input_action_detail} against "
                             f"subject {subject.subject_type.value} with id {subject.subject_id}")
            # loop assigned permission and evaluated it
            for assigned_permission in assigned_permissions:
                for assigned_permission_action in assigned_permission.permission_actions:
                    if self.validate_action_details(
                            input_action_detail,
                            assigned_permission_action.action_detail,
                            action_type.get_attribute_mapping()):
                        result_effect = assigned_permission.effect
                        if result_effect == PermissionEffectsEnum.deny:
                            return PermissionEffectsEnum.deny
        return result_effect

    def validate_action_details(
        self,
        input_action_detail: dict,
        assigned_action_detail: dict,
        attribute_comparision_mapping: dict
    ):
        """
        Validate if input_permission match the criteria from assigned_permission_detail

        @param input_action_detail:
        @param assigned_action_detail:
        @param attribute_comparision_mapping:
        @return: True = input_permission match criteria of assigned_permission_details otherwise False
        """
        for input_permission_key, assigned_permission_attr_info in attribute_comparision_mapping.items():
            input_value = input_action_detail.get(input_permission_key)
            assigned_permission_value = assigned_action_detail[assigned_permission_attr_info['attribute_name']]

            # compare that all permission match the input permission rule
            # if at least one is false then return false
            if not self.attribute_comparator(input_value, assigned_permission_value):
                return False
        # if all attributes were validated and False value wasn't returned, then the permission object matches the
        # criteria and we can return True
        return True

    def attribute_comparator(self, input_value, assigned_permission_value):
        """
        Compare attribute from input permission with assigned permission

        @param input_value: input value from input permission. It is always string
        @param assigned_permission_value: input value from assigned permission. Can be list or string or regex
        @return: True = values are the same, False = values differ
        """
        # if the assigned permission attr value is list then compare all values
        values_to_compare = assigned_permission_value if isinstance(assigned_permission_value, list) else [
            assigned_permission_value]
        for value_to_compare in values_to_compare:
            if isinstance(value_to_compare, dict):
                value_to_compare = value_to_compare["defaultValue"]
            # if it is regex check if it match the pattern otherwise compare only value
            regex = self.check_and_get_regex(value_to_compare)
            if regex:
                match_value = regex.fullmatch(input_value) is not None
            else:
                match_value = (input_value == value_to_compare)
            # if there is at least one match then return True
            if match_value:
                return match_value
        return False

    def check_rights_of_user_against_subjects(self, assigned_group_ids: List):
        """
        Check if user is part of the subjects (for example user is part of group or project)
        @param assigned_group_ids: assigned group ids
        @return: None or exception
        """
        assigned_group_ids = [gr.lower() for gr in assigned_group_ids]
        self.logger.info("Going to validate group against assigned groups")
        selected_group = EntitySubject.filter_subjects_by_type(SubjectTypesEnum.group, self.selected_subjects,
                                                               uselist=False)
        # if group is not part of jwt then raise error
        # adding additional condition to the below line to check if selected group is not empty  since user
        # availability api will not have group details in api request eventually selected group will return None
        if selected_group and selected_group.subject_id.lower() not in assigned_group_ids:
            raise AuthorizationError(
                f"The group {selected_group} of user {self.user_isid}  is not preset in authorization token")

    def validate(self, action_type: ActionType, input_action_detail, **kwargs):
        """
        Validate input_permission

        @param action_type:
        @param input_action_detail:
        @return:
        """
        validation_method_name = self.camel_to_snake(action_type.value)
        self.logger.info(f"Start validating permission {action_type.value} for user "
                         f"{self.user_isid} within selected subjects {self.selected_subjects}")

        # check if there is specific validation method for action type
        if hasattr(self, f"validate_{validation_method_name}"):
            validate_result = getattr(self, f"validate_{validation_method_name}")(input_action_detail, **kwargs)
            self.logger.info(f"Result of permission validation is {validate_result.value}")

            return validate_result

        # if there is no specific validation method for action type then validate permission
        validate_result = self._validate_permission(input_action_detail, action_type)
        self.logger.info(f"Result of permission validation is {validate_result.value}")

        return validate_result

    def validate_execute_pipeline(self, input_action_detail, **kwargs):
        """
        Validate permission type executePipeline
        """

        action_type = ActionType.EXECUTE_PIPELINE
        effect = self._validate_acl_for_objects(
            kwargs.get("acl_relation_list"),
            action_type,
            input_action_detail,
            object_type=ObjectTypesEnum.pipeline,
            check_sharing=True
        )
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_delete_pipeline(self, input_action_detail, **kwargs):
        """
        Validate permission type deletePipeline
        """
        action_type = ActionType.DELETE_PIPELINE
        effect = self._validate_acl_for_objects(
            kwargs.get("acl_relation_list"),
            action_type,
            input_action_detail,
            object_type=ObjectTypesEnum.pipeline,
            check_sharing=False
        )
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_read_pipeline(self, input_action_detail, **kwargs):
        """
        Validate permission type read pipeline
        """
        action_type = ActionType.READ_PIPELINE
        effect = self._validate_acl_for_objects(
            kwargs.get("acl_relation_list"),
            action_type,
            input_action_detail,
            object_type=ObjectTypesEnum.pipeline,
            check_sharing=True,
            allow_action_to_project=True
        )
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_update_pipeline(self, input_action_detail, **kwargs):
        """
        Validate permission type updatePipeline
        """
        action_type = ActionType.UPDATE_PIPELINE
        effect = self._validate_acl_for_objects(
            kwargs.get("acl_relation_list"),
            action_type,
            input_action_detail,
            object_type=ObjectTypesEnum.pipeline,
            check_sharing=False
        )
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_update_secret(self, input_action_detail, **kwargs):
        """
        Validate permission type updateSecret
        """
        action_type = ActionType.UPDATE_SECRET
        effect = self._validate_acl_for_secrets(kwargs.get("acl_relation_list"), action_type,
                                                input_action_detail)
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_read_secret(self, input_action_detail, **kwargs):
        """
        Validate permission type readSecret
        """
        action_type = ActionType.READ_SECRET
        effect = self._validate_acl_for_secrets(kwargs.get("acl_relation_list"), action_type,
                                                input_action_detail)
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_read_secret_items(self, input_action_detail, **kwargs):
        """
        Validate permission type readSecretItems
        """
        action_type = ActionType.READ_SECRET_ITEMS
        effect = self._validate_acl_for_secrets(kwargs.get("acl_relation_list"), action_type,
                                                input_action_detail)
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_delete_secret(self, input_action_detail, **kwargs):
        """
        Validate permission type deleteSecret
        """
        action_type = ActionType.DELETE_SECRET
        effect = self._validate_acl_for_secrets(kwargs.get("acl_relation_list"), action_type,
                                                input_action_detail)
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_update_pipeline_template(self, input_action_detail, **kwargs):
        """
        Validate permission type updatePipelineTemplate
        """
        action_type = ActionType.UPDATE_PIPELINE_TEMPLATE
        effect = self._validate_acl_for_objects(kwargs.get("acl_relation_list"),
                                                action_type,
                                                input_action_detail,
                                                object_type=ObjectTypesEnum.pipeline_template,
                                                check_sharing=False,
                                                share_relation_type=ObjectsACLRelationTypesEnum.shared_template)
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_read_pipeline_template(self, input_action_detail, **kwargs):
        """
        Validate permission type readPipelineTemplate
        """

        action_type = ActionType.READ_PIPELINE_TEMPLATE
        effect = self._validate_acl_for_objects(kwargs.get("acl_relation_list"),
                                                action_type,
                                                input_action_detail,
                                                object_type=ObjectTypesEnum.pipeline_template,
                                                check_sharing=True,
                                                allow_action_to_project=True,
                                                share_relation_type=ObjectsACLRelationTypesEnum.shared_template)
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_delete_pipeline_template(self, input_action_detail, **kwargs):
        """
        Validate permission type deletePipelineTemplate
        """
        action_type = ActionType.DELETE_PIPELINE_TEMPLATE
        effect = self._validate_acl_for_objects(kwargs.get("acl_relation_list"),
                                                action_type,
                                                input_action_detail,
                                                object_type=ObjectTypesEnum.pipeline_template,
                                                check_sharing=False,
                                                share_relation_type=ObjectsACLRelationTypesEnum.shared_template)
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_update_component_template(self, input_action_detail, **kwargs):
        """
        Validate permission type updateComponentTemplate
        """
        action_type = ActionType.UPDATE_COMPONENT_TEMPLATE
        if kwargs.get("acl_relation_list"):
            self.logger.info(
                f"Evaluating ACL for {action_type} action type with action detail "
                f"{input_action_detail}")
            effect = self._validate_acl_for_component_template(kwargs.get("acl_relation_list"), check_sharing=False)
            if effect:
                return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_read_component_template(self, input_action_detail, **kwargs):
        """
        Validate permission type readComponentTemplate
        Here need to check permission itself + if component template is part of the project + if component template
        is shared with subjects from different project

        @param input_action_detail: detail for validating permissions
        @param kwargs: acl_relation_list - list of acl relations for particular template which we want to check
        """
        action_type = ActionType.READ_COMPONENT_TEMPLATE
        if kwargs.get("acl_relation_list"):
            self.logger.info(
                f"Evaluating ACL for {action_type} action type with "
                f"action detail {input_action_detail}")
            effect = self._validate_acl_for_component_template(kwargs.get("acl_relation_list"), check_sharing=True,
                                                               allow_action_to_project=True)
            if effect:
                return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_delete_component_template(self, input_action_detail, **kwargs):
        """
        Validate permission type deleteComponentTemplate

        @param input_action_detail: detail for validating permissions
        @param kwargs: acl_relation_list - list of acl relations for particular template which we want to check
        """
        action_type = ActionType.DELETE_COMPONENT_TEMPLATE

        if kwargs.get("acl_relation_list"):
            self.logger.info(
                f"Evaluating ACL for {action_type} action type with "
                f"action detail {input_action_detail}")
            effect = self._validate_acl_for_component_template(kwargs.get("acl_relation_list"), check_sharing=False)
            if effect:
                return effect
        return self._validate_permission(input_action_detail, action_type)

    def _validate_acl_for_component_template(self, acl_relation_list, check_sharing=True,
                                             allow_action_to_project=False):
        """
        Validate ACL for component template for owner relation.
        @param acl_relation_list: list of acl relations for particular template which we want to check
        @param check_sharing: flag indicates if we will also check sharing relation
        @param allow_action_to_project: flag indicates if the required action is allowed to project which is selected
        @return: PermissionEffectsEnum or none
        """
        if acl_relation_list:
            # first check if template is shared with user or respective subjects
            # it is enough to test if whatever ACL is type of shared
            # sharing with me?
            if check_sharing and EntityACL.filter_entity_acls(
                    acl_relation_list, ComponentTemplatesACLRelationTypesEnum.shared,
                    [subject.subject_id for subject in self.selected_subjects]):
                return PermissionEffectsEnum.allow

            owners = [self.user_isid, self.project_id] if allow_action_to_project else [self.user_isid]
            # am I owner?
            if EntityACL.filter_entity_acls(acl_relation_list, ComponentTemplatesACLRelationTypesEnum.owner, owners):
                return PermissionEffectsEnum.allow

            # if user is not owner and project is not owner then deny it because it is out of scope of project
            # user is not owner and template is not shared with whatever subject in selected subject hierarchy
            if not EntityACL.filter_entity_acls(
                    acl_relation_list, ComponentTemplatesACLRelationTypesEnum.owner, [self.project_id]):
                return PermissionEffectsEnum.deny
        return None

    def _validate_acl_for_secrets(self, acl_relation_list, action_type, input_action_detail):
        """
        Validate ACL for secrets for owner relation
        @param acl_relation_list: list of acl relations for particular secrets which we want to check
        @param action_type: action type to evaluate
        @param input_action_detail: action details which will be logged
        @return: PermissionEffectsEnum or none
        """
        if acl_relation_list:
            self.logger.info(
                f"Evaluating ACL for {action_type} action type with action detail "
                f"{input_action_detail}")
            # am I owner?
            if EntityACL.filter_entity_acls(
                    acl_relation_list, SecretsACLRelationTypesEnum.owner, [self.user_isid]):
                return PermissionEffectsEnum.allow

            # if user is not owner and project is not owner then deny it because it is out of scope of project
            # user is not owner and template is not shared with whatever subject in selected subject hierarchy
            if not EntityACL.filter_entity_acls(
                    acl_relation_list, SecretsACLRelationTypesEnum.owner, [self.project_id]):
                return PermissionEffectsEnum.deny
        return None

    # pylint: disable=too-many-arguments
    def _validate_acl_for_objects(
            self,
            input_acl_relation_list: [EntityACL],
            action_type: ActionType,
            input_action_detail: dict,
            object_type: ObjectTypesEnum,
            check_sharing=True,
            allow_action_to_project=False,
            share_relation_type: ObjectsACLRelationTypesEnum = ObjectsACLRelationTypesEnum.shared
    ):
        """
        Validate ACL for pipelines/pipeline templates for owner relation
        @param acl_relation_list: list of acl relations for particular secrets which we want to check
        @param action_type: action type to evaluate
        @param input_action_detail: action details which will be logged
        @param check_sharing: flag indicates if we will also check sharing relation
        @param allow_action_to_project: flag indicates if the required action is allowed to project which is selected
        @param share_relation_type: ObjectsACLRelationTypesEnum - which type of relation we want to filter upon,
        defaulted as shared, only for pipeline templates (and in future for workflow template) the shared_template
        is passed
        @return: PermissionEffectsEnum or none
        """
        object_name_attribute_name_mapping = {
            ObjectTypesEnum.pipeline: "pipelineName",
            ObjectTypesEnum.pipeline_template: "pipelineTemplateName",
            ObjectTypesEnum.workflow: "workflowName"
        }

        acl_relation_list = input_acl_relation_list
        if not input_acl_relation_list:
            object_name = None
            # get object name from input action detail
            # input_action_detail = {"pipelineName": "my_pipeline_name"}
            for _, action_type_attr_info in action_type.get_attribute_mapping().items():
                attribute_name = action_type_attr_info["attribute_name"]

                if attribute_name == object_name_attribute_name_mapping[object_type] \
                        and attribute_name in input_action_detail:
                    object_name = input_action_detail[attribute_name]
                    break

            if object_name:
                acl_relation_list = EntityACL.from_metadb_object_objects_acls(
                    self.objects_metadata_provider.get_objects_acl(
                        object_name=object_name,
                        user_id=self.user_isid,
                        object_type=object_type,
                    )
                )

        if acl_relation_list:
            self.logger.info(
                f"Evaluating ACL for {action_type} action type with action detail "
                f"{input_action_detail}")
            # first check if pipeline is shared with user or respective subjects
            # it is enough to test if whatever ACL is type of shared
            # sharing with me?
            if check_sharing and EntityACL.filter_entity_acls(
                    acl_relation_list, share_relation_type,
                    [subject.subject_id for subject in self.selected_subjects]):
                return PermissionEffectsEnum.allow

            # am I owner?
            owners = [self.user_isid, self.project_id] if allow_action_to_project else [self.user_isid]
            if EntityACL.filter_entity_acls(
                    acl_relation_list, ObjectsACLRelationTypesEnum.owner, owners):
                return PermissionEffectsEnum.allow

            # if user is not owner and project is not owner then deny it because it is out of scope of project
            # user is not owner and template is not shared with whatever subject in selected subject hierarchy
            if not EntityACL.filter_entity_acls(
                    acl_relation_list, ObjectsACLRelationTypesEnum.owner, [self.project_id]):
                return PermissionEffectsEnum.deny

        return None

    def validate_update_workflow(self, input_action_detail, **kwargs):
        """
        Validate permission type update workflow
        """
        action_type = ActionType.UPDATE_WORKFLOW
        effect = self._validate_acl_for_objects(kwargs.get("acl_relation_list"),
                                                action_type,
                                                input_action_detail,
                                                object_type=ObjectTypesEnum.workflow,
                                                check_sharing=False)
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_delete_workflow(self, input_action_detail, **kwargs):
        """
        Validate permission type delete workflow
        """
        action_type = ActionType.DELETE_WORKFLOW
        effect = self._validate_acl_for_objects(kwargs.get("acl_relation_list"), action_type,
                                                input_action_detail,
                                                object_type=ObjectTypesEnum.workflow,
                                                check_sharing=False)
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_read_workflow(self, input_action_detail, **kwargs):
        """
        Validate permission type read workflow
        """
        action_type = ActionType.READ_WORKFLOW
        effect = self._validate_acl_for_objects(kwargs.get("acl_relation_list"), action_type,
                                                input_action_detail,
                                                object_type=ObjectTypesEnum.workflow,
                                                check_sharing=True, allow_action_to_project=True)
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)

    def validate_execute_workflow(self, input_action_detail, **kwargs):
        """
        Validate permission type execute workflow
        """

        action_type = ActionType.EXECUTE_WORKFLOW
        effect = self._validate_acl_for_objects(kwargs.get("acl_relation_list"), action_type,
                                                input_action_detail,
                                                object_type=ObjectTypesEnum.workflow,
                                                check_sharing=True)
        if effect:
            return effect
        return self._validate_permission(input_action_detail, action_type)