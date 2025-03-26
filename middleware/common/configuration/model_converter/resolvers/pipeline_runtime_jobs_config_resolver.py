from middleware.common.configuration.model_converter.resolvers.pipeline_jobs_config_resolver import \
    PipelineJobsConfigResolver
from middleware.common.entity_management.entities.entity_pipeline_steps import EntityPipelineSteps


class PipelineRuntimeJobsConfigResolver(PipelineJobsConfigResolver):
    """
    Resolve jobs part of related pipeline, is child of PipelineJobsConfigResolver, as we are using its method
    """

    def resolve_model_to_config(self, entity_pipeline, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter. We are using the parent definition of the method, but
        also enhancing it with secondary method call to replace the old values with the new runtime values
        @param entity_pipeline pipeline entity
        @param **kwargs
        @rtype tuple of (str, dict)
        @return runtime config
        """
        # get the config
        _, job_config = super().resolve_model_to_config(entity_pipeline, **kwargs)
        # get component step name mapping as we need it in following method
        component_step_name_mapping = self.converter.get_context_property("component_step_name_mapping")
        # remap the new values onto the old
        runtime_step_parameters = self.create_runtime_step_configuration_section(kwargs.get("pipeline_steps"),
                                                                                 component_step_name_mapping)

        pipeline_step_names: {str, (dict, dict)} = {}

        for job in job_config:
            pipeline_step_names.update({step_job['name']: (step_job, job) for step_job in job.get("steps", [])})

        for step_name, (step_job, job) in pipeline_step_names.items():
            runtime_step_config = runtime_step_parameters.get(step_name, {})
            if runtime_step_config:
                # overwrite step config with only new runtime params
                step_job["configuration"] = runtime_step_config
            else:
                job.get("steps").remove(step_job)
                # clear empty jobs
                if not job.get("steps"):
                    job_config.remove(job)
        # clean out and keep only name and steps
        job_config_clean = [{"name": job.get("name"), "steps": job.get("steps")} for job in job_config
                            if job.get("steps")]
        return "jobs[:]", job_config_clean

    def create_runtime_step_configuration_section(self, steps: [EntityPipelineSteps],
                                                  component_step_name_mapping:
                                                  dict[str, tuple[str, str, str, str]]) -> dict:
        """
        Create step configuration section for jobs

        @param steps: list of pipeline steps
        @param component_step_name_mapping - dict of mapping with the following values
            - key = name of step from UI (componentName)
            - value = tuple of (step name from config, difw step category)
        @rtype dict
        @return dictionary of new runtime overwritten values
        """
        step_config = {}
        for step in steps:
            component_name_to_overwrite = step.component_name
            # first two keys are difw_job_name, difw_job_category = steps
            _, _, difw_step_name, difw_category = component_step_name_mapping[component_name_to_overwrite]
            component_type = step.definition.get('componentType')
            if hasattr(self, f"_custom_step_process_{component_type}"):
                # do deep copy of config list to not lost the reference to original resource
                step = step.create_copy()
                getattr(self, f"_custom_step_process_{component_type}")(
                    **{"job_step": step, "job_config": {}, "is_runtime": True})
            step_config_attributes = {}
            step_config_attributes.update(
                self._convert_dynamic_attributes_to_simple_dict(step.definition.get("attributes")))
            if difw_category in [self.converter.DIFW_STEP_CATEGORY_PROCESS,
                                 self.converter.DIFW_STEP_CATEGORY_TRANSFORMATION]:
                step_config[difw_step_name] = {difw_category: {component_name_to_overwrite: step_config_attributes}}
            # as may be several steps in each, we need to add them without overwriting them
            elif not step_config.get(difw_step_name):
                step_config[difw_step_name] = {difw_category: step_config_attributes}
            else:
                step_config[difw_step_name].update({difw_category: step_config_attributes})

        return step_config