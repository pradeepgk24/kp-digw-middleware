from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline
from middleware.common.entity_management.entities.entity_pipeline_table import EntityPipelineTable, \
    EntityPipelineTableStep


class PipelineTablesConfigResolver(ConfigPartResolver):
    """
    Resolve pipeline table related configuration
    """

    def resolve_model_to_config(self, entity_pipeline: EntityPipeline, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """
        table_configuration_result = []

        component_step_name_mapping = self.converter.get_context_property("component_step_name_mapping")
        condition_type = self.converter.get_context_property("source_condition_type")

        # init resolvers
        glue_table_config_resolver = PipelineTableGlueConfigResolver(self.converter)
        airflow_table_config_resolver = PipelineTableAirflowConfigResolver(self.converter)

        # loop table by table and resolve table specific configurations
        for entity_pipeline_table in entity_pipeline.tables:
            entity_pipeline_table: EntityPipelineTable = entity_pipeline_table
            # basic attributes
            table_config = {}
            # enhance by config related with glue platform
            _, glue_related_table_config = glue_table_config_resolver.resolve_model_to_config(entity_pipeline_table)
            table_config.update(glue_related_table_config)
            # enhance by config related with glue airflow
            _, airflow_related_table_config = airflow_table_config_resolver.resolve_model_to_config(
                entity_pipeline_table)
            table_config.update(airflow_related_table_config)

            # other table config
            self.map_object_attr_to_dict_bulk(
                entity_pipeline_table,
                table_config,
                [
                    (["table_name"], ["name"]),
                    (["source_table_name"], ["original_table_name"]),
                    (["target_table_name"], ["target_table"]),
                    (["load_type"], ["ingest_strategy"]),
                    (["incremental_strategy_no_update"], ["incremental_strategy_no_update"]),
                    (["incremental_condition"], ["incremental_condition", "condition"]),
                    (["primary_keys"], ["primary_key", "columns"]),
                    (["static_partitions"], ["static_partitions"]),
                    (["dynamic_partitions"], ["dynamic_partitions"]),
                    (["refresh_rate"], ["refresh_rate"]),
                    (["depends_on"], ["dependency"]),
                ]
            )
            if entity_pipeline_table.incremental_condition is not None:
                table_config["incremental_condition"]["condition_type"] = condition_type
            if entity_pipeline_table.primary_keys:
                table_config["primary_key"]["name"] = f"pk_{entity_pipeline_table.table_name}"
            table_config.update(
                self._create_table_step_configuration_section(
                    entity_pipeline_table.steps,
                    component_step_name_mapping
                )
            )
            table_configuration_result.append(table_config)
        # will be place into global configuration
        return "tables[:]", table_configuration_result

    def _create_table_step_configuration_section(self, table_steps: list[EntityPipelineTableStep],
                                                 component_step_name_mapping: dict[str, tuple[str, str, str, str]]
                                                 ) -> dict:
        """
        Create step configuration section for tables

        @params table_steps: list of table steps
        @param component_step_name_mapping - dict of mapping with the following values
            - key = name of step from UI (componentName
            - value = tuple of (job name, job category, step name from config, difw step category)
        """
        step_config = {}
        job_config = {}
        for table_step in table_steps:
            component_name_to_overwrite = table_step.component_name
            table_attributes = table_step.overwrite_model_attributes
            difw_job_name, difw_job_category, difw_step_name, difw_step_category = \
                component_step_name_mapping[component_name_to_overwrite]
            step_config_attributes = {}
            # here resolve step configuration
            # table:
            #   steps:
            #     <stepName>:
            #        <stepCategory>:
            #           attrs
            if difw_job_category == self.converter.DIFW_JOB_CATEGORY_STEPS:
                if difw_step_category in [self.converter.DIFW_STEP_CATEGORY_PROCESS,
                                          self.converter.DIFW_STEP_CATEGORY_TRANSFORMATION]:
                    step_config[difw_step_name] = {
                        difw_step_category: {component_name_to_overwrite: step_config_attributes}}
                else:
                    step_config[difw_step_name] = {difw_step_category: step_config_attributes}

                step_config_attributes.update(self._convert_dynamic_attributes_to_simple_dict(table_attributes))

            # here resolve sniffer or operator configuration
            # table:
            #   jobs:
            #     <jobName>:
            #        <sniffer|operator>:
            #           <sniffer|operator>_kwargs:
            #               attrs
            if difw_job_category in [self.converter.DIFW_JOB_CATEGORY_SNIFFER,
                                     self.converter.DIFW_JOB_CATEGORY_OPERATOR]:
                kwargs_attr_name = "operator_kwargs" if difw_job_category == self.converter.DIFW_JOB_CATEGORY_OPERATOR \
                    else "sensor_kwargs"
                class_attr = next((attr for attr in table_attributes if attr["attributeName"] == kwargs_attr_name),
                                  None)
                # if kwargs attr is already present then move it into level back in order to prevent to have to levels
                # of kwargs attr
                # <sniffer|operator>:
                #   <sniffer|operator>_kwargs: OK
                #      <sniffer|operator>_kwargs: NOT OK
                converted_attributes = {}
                if class_attr:
                    table_attributes.remove(class_attr)
                    converted_attributes.update(self._convert_dynamic_attributes_to_simple_dict(
                        class_attr["type"]["attributes"]))
                # if there are still any attributes then convert it also
                if table_attributes:
                    converted_attributes.update(self._convert_dynamic_attributes_to_simple_dict(table_attributes))

                job_config[difw_job_name] = {
                    difw_job_category: {
                        kwargs_attr_name: converted_attributes
                    }
                }

        config_result = {}
        if step_config:
            config_result["steps"] = step_config
        if job_config:
            config_result["jobs"] = job_config
        return config_result


class PipelineTableAirflowConfigResolver(ConfigPartResolver):
    """
    Resolve table airflow related configuration
    """

    def resolve_model_to_config(self, entity_pipeline_table: EntityPipelineTable, **kwargs) -> (str, dict):
        config_part = {}
        self.map_object_attr_to_dict_bulk(
            entity_pipeline_table,
            config_part,
            [
                (["airflow_pool_name"], ["airflow_pool"]),
                (["airflow_pool_slots"], ["airflow_pool_slots"]),
            ]
        )
        # will be place into global configuration
        return None, config_part


class PipelineTableGlueConfigResolver(ConfigPartResolver):
    """
    Resolve table configurations related with AWS Glue platform
    """

    def resolve_model_to_config(self, entity_pipeline_table: EntityPipelineTable, **kwargs) -> (str, dict):
        config_part = {}
        # this depends on main entity pipeline configuration
        entity_pipeline: EntityPipeline = self.converter.get_context_property("input_entity")
        if entity_pipeline.platform == "glue":
            self.map_object_attr_to_dict_bulk(
                entity_pipeline_table,
                config_part,
                [
                    (["advanced_options", "entity_glue_options", "spark_configuration"], ["spark_config"]),
                    (["advanced_options", "entity_glue_options", "java_system_properties"], ["system_properties"]),
                    (["advanced_options", "entity_glue_options", "number_of_workers"], ["num_workers"]),
                    (["advanced_options", "entity_glue_options", "worker_type"], ["worker_type"]),
                    (["advanced_options", "entity_glue_options", "autoscaling"], ["enable_auto_scaling"])
                ]
            )
            spark_sql_settings = self._create_sql_spark_configuration_section(
                entity_pipeline_table.advanced_options.entity_glue_options.spark_sql_configuration
            )
            if spark_sql_settings:
                config_part["spark_sql_settings"] = spark_sql_settings
        # will be place into root of table configuration
        return None, config_part