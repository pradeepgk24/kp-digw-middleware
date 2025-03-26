import json
import os
import base64
from sqlalchemy.exc import IntegrityError

from middleware.common.entity_management.entities.entity_project_account_settings import EntityProjectAccountSettings
from middleware.common.entity_management.entities.entity_project_general_settings import EntityProjectGeneralSettings
from middleware.common.entity_management.entities.entity_secret import EntitySecret
from middleware.common.entity_management.project_settings_management import ProjectSettingsManagement
from middleware.common.entity_management.secrets_management import SecretsManagement
from middleware.common.helpers.exception import EntityConflictError
from middleware.common.metadatabase.model.difw_metadb_model import ComponentTypes, PermissionActionTypes, Permissions, \
    PermissionActions, Subjects, PermissionsACL, Enumerators
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.metadatabase.model.types.permissions_acl_relation_types_enum import \
    PermissionsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.metadatabase.permissions_metadata_provider import PermissionMetadataProvider
from middleware.deploy.metadata_db_generator.db_component_generator import DBComponentGenerator
from middleware.common.metadatabase.definitions_metadata_provider import DefinitionsMetadataProvider
from middleware.common.metadatabase.subjects_metadata_provider import SubjectsMetadataProvider


class DMLGenerator(DBComponentGenerator):
    """
    Class for inserting of all metadata
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, args):
        super().__init__(args)
        self.user = "generator"
        self.project_id = "difw_admin_project"
        self.definitions_metadata_provider = DefinitionsMetadataProvider(
            self.logger,
            self.metadb_configuration.get("dbSecretManagerCredentialStorage", "difw-metadb-ui-credentials"),
            self.api_sm_client)

        self.permission_metadata_provider = PermissionMetadataProvider(
            self.logger,
            self.metadb_configuration.get("dbSecretManagerCredentialStorage", "difw-metadb-ui-credentials"),
            self.api_sm_client)

        self.subjects_metadata_provider = SubjectsMetadataProvider(
            self.logger,
            self.metadb_configuration.get("dbSecretManagerCredentialStorage", "difw-metadb-ui-credentials"),
            self.api_sm_client)
        self.delete_db_interactor_condition = f"FRAMEWORK_VERSION='{self.args.framework_version}'"

        self.project_settings_management = ProjectSettingsManagement(
            logger=self.logger,
            metadatabase_connection=self.metadb_configuration.get("dbSecretManagerCredentialStorage",
                                                                  "difw-metadb-ui-credentials"),
            lambda_secrets_manager=self.api_sm_client, user_isid=self.user, selected_subjects=[]
        )
        self.project_settings_management.project_id = self.project_id
        # get access to target AWS account
        aws_access_key, aws_secret_key, aws_session_token = \
            self.project_settings_management.get_project_aws_account_access_info()
        self.secret_management = SecretsManagement(
            logger=self.logger,
            metadatabase_connection=self.metadb_configuration.get("dbSecretManagerCredentialStorage",
                                                                  "difw-metadb-ui-credentials"),
            lambda_secrets_manager=self.api_sm_client, user_isid=self.user, selected_subjects=[],
            aws_access_key=aws_access_key, aws_secret_key=aws_secret_key, aws_session_token=aws_session_token,
            project_id=self.project_id
        )

    def generate(self, *args):
        """
        Main generate method
        :return:
        """
        self._insert_framework_version()
        self._insert_component_types("input_connector")
        self._insert_component_types("output_connector")
        self._insert_component_types("processor")
        self._insert_component_types("data_type")
        self._insert_component_types("transformer")
        self._insert_component_types("airflow_component")
        self._insert_component_types("data_transformation_tool")
        self._insert_component_types("pipeline_object")
        self._insert_permission_action_types()
        self._insert_generator_user()
        all_global_permissions = self._insert_global_permissions()
        admin_project = self._insert_admin_project(all_global_permissions["admin"])
        self._insert_account_settings(admin_project)
        self._insert_general_settings()
        self._insert_enumerator_categories()

    def _insert_general_settings(self):
        gen_sett_prj_repo = self.project_configuration.get("projectSpecificRepo", [])

        self.project_settings_management.insert_or_update_project_general_settings(
            EntityProjectGeneralSettings(project_id=self.project_id,
                                         resource_prefix=self.project_configuration.get("generalResourcePrefix", ""),
                                         project_group_id=gen_sett_prj_repo[0].get("projectGroupId", ""),
                                         jfrog_repository_id=gen_sett_prj_repo[0].get("repositoryId", "")
                                         if gen_sett_prj_repo else "",
                                         description="Main Admin project for UI",
                                         display_name="DIFW Admin",
                                         environment=self.project_configuration.get("name", "dev"),
                                         default_platform="Glue",
                                         onboard_email=self.project_configuration.get("onboardEmail",
                                                                                      "lukas.krolak@merck.com"),
                                         onboard_message=self.project_configuration.get("onboardMessage",
                                                                                        "Please for onboarding issues,"
                                                                                        " reach out to "
                                                                                        "lukas.krolak@merck.com.")),
            check_permission=False)

    def _insert_account_settings(self, admin_db_project):
        aws_account_options = self.project_configuration.get("apiSpecs", {}).get("computing", {}).get("awsAccount",
                                                                                                      {})
        airflow_account_options = self.project_configuration.get("apiSpecs", {}).get("computing", {}).get(
            "airflowInstance", {})
        databricks_options = self.project_configuration.get("apiSpecs", {}).get("computing", {}).get(
            "databricksAccount", {})
        github_options = self.project_configuration.get("apiSpecs", {}).get("github", {})

        # then save settings into DB, together with updated secrets
        self.project_settings_management.insert_or_update_project_account_settings(
            EntityProjectAccountSettings(project_id=admin_db_project.SUBJECT_ID,
                                         account_type=ProjectAccountTypesEnum.aws,
                                         account_details=aws_account_options),
            False)
        if airflow_account_options:
            self._resolve_airflow_account_secrets(airflow_account_options)
            self.project_settings_management.insert_or_update_project_account_settings(
                EntityProjectAccountSettings(project_id=admin_db_project.SUBJECT_ID,
                                             account_type=ProjectAccountTypesEnum.airflow,
                                             account_details=airflow_account_options),
                False)
        if databricks_options:
            self._resolve_databricks_account_secrets(databricks_options)
            self.project_settings_management.insert_or_update_project_account_settings(
                EntityProjectAccountSettings(project_id=admin_db_project.SUBJECT_ID,
                                             account_type=ProjectAccountTypesEnum.databricks,
                                             account_details=databricks_options),
                False)
        if github_options:
            self._resolve_github_account_secrets(github_options)
            self.project_settings_management.insert_or_update_project_account_settings(
                EntityProjectAccountSettings(project_id=admin_db_project.SUBJECT_ID,
                                             account_type=ProjectAccountTypesEnum.github,
                                             account_details=github_options),
                False)

    def _generate_or_update_account_secret(self, account_secret_object, secret_name_key, account_type):
        """
        Generated secret for default project setting. If exists then only update secretName of account_secret_object

        :param account_secret_object: object from project setting account config. It needs to contain secretManagerName
        :param secret_name_key: key which will be part of secret name
        :param account_type: type of account to update

        :return: created or updated secret
        """
        try:
            secret_manager_name = account_secret_object["secretManagerName"]
            secret_name = f"difw_{self.project_id}_{secret_name_key}"
            if not self.secret_management.get_secret(secret_name, False, False, False):
                self.logger.warning(
                    f"The secret {secret_name} is going to be generated for account of type {account_type}")
                return self.secret_management.create_secret(
                    EntitySecret(secret_name=secret_name, secret_manager_name=secret_manager_name,
                                 description=f"Generated secret for account {account_type} with key {secret_name_key}",
                                 acl=[]),
                    check_permission=False, do_not_raise_entity_conflict_if_exists=True)
            account_secret_object["secretName"] = secret_name
            del account_secret_object["secretManagerName"]
            return None
        except EntityConflictError:
            return None

    def _resolve_github_account_secrets(self, github_account_details):
        """
        Resolve - create/get secrets from GitHub

        :param github_account_details:
        """
        self._generate_or_update_account_secret(
            github_account_details["accessToken"],
            "github_service_user",
            "github"
        )

    def _resolve_airflow_account_secrets(self, airflow_account_details):
        """
        Resolve - create/get secrets from Airflow

        :param airflow_account_details:
        """
        eks_airflow_config = airflow_account_details.get("eksBased")
        if eks_airflow_config:
            self._generate_or_update_account_secret(
                eks_airflow_config["eksGitAccessToken"],
                "airflow_eks_git_user",
                "airflow")

        ec2_airflow_config = airflow_account_details.get("ec2Based")
        if ec2_airflow_config:
            self._generate_or_update_account_secret(
                ec2_airflow_config["sshCredentialsPrivateKey"],
                "airflow_ssh_user",
                "airflow")

        api_access_config = airflow_account_details.get("apiAccess")
        if api_access_config:
            self._generate_or_update_account_secret(
                api_access_config["apiUserPassword"],
                "airflow_api_password",
                "airflow")

    def _resolve_databricks_account_secrets(self, databricks_account_details):
        """
        Resolve - create/get secrets from Databricks

        :param databricks_account_details:
        """
        self._generate_or_update_account_secret(
            databricks_account_details["securityApiToken"],
            "dbx_api_user",
            "databricks")

    def _insert_generator_user(self):
        """
        Insert generator user
        """
        self.subjects_metadata_provider.insert_or_update_subject(
            Subjects(SUBJECT_ID=self.user, SUBJECT_TYPE=SubjectTypesEnum.user, DISPLAY_NAME="Metadb user",
                     DESCRIPTION="User responsible for generation of metadb", IS_ENABLED=True),
            self.user
        )

    def _insert_admin_project(self, admin_permission):
        """
        Insert admin user

        :param admin_permission: admin permissions
        """
        difw_project_subject = self.subjects_metadata_provider.insert_or_update_subject(
            Subjects(SUBJECT_ID=self.project_id, SUBJECT_TYPE=SubjectTypesEnum.project, DISPLAY_NAME="DIFW Admin",
                     DESCRIPTION="Main Admin project for UI", IS_ENABLED=True),
            self.user
        )
        # assign admin permission to admin project
        try:
            self.permission_metadata_provider.insert_permission_subject_relationship(
                PermissionsACL(PERMISSION_NAME=admin_permission.PERMISSION_NAME,
                               SUBJECT_ID=difw_project_subject.SUBJECT_ID,
                               RELATION_TYPE=PermissionsACLRelationTypesEnum.assigned,
                               MASTER_OWNER=self.project_id),
                self.user
            )
        except IntegrityError:
            # ignore if relation exists already
            pass
        return difw_project_subject

    def _insert_framework_version(self):
        """
        Insert framework version
        """
        self.logger.info(f"Going to insert framework version {self.args.framework_version} ...")
        # first get latest FW version
        fw_version = self.definitions_metadata_provider.get_latest_framework_version()

        # compare if latest FW version is the same FW version we wanted to add and
        # prevent adding already existing fw version
        if fw_version and fw_version.DIFW_CORE_VERSION == self.args.framework_version:
            self.logger.info("Skipping adding of FW version, because it already exists as latest")
            return

        new_version_is_latest = True
        if fw_version:
            def version_tuple(input_version):
                if "-" in input_version:
                    input_version = input_version[:input_version.index("-")]
                return tuple(map(int, input_version.split(".")))

            # check if the current version is the latest one
            new_version_is_latest = version_tuple(fw_version.DIFW_CORE_VERSION) < version_tuple(
                self.args.framework_version)

        # if already existing latest FW version has lower version that new one, that disable the latest flag for it
        # fw_version = some latest FW already exist in DB
        # new_version_is_latest = the new FW has bigger version
        if fw_version and new_version_is_latest:
            fw_version.IS_LATEST = False
            self.definitions_metadata_provider.update_framework_version(fw_version, self.user)
        # finally add new latest fw version
        self.definitions_metadata_provider.add_framework_version(self.args.framework_version,
                                                                 self.user,
                                                                 is_latest=new_version_is_latest)

        # pylint: disable= no-self-use
        def convert_svg_to_string(self, svg_file):
            """
            Converts the given svg image to base64 string

            :param svg_file
            :returns base 64 string of the image.
            """
            with open(svg_file, "rb") as file_obj:
                # Read SVG file as bytes
                svg_bytes = file_obj.read()

                # Encode SVG bytes as base64
                base64_str = base64.b64encode(svg_bytes).decode("utf-8")
                return base64_str

        def _insert_component_types(self, component_type_category):
            """
            Insert input connector definitions
            """
            # insert connection types
            self.logger.info(f"Going to insert component type of category  {component_type_category}...")

            framework_branch = "develop" if "SNAPSHOT" in self.args.framework_version \
                else f"release/{self.args.framework_version}"

            for filename in os.scandir(f"{self.step_definitions_path}{os.sep}{component_type_category}"):
                if filename.is_file():
                    self.logger.info(f"Going to process component type file {filename.path}")
                    step_definition = self._load_json_entity_definition(filename.path)
                    icon_path = (f"{self.step_definitions_path}{os.sep}{component_type_category}{os.sep}{'icons'}" \
                                 f"{os.sep}{filename.name.split('.')[0]}" + ".svg")
                    if os.path.exists(icon_path):
                        icon_str = self.convert_svg_to_string(icon_path)
                        step_definition.update({"uiProperties": {"icon": icon_str}})

                    # update documentation link
                    step_definition["documentationLink"] = step_definition.get(
                        "documentationLink",
                        "https://github.com/merck-gen/mf-difw-core/tree/develop/documentation/configuration/steps").format(
                        branch=framework_branch
                    )
                    self.definitions_metadata_provider.insert_or_update_component_type(ComponentTypes(
                        COMPONENT_TYPE_NAME=step_definition["componentType"],
                        COMPONENT_TYPE_CATEGORY=component_type_category,
                        DEFINITION=json.dumps(step_definition, indent=4),
                        DIFW_CORE_VERSION=self.args.framework_version
                    ), self.user)

        def _insert_global_permissions(self):
            """
            Insert global permissions into MetaDB
            """
            # insert connection types
            self.logger.info("Going to insert global permissions...")

            all_global_permissions = {}
            # list all global permissions
            for filename in os.scandir(f"{self.global_permission_path}"):
                if filename.is_file():
                    self.logger.info(f"Going to process global permission file {filename.path}")
                    global_permission = self._load_json_entity_definition(filename.path)
                    permission_name = global_permission["permissionName"]
                    permission = Permissions(
                        PERMISSION_NAME=permission_name,
                        EFFECT=PermissionEffectsEnum.from_str(global_permission["effect"]),
                        DESCRIPTION=global_permission["description"],
                        IS_ENABLED=True
                    )
                    # TODO
                    # permission.rel_permissions_acl.append(
                    #     PermissionsACL(PERMISSION_NAME=permission_name, SUBJECT_ID=self.user,
                    #                    RELATION_TYPE=PermissionsACLRelationTypesEnum.owner))
                    for permission_action in global_permission["permissionActions"]:
                        permission.rel_permission_actions.append(
                            PermissionActions(
                                PERMISSION_NAME=permission_name,
                                ACTION_TYPE=permission_action["actionType"],
                                ACTION_DETAIL=json.dumps(permission_action["actionDetail"], indent=4)
                            ))
                    all_global_permissions[
                        permission_name] = self.permission_metadata_provider.insert_or_update_permission(
                        permission, self.user)
            return all_global_permissions

        def _insert_permission_action_types(self):
            """
            Insert all permission action types
            """
            # insert connection types
            self.logger.info("Going to insert permission action types...")

            for filename in os.scandir(f"{self.permission_actions_path}"):
                if filename.is_file():
                    self.logger.info(f"Going to process permission action type file {filename.path}")
                    action_definitions = self._load_json_entity_definition(filename.path)
                    for action_type in action_definitions:
                        self.definitions_metadata_provider.insert_or_update_permission_action_type(
                            PermissionActionTypes(
                                ACTION_TYPE=action_type["actionType"],
                                DEFINITION=json.dumps(action_type["actionDefinition"], indent=4),
                                DESCRIPTION=action_type["description"]
                            ), self.user)

        def _load_json_entity_definition(self, step_definition_file):
            """
            Load json step definition file

            :param step_definition_file:
            :return: dict of json
            """
            with open(step_definition_file) as json_file:
                basic_json = json.load(json_file)
                json_result = self._resolve_json_import(basic_json, os.path.dirname(step_definition_file), None)
                return json_result

        def _resolve_json_import(self, json_element, base_path, key):
            """
            Resolve custom imports in JSON

            :param json_element:
            :param base_path:
            :param key:
            :return: resolved json element
            """
            if isinstance(json_element, dict):
                new_json_dict = {}
                for json_element_key, json_element_value in json_element.items():
                    new_json_dict[json_element_key] = self._resolve_json_import(json_element_value, base_path,
                                                                                json_element_key)
                return new_json_dict

            if isinstance(json_element, list):
                new_json_items = []
                for json_element_item in json_element:
                    new_jsom_element_item = self._resolve_json_import(json_element_item, base_path, key)
                    if isinstance(new_jsom_element_item, list):
                        new_json_items.extend(new_jsom_element_item)
                    else:
                        new_json_items.append(new_jsom_element_item)
                return new_json_items

            if isinstance(json_element, str) and json_element.startswith("#extendByFile:"):
                json_element = self._load_json_entity_definition(
                    f"{base_path}{os.sep}{json_element.split(':')[1].strip()}")
            return json_element

        def _insert_enumerator_categories(self):
            """
            Insert enumerator categories into MetaDB
            """
            self.logger.info("Going to insert enumerator categories...")

            for filename in os.scandir(f"{self.enumerator_categories_path}"):
                if filename.is_file():
                    self.logger.info(f"Going to process enumerator category file {filename.path}")
                    enumerator_definitions = self._load_json_entity_definition(filename.path)
                    # category = name of file without .json extension
                    enumerator_category = filename.name.replace(".json", "")
                    for enumerator in enumerator_definitions:
                        self.definitions_metadata_provider.insert_or_update_enumerator_entry(
                            Enumerators(
                                ENUMERATOR_CATEGORY=enumerator_category,
                                ENUMERATOR_VALUE=enumerator["enumeratorValue"],
                                DISPLAY_NAME=enumerator["displayName"]
                            ), self.user)
