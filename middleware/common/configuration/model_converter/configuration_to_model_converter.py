import copy

from common.configuration.configuration_utils import ConfigurationUtils
from common.secrets.secrets import SecretValue
from middleware.common.configuration.model_converter.config_model_converter import ConfigModelConverter
from middleware.common.configuration.model_converter.configuration_utils import map_dict_to_destination
from middleware.common.entity_management.definitions_metadata_management import DefinitionsMetadataManagement
from middleware.common.entity_management.entities.entity_airflow_notification import EntityAirflowNotification
from middleware.common.entity_management.entities.entity_airflow_notifications import EntityAirflowNotifications
from middleware.common.entity_management.entities.entity_component_type import EntityComponentType
from middleware.common.entity_management.entities.entity_glue_database import EntityGlueDatabase
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline
from middleware.common.entity_management.entities.entity_pipeline_steps import EntityPipelineSteps
from middleware.common.entity_management.entities.entity_pipeline_table import EntityPipelineTable, \
    EntityPipelineTableStep
from middleware.common.entity_management.entities.entity_secret import EntitySecret
from middleware.common.entity_management.entities.entity_unity_catalog import EntityUnityCatalog
from middleware.common.entity_management.entities.entity_unity_schema import EntityUnitySchema
from middleware.common.entity_management.secrets_management import SecretsManagement
from middleware.common.helpers.exception import ConfigurationModelConvertorError
from pipeline.common.helpers.utils import resolve_dependencies


