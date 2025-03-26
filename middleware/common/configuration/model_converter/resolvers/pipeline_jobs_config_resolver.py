import copy
import re

from common.secrets.secrets import SecretValue
from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_base_pipeline import EntityBasePipeline
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline
from middleware.common.entity_management.entities.entity_pipeline_steps import EntityPipelineSteps


class PipelineJobsConfigResolver(ConfigPartResolver):
    """
    Resolve jobs related configuration
    """
    AWS_ACCESS_KEY_ID_DEFINITION = {
        "attributeName": "aws_access_key_id",
        "type": {
            "objectType": "secret"
        }
    }

    AWS_SECRET_ACCESS_KEY_DEFINITION = {
        "attributeName": "aws_secret_access_key",
        "type": {
            "objectType": "secret"
        }
    }

    S3_ASSUME_ROLE_ATTR_DEFINITION = {
        "attributeName": "s3_assume_role",
        "type": {
            "objectType": "string"
        }
    }

    SPARK_ASSUME_ROLE_ATTR_DEFINITION = {
        "attributeName": "spark_assume_role",
        "type": {
            "objectType": "string"
        }
    }

    def resolve_model_to_config(self, entity_pipeline: EntityPipeline, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """
        # extract steps into dict and check uniqueness of names
        steps_dict = self._convert_steps_to_dict_check_duplicities(entity_pipeline.steps)

        # order steps
        ordered_steps = self._order_steps(steps_dict=steps_dict)

        # group steps into jobs
        ordered_jobs = self._group_steps_into_jobs(ordered_steps, entity_pipeline.platform)

        # resolve attributes and custom processors of job
        job_configuration_part, component_step_name_mapping = self._create_jobs_configuration_section(
            ordered_jobs, entity_pipeline)

        # store component step name mapping  and condition type into context to use it for table resolver
        self.converter.add_context_property("component_step_name_mapping", component_step_name_mapping)
        self.converter.add_context_property("source_condition_type", self._resolve_condition_type(ordered_steps))

        # will be place into global configuration
        return "jobs[:]", job_configuration_part

    @staticmethod
    def _resolve_condition_type(ordered_steps: [EntityPipelineSteps]):
        """
        Resolve condition type for incremental condition. It will take the first step which has defined
        property conditionType

        @param ordered_steps: steps

        @return: condition type, default is spark_sql
        """
        for step in ordered_steps:
            if "conditionType" in step.definition.get("componentProperties", {}):
                return step.definition["componentProperties"]["conditionType"]
        return "spark_sql"

    def _convert_steps_to_dict_check_duplicities(self, steps: [EntityPipelineSteps]) -> dict[str, EntityPipelineSteps]:
        """
        Extract and sort steps from pipeline model based on child component name

        @param steps: list of instance EntityPipelineSteps
        @return:
        """
        # need to or
        steps_dict = {}
        # divide steps into hash map, based on component name key
        for step in steps:
            step_name = step.component_name
            if step_name in steps_dict:
                raise Exception(
                    f"There is duplicity within step name. Name of step {step_name} exists more then once ")
            steps_dict[step_name] = step
        self.converter.logger.info(f"Steps names: {list(steps_dict.keys())}")
        return steps_dict

    def _order_steps(self, steps_dict: dict[str, EntityPipelineSteps]) -> [EntityPipelineSteps]:
        """
        Find step name which is defined as first one within the model.

        @param  steps_dict: dict of steps
        @return: list of instance of EntityPipelineSteps
        """
        # key = child name, value = parent name
        child_to_parent_hierarchy: dict[str, str] = {}
        final_step_list: [EntityPipelineSteps] = []
        last_child_name = "__LAST_STEP__"
        for step_name, step_item in steps_dict.items():
            child_name = step_item.child_component_name
            if not child_name:
                child_name = last_child_name
            child_to_parent_hierarchy[child_name] = step_name
        # loop from last to first and add to the end
        while child_to_parent_hierarchy:
            last_child_name = child_to_parent_hierarchy.pop(last_child_name)
            final_step_list.append(steps_dict[last_child_name])
        # final step list is now ordered from last to first. We need to reverse it
        final_step_list.reverse()
        self.converter.logger.info(
            f"Ordered steps = {[step_item.component_name for step_item in final_step_list]}")
        return final_step_list

    def _group_steps_into_jobs(self, ordered_steps: [EntityPipelineSteps], platform: str):
        """
        Take steps and divide it into jobs. For example transformers in the same order can be together in one job,
        but the processor before source needs to be put in separate job...
        @param ordered_steps:
        @param platform:
        @return:
        """
        jobs = list()
        previous_job_type = None
        previous_step_category = None
        step_name = None
        job_number = -1
        step_number = 0
        # following dict is only logged in the end to have an option to check the mapping between the simplification
        # and the proper step/job names
        # if we start index on 1, the first job will be job_1
        for step in ordered_steps:
            job_category = step.definition.get("difwJobCategory", self.converter.DIFW_JOB_CATEGORY_STEPS)
            step_category = self._get_step_difw_category(step)
            # if there is no platform type defined and it is OUTPUT or TRANSFORMER then take actual/previous job type
            if not step.definition.get('platforms') and step_category in \
                    [self.converter.DIFW_STEP_CATEGORY_OUTPUT, self.converter.DIFW_STEP_CATEGORY_TRANSFORMATION]:
                job_type = previous_job_type
            else:
                job_type = self._get_job_type_of_step(step, platform)

            if job_type is None and job_category == self.converter.DIFW_JOB_CATEGORY_STEPS:
                raise Exception(
                    f"Not able to recognize the correct job type for step {self._get_step_difw_type(step)}")
            # add new job if job type differ or the first steps are processors only. Then in this case, the processors
            # are separate job. But only in case of first ranks in queue. Therefore, if category is not processor,
            # the first job was processors (can be checked that first step is processor, but there is
            # exactly one job then create new job
            # also if job category is sniffer or operator then always create new job
            if previous_job_type != job_type or job_category in [self.converter.DIFW_JOB_CATEGORY_SNIFFER,
                                                                 self.converter.DIFW_JOB_CATEGORY_OPERATOR]:
                previous_step_category = None
                previous_job_type = job_type
                job_number += 1
                if job_category != self.converter.DIFW_JOB_CATEGORY_STEPS:
                    jobs.append({
                        "job_name": f"job_{job_number + 1}",
                        job_category: {}
                    })
                else:
                    jobs.append({
                        "job_name": f"job_{job_number + 1}",
                        "type": job_type,
                        "steps": {}
                    })

            if step_category == self.converter.DIFW_STEP_CATEGORY_INPUT or \
                    step.definition["componentCategory"] == self.converter.MODEL_STEP_CATEGORY_IN_CONNECTOR or (
                    step_category == self.converter.DIFW_STEP_CATEGORY_PROCESS and
                    previous_step_category != self.converter.DIFW_STEP_CATEGORY_PROCESS and
                    previous_step_category != self.converter.DIFW_STEP_CATEGORY_OUTPUT):
                step_number += 1
                step_name = f"{jobs[job_number]['job_name']}_step_{step_number}"
                jobs[job_number]["steps"][step_name] = []
            if job_category == self.converter.DIFW_JOB_CATEGORY_STEPS:
                if step_name is None:
                    raise Exception("The order of steps is not correct. Not able to generate jobs sequence")
                jobs[job_number]["steps"][step_name].append(step)
                previous_step_category = step_category
            else:
                jobs[job_number][job_category] = step
        return jobs

    @staticmethod
    def _get_step_difw_category(step: EntityPipelineSteps):
        """
        Get DIFW category of step

        @param step:
        @return:
        """
        if step.definition:
            return step.definition.get("difwStepCategory")
        raise Exception(f"Step {step.component_name}  need to have defined model")

    @staticmethod
    def _get_step_difw_type(step: EntityPipelineSteps):
        """
        Get difw type of step

        @param step:
        @return:
        """
        if step.definition:
            return step.definition["difwStepType"]
        raise Exception(f"Step {step.component_name} need to have defined model")

    def _get_job_type_of_step(self, step: EntityPipelineSteps, platform):
        """
        Get supported job type from step model
        @param step:
        @param platform:
        @return: supported job type
        """
        supported_job_types = step.definition.get('platforms', self.converter.JOB_TYPE_PLATFORM_DEFAULT_MAPPING)[
            platform]
        # there can be more of supported job types. For example some of the processors can run as spark but also
        # as a python therefore return always first, because it is type with biggest priority.
        if supported_job_types.get('supportedJobTypes', []):
            return supported_job_types['supportedJobTypes'][0]
        else:
            return None

    def _create_jobs_configuration_section(self, ordered_jobs: list,
                                           entity_base_pipeline: EntityBasePipeline) -> (list, dict):
        """
        Convert job section

        @param ordered_jobs:
        @param entity_base_pipeline:

        @return: job configuration result and mapping of componentName -> stepName
        """
        job_configuration_result = []
        component_step_name_mapping = {}
        for job in ordered_jobs:
            if self.converter.DIFW_JOB_CATEGORY_STEPS in job:
                self._create_jobs_steps_configuration_section(job, component_step_name_mapping,
                                                              job_configuration_result,
                                                              entity_base_pipeline)
            if self.converter.DIFW_JOB_CATEGORY_SNIFFER in job:
                self._create_jobs_airflow_configuration_section(job, component_step_name_mapping,
                                                                job_configuration_result,
                                                                self.converter.DIFW_JOB_CATEGORY_SNIFFER)
            if self.converter.DIFW_JOB_CATEGORY_OPERATOR in job:
                self._create_jobs_airflow_configuration_section(job, component_step_name_mapping,
                                                                job_configuration_result,
                                                                self.converter.DIFW_JOB_CATEGORY_OPERATOR)
        return job_configuration_result, component_step_name_mapping

    def _create_jobs_airflow_configuration_section(self, job: dict,
                                                   component_step_name_mapping: dict,
                                                   job_configuration_result: list,
                                                   job_category: str) -> None:
        """
        Create job configuration section for airflow component (sniffer/operator)

        @param job: resolved job configuration
        @param component_step_name_mapping:
        @param job_configuration_result: final result fo configuration
        @param job_category: It can be either sniffer or operator

        @return None
        """
        airflow_component_type = "operator" if job_category == self.converter.DIFW_JOB_CATEGORY_OPERATOR else "sensor"
        airflow_step_config = job[job_category]
        # because of remove operation in next step, copy the definition of step
        airflow_step_definition = copy.deepcopy(airflow_step_config.definition)
        class_attr_name = f"{airflow_component_type}_class"
        kwargs_attr_name = f"{airflow_component_type}_kwargs"
        airflow_configuration = {
            class_attr_name: "",
            kwargs_attr_name: {}
        }
        job_config = {
            "name": job["job_name"],
            job_category: airflow_configuration
        }
        job_configuration_result.append(job_config)
        airflow_task_parameters_attr = next((attr for attr in airflow_step_definition["attributes"] if
                                             attr["attributeName"] == "airflow_task_parameters"), None)
        if airflow_task_parameters_attr:
            airflow_configuration[kwargs_attr_name].update(
                self._convert_dynamic_attributes_to_simple_dict(airflow_task_parameters_attr["type"]["attributes"]))
            # delete for next processing
            airflow_step_definition["attributes"].remove(airflow_task_parameters_attr)
        if f"{airflow_component_type}Class" in airflow_step_config.definition.get("componentProperties", {}):
            airflow_configuration[class_attr_name] = \
                airflow_step_definition.get("componentProperties")[f"{airflow_component_type}Class"]
            airflow_configuration[kwargs_attr_name].update(
                self._convert_dynamic_attributes_to_simple_dict(airflow_step_definition["attributes"]))
        else:
            class_attr = next((attr for attr in airflow_step_definition["attributes"] if
                               attr["attributeName"] == class_attr_name), None)
            if not class_attr:
                raise Exception(f"Within the step {airflow_step_config.component_name} the {class_attr_name} "
                                f"is missing. Please fix metadata")

            class_kwargs = next((attr for attr in airflow_step_definition["attributes"] if
                                 attr["attributeName"] == kwargs_attr_name), None)
            if not class_kwargs:
                raise Exception(f"Within the step {airflow_step_config.component_name} the {kwargs_attr_name} "
                                f"are missing. Please fix metadata")

            airflow_configuration[class_attr_name] = class_attr.get("value")
            airflow_configuration[kwargs_attr_name].update(self._convert_dynamic_attributes_to_simple_dict(
                class_kwargs["type"]["attributes"]))
        # assign job category
        component_step_name_mapping[airflow_step_config.component_name] = (job["job_name"], job_category, None, None)

    def _create_jobs_steps_configuration_section(self, job: dict,
                                                 component_step_name_mapping: dict, job_configuration_result: list,
                                                 entity_base_pipeline: EntityBasePipeline) -> None:
        """
        Create jobs steps configuration

        @param job: resolved job configuration
        @param entity_base_pipeline:base entity pipeline
        @param job_configuration_result: final result fo configuration
        @param component_step_name_mapping:

        @return None
        """
        job_config = {
            "name": job["job_name"],
            "type": job["type"],
            "steps": []
        }
        if self.converter.DIFW_JOB_CATEGORY_STEPS in job:
            # adding additional check not to add empty event_notifications keyword
            if self.converter.get_context_property("event_notifications", default_value={}).get("event_notifications"):
                job_config.update(self.converter.get_context_property("event_notifications"))
        for step_name, step_config_list in job["steps"].items():
            difw_step_final_config = {"name": step_name}
            job_config["steps"].append(difw_step_final_config)
            # resolve options for aws account storage
            self._resolve_job_aws_account_external_storage(job_config, entity_base_pipeline)
            difw_step_final_config["configuration"] = \
                self._create_step_configuration_section(step_config_list, job_config, entity_base_pipeline)
            spark_configuration_section = self._create_job_spark_configuration_section(step_config_list)
            if spark_configuration_section:
                job_config["spark_config"] = spark_configuration_section
            for step_configuration in step_config_list:
                component_step_name_mapping[step_configuration.component_name] = (
                    job["job_name"],
                    self.converter.DIFW_JOB_CATEGORY_STEPS,
                    step_name,
                    self._get_step_difw_category(step_configuration)
                )
        job_configuration_result.append(job_config)

    def _resolve_step_aws_account_external_storage(self, job_step: EntityPipelineSteps,
                                                   entity_base_pipeline: EntityBasePipeline):
        """
        If step has support for account storage then add 4 attributes

        s3_assume_role
        aws_access_key_id
        aws_secret_access_key
        aws_session_token

        @param job_step: step to convert
        @param entity_base_pipeline: entity to convert
        """
        if job_step.definition.get("componentProperties", {}).get("supportExternalAwsStorage", False):
            # if there is assumed role within account storage then add it into step attributes
            if entity_base_pipeline.advanced_options.entity_aws_account_storage.assume_role:
                job_step.definition["attributes"].append(
                    self.copy_and_replace_template_attr(
                        self.S3_ASSUME_ROLE_ATTR_DEFINITION,
                        entity_base_pipeline.advanced_options.entity_aws_account_storage.assume_role)
                )
            # if there is access key of service user within account storage then add it into step attributes
            if entity_base_pipeline.advanced_options.entity_aws_account_storage.service_user_access_key_sn:
                job_step.definition["attributes"].append(
                    self.copy_and_replace_template_attr(
                        self.AWS_ACCESS_KEY_ID_DEFINITION,
                        {
                            "secretName": entity_base_pipeline.advanced_options.entity_aws_account_storage.
                            service_user_access_key_sn,
                            "secretKey": entity_base_pipeline.advanced_options.entity_aws_account_storage.
                            service_user_access_key_sk
                        })
                )
                job_step.definition["attributes"].append(
                    self.copy_and_replace_template_attr(
                        self.AWS_SECRET_ACCESS_KEY_DEFINITION,
                        {
                            "secretName": entity_base_pipeline.advanced_options.entity_aws_account_storage.
                            service_user_secret_key_sn,
                            "secretKey": entity_base_pipeline.advanced_options.entity_aws_account_storage.
                            service_user_secret_key_sk
                        })
                )

    def _resolve_job_aws_account_external_storage(self, job, entity_base_pipeline: EntityBasePipeline):
        """
        If job has support for account storage then add 4 attributes

        s3_assume_role
        aws_access_key_id
        aws_secret_access_key
        aws_session_token

        @param entity_base_pipeline: entity to convert
        """
        # can be spark or databricks_spark or spark_submit,...
        if "spark" in job.get("type"):
            if entity_base_pipeline.advanced_options.entity_aws_account_storage.assume_role:
                job["spark_assume_role"] = entity_base_pipeline.advanced_options.entity_aws_account_storage.assume_role
            if entity_base_pipeline.advanced_options.entity_aws_account_storage.service_user_access_key_sn:
                secret_manager_name_access_key = self._resolve_secret_manager_name(
                    {"secretName":
                         entity_base_pipeline.advanced_options.entity_aws_account_storage.service_user_access_key_sn}
                )
                secret_manager_name_secret_key = self._resolve_secret_manager_name(
                    {"secretName":
                         entity_base_pipeline.advanced_options.entity_aws_account_storage.service_user_secret_key_sn}
                )
                job["aws_access_key_id"] = SecretValue(
                    secret_manager_name_access_key,
                    entity_base_pipeline.advanced_options.entity_aws_account_storage.service_user_access_key_sk)
                job["aws_secret_access_key"] = SecretValue(
                    secret_manager_name_secret_key,
                    entity_base_pipeline.advanced_options.entity_aws_account_storage.service_user_secret_key_sk)

    def _create_step_configuration_section(self, job_steps: list, job_config: dict,
                                           entity_base_pipeline: EntityBasePipeline) -> dict:
        """
         Create dict representation of dataset configuration section -> jobs/<job>/steps/<step>/configuration
         from model.

        @param job_steps:
        @param job_config:
        @param entity_base_pipeline:

        @return: dict representation of dataset step configuration section
        """
        steps_configuration_section = {}
        # parent step is needed for resolving of depends on section
        parent_category_step = None
        previous_category = None
        for job_step in job_steps:
            # before the resolving the step values, enrich attrs by aws account storage if needed
            self._resolve_step_aws_account_external_storage(job_step, entity_base_pipeline)
            # check if there is needed any custom step
            component_type = job_step.definition['componentType']
            if hasattr(self, f"_custom_step_process_{component_type}"):
                # do deep copy of config list to not lost the reference to original resource
                job_step = job_step.create_copy()
                getattr(self, f"_custom_step_process_{component_type}")(
                    **{"job_step": job_step, "job_config": job_config})
            # difw_step_category => configuration/(input|transformer|output|processor)
            difw_step_category = self._get_step_difw_category(job_step)
            if previous_category != difw_step_category:
                # reset previous category step if differ from previous one
                parent_category_step = None
            step_config_fragment = self._create_step_config_fragment(job_step, parent_category_step)
            parent_category_step = job_step
            previous_category = difw_step_category
            if difw_step_category in steps_configuration_section:
                steps_configuration_section[difw_step_category].update(step_config_fragment)
            else:
                steps_configuration_section[difw_step_category] = step_config_fragment
        return steps_configuration_section

    def _create_step_config_fragment(self, step_config: EntityPipelineSteps, parent_category_step):
        """
        Create dict representation of dataset step type section -> jobs/<job>/steps/<step>/configuration/<stepType>
        from model.

        @param step_config:
        @param parent_category_step: parent step configuration for the same category

        @return: dict representation of dataset step process configuration section.
        """
        step_category = self._get_step_difw_category(step_config)
        step_type = self._get_step_difw_type(step_config)
        converted_attributes = self._convert_dynamic_attributes_to_simple_dict(step_config.definition["attributes"])
        if step_category in [self.converter.DIFW_STEP_CATEGORY_PROCESS,
                             self.converter.DIFW_STEP_CATEGORY_TRANSFORMATION]:
            depends_on_value = '__FIRST__' if parent_category_step is None else parent_category_step.component_name
            step_type_config = {step_config.component_name: {"type": step_type, "depends_on": depends_on_value}}
            step_type_config[step_config.component_name].update(converted_attributes)
        elif step_category == self.converter.DIFW_STEP_CATEGORY_OUTPUT:
            step_type_config = {"writer": step_type}
            step_type_config.update(converted_attributes)
        else:
            step_type_config = {"format": step_type}
            step_type_config.update(converted_attributes)
        return step_type_config

    @staticmethod
    def _create_job_spark_configuration_section(job_steps):
        """
        Create dict representation of spark config section -> jobs/<job>/spark_config from model.
        @param job_steps:
        @return: dict of spark config
        """
        spark_config_section = {}
        for job_step in job_steps:
            spark_config_section.update(job_step.definition.get("componentProperties", {}).get("sparkConfig", {}))
        return spark_config_section

    @staticmethod
    def copy_and_replace_template_attr(attr_template: dict, attr_value):
        """
        Take definition of attr_template, copy it and assign correct value

        @param attr_template: template of attribute
        @param attr_value: new value of attribute

        @return attr_template: new representation of attribute
        """
        copy_attr = copy.deepcopy(attr_template)
        copy_attr["value"] = attr_value
        return copy_attr

    #
    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    # CUSTOM CODE PROCESSING METHODS
    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    #

    @staticmethod
    def _custom_code_extract_basic_attrs(job_step, basic_dependencies_attr_name):
        """
        Method will return the basic attributes plus custom dependencies attr
        """
        filename_attribute = {}
        basic_additional_attribute = {}
        s3_assume_role_attribute = {}
        runtime_dependencies_attribute = {}
        custom_process_attributes = {}
        attributes_list = job_step.definition['attributes']
        for attr in attributes_list:
            if attr['type']['objectType'] == 'file':
                filename_attribute = attr
            if attr['attributeName'] == basic_dependencies_attr_name:
                basic_additional_attribute = attr
            if attr['attributeName'] == "runtime_python_packages":
                runtime_dependencies_attribute = attr
            if attr['attributeName'] == 's3_assume_role':
                s3_assume_role_attribute = attr
            if attr['attributeName'] == 'custom_parameters':
                custom_process_attributes = attr
        available_custom_step_attrs = [{
            "attributeName": "s3_path",
            "type": {"objectType": "string"},
            "value": filename_attribute["type"]['s3Location']
        }, {
            "attributeName": "filename",
            "type": {"objectType": "string"},
            "value": filename_attribute["type"]['fileName']
        }, {
            "attributeName": "s3_bucket",
            "type": {"objectType": "string"},
            "value": "{{data_bucket}}" if filename_attribute["type"][
                                              'bucketType'] == "data_bucket" else "{{resources_bucket}}"
        }, {
            "attributeName": "s3_assume_role",
            "type": {"objectType": "string"},
            "value": s3_assume_role_attribute.get("value", "")
        }, ]
        if custom_process_attributes:
            available_custom_step_attrs.append(custom_process_attributes)
        return available_custom_step_attrs, basic_additional_attribute, runtime_dependencies_attribute

    def _custom_append_additional_dependencies(self, job_config, basic_dependencies_attribute, language_type):
        """
        Append additional dependencies into job config
        """
        if basic_dependencies_attribute.get('value', []):
            # if setup dose not exists in job config then add new one
            if f"additional_{language_type}_packages" not in job_config:
                job_config[f"additional_{language_type}_packages"] = {
                    "index_url": "https://artifacts.merck.com/artifactory/api/pypi/pypi-main-dev/simple",
                    "packages": []
                }
            # add configured dependencies from model
            packages = job_config[f"additional_{language_type}_packages"]["packages"]
            for item in self._get_attr_value_from_dynamic_attribute(basic_dependencies_attribute):
                packages.append(f"{item['library_name']}=={item['library_version']}")
            # remove duplicates if any
            job_config[f"additional_{language_type}_packages"]["packages"] = sorted([*set(packages)])

    def _custom_append_runtime_python_dependencies(self, job_config, runtime_dependencies_attribute):
        """
        Append runtime python dependencies into job config
        """
        if runtime_dependencies_attribute.get('value', []):
            # if setup does not exists in job config then add new one
            if "runtime_python_packages" not in job_config:
                job_config["runtime_python_packages"] = {
                    "install_retries": 1,
                    "install_delay": 10,
                    "upgrade_pip": True,
                    "add_no_dependency_flag": False,
                    "index_url": "https://artifacts.merck.com/artifactory/api/pypi/pypi-main-dev/simple",
                    "packages": []
                }
            packages = job_config["runtime_python_packages"]["packages"]
            for item in self._get_attr_value_from_dynamic_attribute(runtime_dependencies_attribute):
                packages.append(f"{item['library_name']}=={item['library_version']}")
            # remove duplicates if any
            job_config["runtime_python_packages"]["packages"] = sorted([*set(packages)])

    def _custom_step_process_custom_python_processor(self, job_step, job_config, **kwargs):
        """
        Custom processing of step 'custom_python_processor'

        @param job_step: step configuration
        @param job_config: job configuration
        @return: N/A
        """
        self._process_custom_code_step("python", 'additional_python_packages', job_step, job_config)

    def _custom_step_process_custom_python_loader(self, job_step, job_config, **kwargs):
        """
        Custom processing of step 'custom_python_loader'

        @param job_step: step configuration
        @param job_config: job configuration
        @return: N/A
        """
        self._process_custom_code_step("python", 'additional_python_packages', job_step, job_config)

    def _custom_step_process_custom_spark_loader(self, job_step, job_config, **kwargs):
        """
        Custom processing of step 'custom_spark_loader'

        @param job_step: step configuration
        @param job_config: job configuration
        @return: N/A
        """
        self._process_custom_code_step("spark", 'additional_spark_packages', job_step, job_config)

    def _custom_step_process_custom_spark_writer(self, job_step, job_config, **kwargs):
        """
        Custom processing of step 'custom_spark_writer'

        @param job_step: step configuration
        @param job_config: job configuration
        @return: N/A
        """
        self._process_custom_code_step("spark", 'additional_spark_packages', job_step, job_config)

    def _custom_step_process_custom_spark_processor(self, job_step, job_config, **kwargs):
        """
        Custom processing of step 'custom_spark_processor'

        @param job_step: step configuration
        @param job_config: job configuration
        @return: N/A
        """
        self._process_custom_code_step("spark", 'additional_spark_packages', job_step, job_config)

    def _custom_step_process_custom_spark_transformer(self, job_step, job_config, **kwargs):
        """
        Custom processing of step 'custom_spark_transformer'

        @param job_step: step configuration
        @param job_config: job configuration
        @return: N/A
        """
        self._process_custom_code_step("spark", 'additional_spark_packages', job_step, job_config)

    def _process_custom_code_step(self, type_of_step: str, packages_type: str, job_step: EntityPipelineSteps,
                                  job_config: dict):
        """
        Process custom code step

        @param type_of_step: type of step. Can be spark or python
        @param packages_type: packages type. Can be additional_spark_packages or additional_python_packages
        @return: N/A
        """
        basic_attributes, basic_dependencies_attribute, runtime_dependencies_attribute = \
            self._custom_code_extract_basic_attrs(job_step, packages_type)
        self._custom_append_additional_dependencies(job_config, basic_dependencies_attribute, type_of_step)
        self._custom_append_runtime_python_dependencies(job_config, runtime_dependencies_attribute)
        job_step.definition['attributes'] = basic_attributes

    @staticmethod
    def _custom_step_process_local_file(job_step, **kwargs):
        """
        Convert acq from local to acq from s3

        @param job_step: step configuration
        @return: N/A
        """
        file_name_attr_type = job_step.definition['attributes'][0]["type"]
        source_delete_value = True
        for attr in job_step.definition['attributes']:
            if attr["attributeName"] == "source_delete":
                source_delete_value = attr['value']
                break
        job_step.definition['componentType'] = 's3'
        job_step.definition['attributes'] = [
            {
                "attributeName": "source_path",
                "type": {
                    "objectType": "string"
                },
                "value": file_name_attr_type['s3Location']
            },
            {
                "attributeName": "file_regex",
                "type": {
                    "objectType": "string"
                },
                # escape all special characters
                "value": re.sub(r'(\W)', r'\\\1', file_name_attr_type['fileName'])
            },
            {
                "attributeName": "source_delete",
                "type": {
                    "objectType": "boolean"
                },
                "value": source_delete_value
            },
            {
                "attributeName": "static_file_location",
                "type": {
                    "objectType": "boolean"
                },
                "value": False
            }
        ]
        # in case of calling this as via start with runtime parameters, we do not want to add the
        # following attributes, as they are having placeholders, which are called in resource generator,
        # as part of runtime we are not calling resource generator and these attributes would not be replaced
        # in normal non-runtime call we need to add these params
        if not kwargs.get("is_runtime"):
            job_step.definition["attributes"].append(
                {
                    "attributeName": "source_s3_bucket",
                    "type": {
                        "objectType": "string"
                    },
                    "value": "{{data_bucket}}" if file_name_attr_type['bucketType'] == "data_bucket"
                    else "{{resources_bucket}}"
                })
            job_step.definition["attributes"].append(
                {
                    "attributeName": "s3_bucket",
                    "type": {
                        "objectType": "string"
                    },
                    "value": "{{data_bucket}}"
                })
            job_step.definition["attributes"].append({
                "attributeName": "s3_layer_path",
                "type": {
                    "objectType": "string"
                },
                "value": "{{s3_paths.b_path}}"
            })