# pylint: disable=too-many-instance-attributes, duplicate-code
class ConfigurationConverter(ConfigModelConverter):
    """
    Class for converting model to Yaml configuration/dataset.
    """
    DIFW_STEP_CATEGORY_MULTISTEP_FLAG = {
        ConfigModelConverter.DIFW_STEP_CATEGORY_INPUT: False,
        ConfigModelConverter.DIFW_STEP_CATEGORY_TRANSFORMATION: True,
        ConfigModelConverter.DIFW_STEP_CATEGORY_OUTPUT: False,
        ConfigModelConverter.DIFW_STEP_CATEGORY_PROCESS: True,
    }
    # list of order in DIFW steps
    # each item contains
    #  - difw_step_category_name = name of DIFW step category
    #  - multistep_category = flag indicates if it particular category may be more steps
    DIFW_STEP_CATEGORY_ORDER = [
        {"difw_step_category_name": ConfigModelConverter.DIFW_STEP_CATEGORY_INPUT,
         "multistep_category": DIFW_STEP_CATEGORY_MULTISTEP_FLAG[ConfigModelConverter.DIFW_STEP_CATEGORY_INPUT]},
        {"difw_step_category_name": ConfigModelConverter.DIFW_STEP_CATEGORY_TRANSFORMATION,
         "multistep_category": DIFW_STEP_CATEGORY_MULTISTEP_FLAG[
             ConfigModelConverter.DIFW_STEP_CATEGORY_TRANSFORMATION]},
        {"difw_step_category_name": ConfigModelConverter.DIFW_STEP_CATEGORY_OUTPUT,
         "multistep_category": DIFW_STEP_CATEGORY_MULTISTEP_FLAG[ConfigModelConverter.DIFW_STEP_CATEGORY_OUTPUT]},
        {"difw_step_category_name": ConfigModelConverter.DIFW_STEP_CATEGORY_PROCESS,
         "multistep_category": DIFW_STEP_CATEGORY_MULTISTEP_FLAG[ConfigModelConverter.DIFW_STEP_CATEGORY_PROCESS]}
    ]

    DIFW_STEP_CATEGORY_AND_TYPE_IDENTIFIER_MAPPING = {
        ConfigModelConverter.DIFW_STEP_CATEGORY_INPUT: "format",
        ConfigModelConverter.DIFW_STEP_CATEGORY_TRANSFORMATION: "type",
        ConfigModelConverter.DIFW_STEP_CATEGORY_OUTPUT: "writer",
        ConfigModelConverter.DIFW_STEP_CATEGORY_PROCESS: "type",
    }

    def __init__(self, logger, secrets_management: SecretsManagement,
                 definition_metadata_management: DefinitionsMetadataManagement, user_isid, project_id,
                 all_environments=None):
        super().__init__(logger, secrets_management)
        self.platform = None
        self.definition_metadata_management = definition_metadata_management
        self.created_secrets = []
        # napping of step name from YAML + difw step category configuration to entity pipeline step
        self.yaml_step_name_to_pipeline_step = {}
        self.pipeline_name = None
        if not all_environments:
            all_environments = ['dev', 'tst', 'test', 'sit', 'uat', 'prd', 'prod', 'sbx']
        self.config_utils = ConfigurationUtils(logger=self.logger, isid=user_isid, environment="dev",
                                               all_environments=all_environments)
        self.environment = ""
        self.project_id = project_id

    def convert_yaml_config_to_model(self, yaml_configuration: dict, framework_version: str,
                                     pipeline_version: str = "1.0.0", environment: str = "dev") -> \
            (EntityPipeline, dict, [str]):
        """
        Main method for conversion of yaml configuration to model
        :param yaml_configuration: dict of yaml configuration
        :param framework_version: version of framework
        :param pipeline_version: pipeline version
        :param environment: environment

        :return: tuple of EntityPipeline, dict of unprocessed configuration keys and name of created secrets
        """
        self.logger.info(f"Going to convert YAML configuration to model for "
                         f"framework version = {framework_version} and environment = {environment}")
        self.pipeline_name = yaml_configuration.get("dataset_name")
        self.environment = environment
        self.config_utils.environment = environment

        del yaml_configuration['dataset_name']
        self.platform = yaml_configuration.get("platform", "glue")
        final_model = EntityPipeline(self.pipeline_name, pipeline_version=pipeline_version,
                                     framework_version=framework_version)

        # first resolve all env specific values
        self._resolve_env_specific_values(yaml_config_value=yaml_configuration, environment=environment)

        # general attribute first
        self._resolve_general_attributes(yaml_configuration, final_model)

        # resolve dbx
        self._resolve_dbx_settings(yaml_configuration, final_model)

        # resolve airflow_event_handlers - airflow notifications
        self._resolve_airflow_event_handlers(yaml_configuration, final_model)

        # resolve catalogs
        self._resolve_catalogs(yaml_configuration, final_model)

        # then steps
        self._resolve_entity_pipeline_steps(yaml_configuration, framework_version,
                                            yaml_configuration.get("platform", "glue"), final_model)
        # and finally tables
        self._resolve_tables(yaml_configuration, final_model, yaml_configuration.get("platform", "glue"))

        # at the end remove the keys from yaml_configuration which are empty
        unprocessed_yaml_configuration = self._remove_empty_values_from_yaml(yaml_configuration)
        return final_model, unprocessed_yaml_configuration, self.created_secrets

    def _remove_empty_values_from_yaml(self, input_dict):
        """
        Remove empty values from input dict which represent yaml configuration
        Sample input:
        key1:
            key11: ""
            key12: {}
            key13: "someValue"
        key2:
            key21:
                key211: ""

        Sample output
        key1:
            key13: "someValue"

        :return: cleared dict
        """
        if isinstance(input_dict, dict):
            return dict((yaml_item_config_key, self._remove_empty_values_from_yaml(yaml_config_item_value)) for
                        yaml_item_config_key, yaml_config_item_value in input_dict.items() if
                        yaml_config_item_value and self._remove_empty_values_from_yaml(yaml_config_item_value))
        if isinstance(input_dict, list):
            return [self._remove_empty_values_from_yaml(yaml_config_item_value) for yaml_config_item_value in input_dict
                    if yaml_config_item_value and self._remove_empty_values_from_yaml(yaml_config_item_value)]
        return input_dict

    def _resolve_env_specific_values(
            self, yaml_config_value, parent_config_item=None, parent_config_key: str = None,
            environment: str = None):
        """
        Resolve environment specific value. For example if we are working with env1 and in yaml there is value such:
        ---
        some_key:
            _env_1_: value of env 1
            _env_2: value of env 2
        ---
        Then it will be simple resolve as
        ---
        some_key: value of env 1
        ---

        :param yaml_config_value: dict of yaml configuration
        :param parent_config_item: parent yaml config item needed in recursion
        :param parent_config_key: parent yaml config key needed in recursion
        :param environment: environment
        """
        if isinstance(yaml_config_value, dict):
            if f"_{environment}_" in yaml_config_value.keys():
                yaml_config_value = yaml_config_value[f"_{environment}_"]
                parent_config_item[parent_config_key] = yaml_config_value
                self._resolve_env_specific_values(yaml_config_value, parent_config_item=parent_config_item,
                                                  parent_config_key=parent_config_key,
                                                  environment=environment)
            else:
                for key, value in yaml_config_value.items():
                    self._resolve_env_specific_values(value, parent_config_item=yaml_config_value,
                                                      parent_config_key=key,
                                                      environment=environment)
        if isinstance(yaml_config_value, list):
            for list_item in yaml_config_value:
                self._resolve_env_specific_values(list_item, parent_config_item=yaml_config_value,
                                                  parent_config_key=parent_config_key,
                                                  environment=environment)

    def _resolve_general_attributes(self, yaml_config_jobs: dict, final_model: EntityPipeline):
        """
        Resolve general attributes of pipeline

        :param yaml_config_jobs:
        :param final_model:
        """
        self.logger.info("Going to resolve general attributes")
        # global config
        is_glue_platform = yaml_config_jobs.get("platform", "glue") == "glue"
        map_dict_to_destination(
            [
                ("platform", "platform", "glue"),
                ("resource_prefix", "resource_prefix", "data_ingest_{{dataset_name}}"),
                ("schedule", "schedule", None),
                ("initial_load/start_date", "initial_load_start_date", None),
                ("initial_load/lower_bound", "lower_bound_start_date", None),
                ("defer", "enable_deffer_operators", False),
                ("aws_account/custom_tags", "tags", {}),
                # glue advance properties
                ("spark_sql_settings", "advanced_options/entity_glue_options/spark_sql_configuration", None,
                 is_glue_platform),
                ("system_properties", "advanced_options/entity_glue_options/java_system_properties", None,
                 is_glue_platform),
                ("spark_config", "advanced_options/entity_glue_options/spark_configuration", None, is_glue_platform),
                ("enable_auto_scaling", "advanced_options/entity_glue_options/autoscaling", None, is_glue_platform),
                ("worker_type", "advanced_options/entity_glue_options/worker_type", None, is_glue_platform),
                ("num_workers", "advanced_options/entity_glue_options/number_of_workers", None, is_glue_platform),
                ("dag_instance_parameters",
                 "advanced_options/entity_airflow_options/dag_instance_parameters", None,
                 'dag_instance_parameters' in yaml_config_jobs),
                ("dag_concurrency", "advanced_options/entity_airflow_options/dag_concurrency", None,
                 'dag_concurrency' in yaml_config_jobs),
                ("airflow_pool", "advanced_options/entity_airflow_options/airflow_pool_name", None,
                 'airflow_pool' in yaml_config_jobs),
                ("airflow_pool_slots", "advanced_options/entity_airflow_options/airflow_pool_slots", None,
                 'airflow_pool_slots' in yaml_config_jobs)
            ],
            yaml_config_jobs,
            final_model,
            True
        )

    # pylint: disable=too-many-locals
    def _resolve_tables(self, yaml_configuration: dict, final_model: EntityPipeline, platform: str = "glue"):
        """
        Resolve tables

        :param yaml_configuration:
        :param final_model:
        :param platform:
        """
        self.logger.info("Going to resolve tables,...")
        is_glue_platform = platform == "glue"
        for yaml_table_config in yaml_configuration["tables"]:
            entity_pipeline_table = EntityPipelineTable(yaml_table_config["name"], parent_pipeline=final_model,
                                                        framework_version=final_model.framework_version)
            del yaml_table_config["name"]
            map_dict_to_destination(
                [
                    ("original_table_name", "source_table_name", None),
                    ("target_table", "target_table_name", None),
                    ("ingest_strategy", "load_type", "full"),
                    ("incremental_condition/condition", "incremental_condition", None),
                    ("primary_key/columns", "primary_keys", []),
                    ("incremental_strategy_no_update", "incremental_strategy_no_update", True),
                    ("static_partitions", "static_partitions", {}),
                    ("dynamic_partitions", "dynamic_partitions", []),
                    ("airflow_pool", "airflow_pool_name", None),
                    ("airflow_pool_slots", "airflow_pool_slots", None),
                    ("refresh_rate", "refresh_rate", None),
                    ("dependency", "depends_on", []),
                    # glue advance properties - for tables only glue are allowed
                    ("spark_sql_settings", "advanced_options/entity_glue_options/spark_sql_configuration", None,
                     is_glue_platform),
                    ("system_properties", "advanced_options/entity_glue_options/java_system_properties", None,
                     is_glue_platform),
                    ("spark_config", "advanced_options/entity_glue_options/spark_configuration", None,
                     is_glue_platform),
                    ("enable_auto_scaling", "advanced_options/entity_glue_options/autoscaling", None, is_glue_platform),
                    ("worker_type", "advanced_options/entity_glue_options/worker_type", None, is_glue_platform),
                    ("num_workers", "advanced_options/entity_glue_options/number_of_workers", None, is_glue_platform),
                ],
                yaml_table_config,
                entity_pipeline_table,
                True
            )
            # overwritten on step is allowed
            for step_name, difw_step_categories in yaml_table_config.get("steps", {}).items():
                for difw_step_category_name, yaml_table_step_configs in difw_step_categories.items():
                    if self.DIFW_STEP_CATEGORY_MULTISTEP_FLAG[difw_step_category_name]:
                        yaml_step_configs = []
                        for difw_multi_category_step_name, yaml_table_step_config in yaml_table_step_configs.items():
                            yaml_table_step_config["component_name"] = self._resolve_component_name(
                                difw_step_category_name, difw_multi_category_step_name=difw_multi_category_step_name)
                            yaml_step_configs.append(yaml_table_step_config)
                    else:
                        yaml_table_step_configs["component_name"] = self._resolve_component_name(
                            difw_step_category_name, step_name=step_name)
                        yaml_step_configs = [yaml_table_step_configs]

                    for yaml_step_config_item in yaml_step_configs:
                        entity_pipeline_step = \
                            self.yaml_step_name_to_pipeline_step.get(yaml_step_config_item["component_name"])
                        if not entity_pipeline_step:
                            self.logger.warning(f"The table with name {entity_pipeline_table.table_name} "
                                                f"does not contain component with name "
                                                f"{yaml_step_config_item['component_name']} ")
                        else:
                            table_attributes = copy.deepcopy(entity_pipeline_step.definition['attributes'])
                            self._resolve_step_attributes_values(
                                table_attributes,
                                yaml_step_config_item, remove_not_included_components=True)
                            entity_pipeline_table.steps.append(
                                EntityPipelineTableStep(component_name=entity_pipeline_step.component_name,
                                                        overwrite_model_attributes=table_attributes,
                                                        origin_table_name=entity_pipeline_table.table_name,
                                                        origin_table_version=entity_pipeline_table.table_version))
                        # those attribute is already used, we can remove it
                        del yaml_step_config_item["component_name"]

            final_model.tables.append(entity_pipeline_table)

    def _get_step_info_from_yaml_config_jobs(self, yaml_config_jobs):
        """
        Get information about step from yaml configuration
        :param yaml_config_jobs: configuration of yaml jobs

        :return:
            - list of steps. Each step is dict of the following info:
                - yaml_step_config_name
                - component_name
                - difw_step_category
                - difw_step_type
                - yaml_step_config
        """
        # pylint:disable=too-many-nested-blocks

        # loop all steps and create list of all steps
        # each item in list is dict with component_name created from job name and step name and yaml_step_config
        # what is full config of step
        self.logger.info("Going to parse jobs/steps,...")
        steps_to_parse = []
        # config contains the list of jobs followed by steps. Each step has the own configuration.
        # Configuration is dict of difw step category and configuration of particular difw step type
        for yaml_config_job in yaml_config_jobs["jobs"]:
            for yaml_step_config in yaml_config_job["steps"]:
                step_configuration = yaml_step_config["configuration"]
                for difw_step_category in self.DIFW_STEP_CATEGORY_ORDER:
                    difw_step_category_name = difw_step_category["difw_step_category_name"]
                    if difw_step_category_name in step_configuration:
                        steps_to_assign = []
                        difw_step_type_identifier = self.DIFW_STEP_CATEGORY_AND_TYPE_IDENTIFIER_MAPPING[
                            difw_step_category_name]
                        if difw_step_category["multistep_category"]:
                            # this section solve use case in case of transformers and processors.
                            # both are multistep categories, so it means, there can be more components
                            # of the same type, but with different name
                            ordered_types = resolve_dependencies(step_configuration[difw_step_category_name])
                            for difw_multi_category_step_name in ordered_types:
                                step_config = step_configuration[difw_step_category_name].get(
                                    difw_multi_category_step_name
                                )
                                difw_step_type = step_config[difw_step_type_identifier]
                                step_config["component_name"] = self._resolve_component_name(
                                    difw_category_type=difw_step_category_name,
                                    difw_multi_category_step_name=difw_multi_category_step_name
                                )
                                step_config["difw_step_type"] = difw_step_type
                                steps_to_assign.append(step_config)
                        else:
                            step_config = step_configuration[difw_step_category_name]
                            difw_step_type = step_config[difw_step_type_identifier]
                            step_config["component_name"] = self._resolve_component_name(
                                difw_category_type=difw_step_category_name, step_name=yaml_step_config['name']
                            )
                            step_config["difw_step_type"] = difw_step_type
                            steps_to_assign.append(step_config)
                        for step_to_assign in steps_to_assign:
                            steps_to_parse.append({
                                "yaml_step_config_name": f"{yaml_step_config['name']}_{difw_step_category_name}",
                                "component_name": step_to_assign["component_name"],
                                "difw_step_category": difw_step_category_name,
                                "difw_step_type": step_to_assign["difw_step_type"],
                                "yaml_step_config": step_to_assign
                            })
                            # those 2 attributes are already used, we can remove it
                            del step_to_assign["component_name"]
                            del step_to_assign["difw_step_type"]

                # clear processed keys
                del yaml_step_config['name']

        return steps_to_parse

    @staticmethod
    def _resolve_component_name(difw_category_type, step_name=None, difw_multi_category_step_name=None):
        """
        Create component name from yaml step information

        :return: component name
        """
        if difw_multi_category_step_name:
            return f"{difw_multi_category_step_name}_{difw_category_type}"
        return f"{step_name}_{difw_category_type}"

    def _resolve_entity_pipeline_steps(self, yaml_config_jobs, framework_version, platform,
                                       final_model: EntityPipeline) -> [EntityPipelineSteps]:
        """
        Parse job config and create entity pipeline steps
        """
        steps_to_parse = self._get_step_info_from_yaml_config_jobs(yaml_config_jobs)

        # check unique names of components
        values = [item["component_name"] for item in steps_to_parse]
        if len(values) != len(set(values)):
            raise ConfigurationModelConvertorError(
                'There are duplicated component names in the configuration. Please check the configuration '
                'and make sure that all step components have unique names.'
            )

        # loop all steps and find out the child component and parse model
        entity_pipeline_steps = []
        step_index = 0
        entity_pipeline_step = None
        for step_info in steps_to_parse:
            definition = self._parse_model(
                step_info["yaml_step_config"],
                step_info["difw_step_type"],
                step_info["difw_step_category"],
                self.definition_metadata_management.get_component_types(platform, framework_version, None)
            )
            step_index += 1
            if definition:
                entity_pipeline_step = EntityPipelineSteps(
                    component_id=None,
                    component_name=step_info["component_name"],
                    component_coordinates=None,
                    child_component_name=None if step_index >= len(steps_to_parse) else steps_to_parse[step_index][
                        "component_name"],
                    description="",
                    definition=definition,
                    framework_version=framework_version
                )
                # fill mapping. It will be needed in table section to properly identify the component
                # which is going to be used to identify the exact name of component based on yaml step name
                # and difw step category
                self.yaml_step_name_to_pipeline_step[step_info["component_name"]] = entity_pipeline_step
                entity_pipeline_steps.append(entity_pipeline_step)
            else:
                # if there is entity_pipeline_step from previous iteration then remove child
                if entity_pipeline_step:
                    entity_pipeline_step.set_child_component_name(None)
        final_model.steps.extend(entity_pipeline_steps)

    def _parse_model(self, step_configuration: dict, difw_step_type: str, difw_step_category: str,
                     component_types: [EntityComponentType]) -> dict:
        """
        Main method for parsing model

        :param step_configuration: step configuration
        :param difw_step_type: difw step type
        :param difw_step_category: difw step category
        :param component_types: list of EntityComponentType - all metadata from DB

        :return: dict represents model
        """
        self.logger.info(f"Going to parse model for difw_step_type={difw_step_type}")
        # first get component type and category of particular step
        resolved_component_type = None
        for component_type in component_types:
            if component_type.definition["difwStepType"] == difw_step_type \
                    and component_type.definition["difwStepCategory"] == difw_step_category \
                    and component_type.component_type_name not in ['local_file']:
                resolved_component_type = copy.deepcopy(component_type)
                break
        if resolved_component_type is None:
            self.logger.warning(f"Metadata not found for difw_step_type={difw_step_type} "
                                f"and difw_step_category={difw_step_category}")
            return {}

        # now parse all attributes and take value from Yaml configuration
        # in case of dynamicPattern the attributes can miss
        self._resolve_step_attributes_values(resolved_component_type.definition["attributes"], step_configuration)
        # in this phase we know that we can remove category identifiers and depends_on keywords
        self._delete_process_keys_from_step_configuration(step_configuration,
                                                          resolved_component_type.definition["difwStepCategory"])
        return resolved_component_type.definition

    def _delete_process_keys_from_step_configuration(self, step_configuration, difw_step_category):
        """
        Delete identifiers and depends on sections from step config
        """
        del step_configuration[self.DIFW_STEP_CATEGORY_AND_TYPE_IDENTIFIER_MAPPING[difw_step_category]]
        if "depends_on" in step_configuration:
            del step_configuration["depends_on"]

    def _resolve_step_attributes_values(self, component_type_attributes: list, step_configuration,
                                        remove_not_included_components=False):
        """
        Resolve values of component types

        :param component_type_attributes - definition of attributes from metadata
        :param step_configuration - fragment of yaml step configuration
        :param remove_not_included_components - flag indicates if remove component_type_attribute which
        is not part of step configuration then
        """
        components_attrs_to_remove = []
        for component_type_attribute in component_type_attributes:
            attr_name = component_type_attribute.get("attributeName")
            # there is different approach in case of dynamicPattern
            if "dynamicPattern" in component_type_attribute["type"]:
                # now loop via pattern and enhance component_type_attribute with new attributes from dynamicPattern
                component_type_attribute["type"]["attributes"] = []
                for dynamic_step_config_key, dynamic_step_config_value in step_configuration.items():
                    dynamic_attributes = copy.deepcopy(component_type_attribute["type"]["dynamicPattern"]["attributes"])
                    # take it and resolve attributes again
                    self._resolve_step_attributes_values(dynamic_attributes, dynamic_step_config_value,
                                                         remove_not_included_components)
                    component_type_attribute["type"]["attributes"].append(
                        {
                            "attributeName": dynamic_step_config_key,
                            "type": {
                                "objectType": self.MODEL_TYPE_OBJECT,
                                "attributes": dynamic_attributes
                            }
                        }
                    )
            # here process with regular assignment of values
            elif attr_name in step_configuration:
                yaml_config_value = step_configuration[attr_name]
                if isinstance(yaml_config_value, SecretValue):
                    self._process_yaml_secret(component_type_attribute, yaml_config_value, attr_name)
                    # deleting this attribute we are saying that it is already process
                    del step_configuration[attr_name]
                elif component_type_attribute["type"]["objectType"] == self.MODEL_TYPE_OBJECT:
                    self._resolve_step_attributes_values(component_type_attribute["type"]["attributes"],
                                                         yaml_config_value, remove_not_included_components)
                elif component_type_attribute["type"]["objectType"] == self.MODEL_TYPE_LIST and \
                        component_type_attribute["type"]["elementsType"]["objectType"] == self.MODEL_TYPE_OBJECT:
                    # It is list of objects, so value should be list of specific attributes
                    # the yaml config value is list in this case
                    component_type_attribute["value"] = []
                    for yaml_config_list_item_value in yaml_config_value:
                        # will take the structure of element and assign it as separate value into final json
                        # per each item in yaml configuration file
                        attributes_of_list_element = \
                            copy.deepcopy(component_type_attribute["type"]["elementsType"]["attributes"])
                        component_type_attribute["value"].append({"attributes": attributes_of_list_element})
                        self._resolve_step_attributes_values(attributes_of_list_element,
                                                             yaml_config_list_item_value,
                                                             remove_not_included_components)
                else:
                    component_type_attribute["value"] = yaml_config_value
                    # deleting this attribute we are saying that it is already process
                    del step_configuration[attr_name]
            else:
                # now there is situation that component type is not in attribute and if it is requested we can remove
                # it from list of attributes
                if remove_not_included_components:
                    components_attrs_to_remove.append(component_type_attribute)
        # if there are any components_attr_to_remove then remove it from main list
        for components_attr_to_remove in components_attrs_to_remove:
            component_type_attributes.remove(components_attr_to_remove)

    def _process_yaml_secret(self, component_type_attribute, yaml_config_value, attr_name):
        """
        Process secrets from yaml. I method we are checking if secret exists or not.
        If not the secret is created and assign to created secret lis

        :param component_type_attribute: dict of metadata of particular component type from metaDB
        :param yaml_config_value: value of configuration from yaml / dataset definition configuration
        :param attr_name: Name of processing attribute
        """
        if component_type_attribute["type"]["objectType"] == self.MODEL_TYPE_SECRET:
            # resolve SM name in case there are some placeholders
            yaml_config_value.secret_name = ConfigurationUtils.render(
                yaml_config_value.secret_name,
                {"env": self.environment, "dataset_name": self.pipeline_name})
            stored_secrets = self.secrets_management.get_secret_by_sm_name(yaml_config_value.secret_name)
            # if secret does not exist then create new one
            if not stored_secrets:
                stored_secrets.append(EntitySecret(
                    secret_name=f"{self.project_id}_{yaml_config_value.secret_name.replace('/', '_')}",
                    secret_manager_name=yaml_config_value.secret_name,
                    description="Generated secret by configuration converter"
                ))
                # if there are any stored_secrets then it is enough to take the first one
                self.secrets_management.create_secret(stored_secrets[0], check_permission=True)
                # if within the process secret was created then append it to list of newly stored secrets
                self.created_secrets.append(stored_secrets[0].secret_name)
            # assign secret to final model
            component_type_attribute["value"] = {
                "secretName": stored_secrets[0].secret_name,
                "secretManagerName": stored_secrets[0].secret_manager_name,
                "secretKey": yaml_config_value.secret_key
            }
        else:
            # in case there is type mismatch between metadata and secrets type from yaml then
            # assign None as value
            self.logger.warning(f"There is type mismatch for attr with name {attr_name}")
            component_type_attribute["value"] = None

    def _resolve_catalogs(self, yaml_configuration: dict, final_model: EntityPipeline):
        """
        Resolve catalog attributes of pipeline

        :param yaml_configuration:
        :param final_model:
        """
        self.logger.info("Going to resolve general attributes")
        # first glue databases
        if self.platform == "glue" and yaml_configuration.get("glue_databases"):
            dict_of_glue_databases = {}
            for name_of_glue_database, yaml_glue_database in yaml_configuration.get("glue_databases").items():
                entity_glue_database = EntityGlueDatabase()
                map_dict_to_destination(
                    [
                        ("database_name", "database_name", None),
                        ("s3_layer_path", "s3_layer_path", None),
                    ],
                    yaml_glue_database,
                    entity_glue_database,
                    True
                )
                dict_of_glue_databases[name_of_glue_database] = entity_glue_database
            # add glue databases to the property of the catalog entity
            final_model.catalogs.set_dict_glue_databases(dict_of_glue_databases)
        # unity catalogs
        if self.platform == "databricks" and yaml_configuration.get("unity_catalog"):
            list_of_unity_catalogs = []
            # unity catalog is list
            for yaml_unity_catalog in yaml_configuration.get("unity_catalog"):
                unity_catalog = EntityUnityCatalog(unity_schemas={})
                yaml_unity_catalog.get("unity_schemas")
                map_dict_to_destination(
                    [
                        ("name", "name", None),
                        ("permissions", "permissions", None),
                    ],
                    yaml_unity_catalog,
                    unity_catalog,
                    True
                )
                # as unity schemas are nested dictionary
                for name_of_schema, yaml_unity_schema in yaml_unity_catalog.get("unity_schemas").items():
                    entity_unity_schema = EntityUnitySchema()
                    map_dict_to_destination(
                        [
                            ("skip_creation", "skip_creation", None),
                            ("schema_name", "schema_name", None),
                            ("s3_layer_path", "s3_layer_path", None),
                            ("permissions", "permissions", None),
                        ],
                        yaml_unity_schema,
                        entity_unity_schema,
                        True
                    )
                    # add the unity schema to current unity_catalog
                    unity_catalog.unity_schemas[name_of_schema] = entity_unity_schema
                # append unity catalog to the list
                list_of_unity_catalogs.append(unity_catalog)
            # add list unity catalog under catalog property
            final_model.catalogs.set_list_unity_catalog(list_of_unity_catalogs)

    def _resolve_airflow_event_handlers(self, yaml_configuration: dict, final_model: EntityPipeline):
        """
        Resolve airflow event handlers - airflow notifications

        @param yaml_configuration:
        @param final_model:
        """
        self.logger.info("Going to resolve airflow event handlers")
        if yaml_configuration.get("airflow_event_handlers"):
            airflow_notifications = EntityAirflowNotifications()
            for on_task_state, notification_definition in yaml_configuration.get("airflow_event_handlers", {}).items():
                airflow_notification = EntityAirflowNotification(enabled=True)
                map_dict_to_destination(
                    [
                        ("to", "email_recipients", None),
                        ("subject", "email_subject", None),
                        ("html_content", "email_content", None)
                    ],
                    notification_definition.get("email_message"),
                    airflow_notification,
                    True
                )
                if on_task_state == "on_task_success":
                    airflow_notifications.set_on_success(airflow_notification)
                if on_task_state == "on_task_failure":
                    airflow_notifications.set_on_failure(airflow_notification)
                # mapping to drop the all_tables key from dictionary
                map_dict_to_destination(
                    [
                        ("all_tables", "all_tables", None)
                    ],
                    notification_definition,
                    {},
                    True
                )
            final_model.notification.set_entity_airflow_notifications(airflow_notifications)

    def _resolve_dbx_settings(self, yaml_configuration: dict, final_model: EntityPipeline):
        """
        Resolve dbx account settings of the pipeline and dbx access control list

        :param yaml_configuration:
        :param final_model:
        """
        self.logger.info("Going to resolve general attributes")
        # dbx advance properties
        is_dbx_account_present = yaml_configuration.get("databricks_account")
        is_acl_present = is_dbx_account_present and yaml_configuration.get("access_control_list")
        map_dict_to_destination([
            ("databricks_account/cluster_options", "advanced_options/entity_dbx_options/job_cluster_options",
             None, is_dbx_account_present),
            ("databricks_account/validate_all_purpose_cluster",
             "advanced_options/entity_dbx_options/all_purpose_cluster_validate",
             None, is_dbx_account_present),
            ("databricks_account/existing_cluster_name",
             "advanced_options/entity_dbx_options/all_purpose_cluster_name",
             None, is_dbx_account_present),
            ("databricks_account/existing_cluster_id",
             "advanced_options/entity_dbx_options/all_purpose_cluster_id",
             None, is_dbx_account_present)],
            yaml_configuration,
            final_model,
            True
        )
        # dbx acls, as this is configuration to model convertor we just need to parse the acl
        # under correct properties of the dbx options
        if is_acl_present:
            acls_user = []
            acls_group = []
            # cycle through them and check the key if its user_name or group_name, so its assigned under correct acl
            for acl in is_acl_present:
                if acl.get("user_name"):
                    acl_object = {}
                    map_dict_to_destination([
                        ("user_name", "UserName", None),
                        ("permission_level", "Permission", None)
                    ],
                        acl,
                        acl_object,
                        True
                    )
                    acls_user.append(acl_object)
                if acl.get("group_name"):
                    acl_object = {}
                    map_dict_to_destination([
                        ("group_name", "UserGroup", None),
                        ("permission_level", "Permission", None)
                    ],
                        acl,
                        acl_object,
                        True
                    )
                    acls_group.append(acl_object)
            # set the acs under correct properties of the dbx options
            final_model.advanced_options.entity_dbx_options.set_dbx_acl_user(acls_user)
            final_model.advanced_options.entity_dbx_options.set_dbx_acl_group(acls_group)
