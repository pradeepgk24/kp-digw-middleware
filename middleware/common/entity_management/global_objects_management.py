from middleware.common.helpers.exception import NoDataError
from middleware.api.common.helpers import SortAndPaginate
from middleware.common.entity_management.entities.entity_component_template import EntityComponentTemplate
from middleware.common.entity_management.entities.entity_global_object import EntityGlobalObject
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline
from middleware.common.entity_management.entities.entity_pipeline_template import EntityPipelineTemplate
from middleware.common.entity_management.entities.entity_workflow import EntityWorkflow
from middleware.common.entity_management.objects_management import ObjectsManagement
from middleware.common.metadatabase.component_templates_metadata_provider import ComponentTemplateMetadataProvider
from middleware.common.metadatabase.global_objects_metadata_provider import GlobalObjectsMetadataProvider
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.metadatabase.objects_metadata_provider import ObjectsMetadataProvider


class GlobalObjectsManagement(ObjectsManagement):
    """
    Global Objects Management.
    """
    object_type_mapping = {"pipeline": {"object_name": "pipelineName", "object_version": "pipelineVersion",
                                        "entity": EntityPipeline, "object_type": ObjectTypesEnum.pipeline},
                           "workflow": {"object_name": "workflowName", "object_version": "workflowVersion",
                                        "entity": EntityWorkflow, "object_type": ObjectTypesEnum.workflow},
                           "pipelineTemplate": {"object_name": "pipelineTemplateName",
                                                "object_version": "pipelineTemplateVersion",
                                                "entity": EntityPipelineTemplate,
                                                "object_type": ObjectTypesEnum.pipeline_template}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._global_objects_metadata_provider = None
        self._objects_metadata_provider = None
        self._component_templates_metadata_provider = None

    @property
    def global_objects_metadata_provider(self):
        """
        Global objects metadata provider
        """
        if self._global_objects_metadata_provider is None:
            self._global_objects_metadata_provider = GlobalObjectsMetadataProvider(self.logger,
                                                                                   self.metadatabase_connection,
                                                                                   self.lambda_secrets_manager)
        return self._global_objects_metadata_provider

    @property
    def objects_metadata_provider(self):
        """
        Objects metadata provider
        """
        if self._objects_metadata_provider is None:
            self._objects_metadata_provider = ObjectsMetadataProvider(self.logger, self.metadatabase_connection,
                                                                      self.lambda_secrets_manager)
        return self._objects_metadata_provider

    @property
    def component_templates_metadata_provider(self):
        """
        Component templates metadata provider
        """
        if self._component_templates_metadata_provider is None:
            self._component_templates_metadata_provider = ComponentTemplateMetadataProvider(
                self.logger, self.metadatabase_connection, self.lambda_secrets_manager)
        return self._component_templates_metadata_provider

    # pylint: disable=too-many-locals
    def global_object_search(self, object_type: str = None, cross_project_search: bool = False, name: str = None,
                             excluded_projects: [str] = None, sort_and_paginate: SortAndPaginate = None):
        """
        Get objects types under a given projects.
        @param object_type: type of the object
        @param cross_project_search: flag indicates if object needs to search across projects
        @param name: name
        @param excluded_projects:  list of project names that needs to be excluded
        @param sort_and_paginate: for pagination

        @return
        """
        self.logger.info("Starting method global_object_search")
        current_project = self.project_id
        # if we want to search across projects, overwrite the current_project to None
        if cross_project_search:
            current_project = None
        # if object type is componentTemplate obtain them from method
        if object_type == "componentTemplate":
            # for each component template we need to obtain its component type/category/versions
            component_templates_objects, total_count_objects = self.global_objects_metadata_provider. \
                get_global_component_templates(user_id=self.user_isid, component_template_name=name,
                                               current_project=current_project, excluded_projects=excluded_projects,
                                               sort_and_paginate=sort_and_paginate)
            global_objects_entities = EntityGlobalObject.from_metadb_objects(component_templates_objects,
                                                                             is_component_template=True)
        # else the object type is one of workflow, pipeline, pipelineTemplate, obtain them from method with filtrating
        # on object_type
        else:
            object_type = ObjectTypesEnum.pipeline_template \
                if object_type == "pipelineTemplate" else ObjectTypesEnum.from_str(object_type)
            objects_db, total_count_objects = self.global_objects_metadata_provider.get_global_objects(
                user_id=self.user_isid, object_type=object_type, object_name=name,
                current_project=current_project, excluded_projects=excluded_projects,
                sort_and_paginate=sort_and_paginate)
            global_objects_entities = EntityGlobalObject.from_metadb_objects(objects_db, is_component_template=False)
            # if we collected pipelines or pipeline templates add input and output names for connectors
            if object_type != ObjectTypesEnum.workflow:
                for object_from_db in global_objects_entities:
                    first_input_connector, last_output_connector = self.get_first_and_last_steps_connectors(
                        object_from_db.entity.steps)
                    object_from_db.entity.set_first_and_last_connector_info(first_input_connector,
                                                                            last_output_connector)
        if total_count_objects == 0:
            raise NoDataError(f"No objects of type {object_type} which are accessible based on given filters: "
                              f"cross_project_search: {cross_project_search}, object name: {name},"
                              f" excluded projects: {excluded_projects}.")
        # set environments based on the project ids, to avoid unnecessary calls we save the results in dict
        env_dict = {}
        for global_object in global_objects_entities:
            # if the project_id is not yet in dict, obtain its env
            if global_object.project_id not in env_dict:
                env_dict[global_object.project_id] = self.project_settings_management.get_project_environment(
                    global_object.project_id)
            # set the environment
            global_object.set_environment(env_dict[global_object.project_id])

        global_objects_result_list = [entity.to_json_dict() for entity in global_objects_entities]
        return global_objects_result_list, total_count_objects

    def get_global_object_detail(self, project_instance_name: str, project_id: str, env: str, object_type: str,
                                 object_identifiers: dict):
        """
        Get global object details

        @param project_instance_name:
        @param project_id: id of the project
        @param object_type: type of object can be one among pipeline, pipelineTemplate,
        componentTemplate, workflow
        @param env: environment
        @param object_identifiers: object identifiers

        @returns details of given object type and object identifier.
        """
        self.logger.info(
            f"User {self.user_isid} starts method get_global_object_detail with object_identifier={object_identifiers},"
            f" type {object_type}, project {project_id}, UI instance {project_instance_name} and environment {env}")
        # for now as we are locked inside one instance and DB, we do not need to specify project_instance_name and
        # project_name
        if object_type == "componentTemplate":
            # component templates have only one identifier
            template_id = int(object_identifiers.get("templateId"))
            retrieved_object = EntityComponentTemplate.from_metadb_object(
                self.component_templates_metadata_provider.get_component_template(
                    template_id, self.user_isid))
            if not retrieved_object:
                raise NoDataError(f"There is no object of type {object_type}"
                                  f" with templateId {template_id}.")
        else:
            # use mapping defined in this class to simlify the logic
            object_name = object_identifiers.get(self.object_type_mapping.get(object_type).get("object_name"))
            object_version = object_identifiers.get(
                self.object_type_mapping.get(object_type).get("object_version"), "1.0.0")
            # collect entity for using to correctly call from_metadb_object
            entity = self.object_type_mapping.get(object_type).get("entity")
            # set object_type into correct format
            object_type = self.object_type_mapping.get(object_type).get("object_type")
            retrieved_object = entity.from_metadb_object(
                self.objects_metadata_provider.get_object(object_name=object_name, object_version=object_version,
                                                          object_type=object_type, user_id=self.user_isid))
            if not retrieved_object:
                raise NoDataError(f"There is no object of type {object_type}"
                                  f" with name {object_name} and version {object_version}")
            if object_type in (ObjectTypesEnum.pipeline, ObjectTypesEnum.pipeline_template):
                first_input_connector, last_output_connector = self.get_first_and_last_steps_connectors(
                    retrieved_object.steps)
                retrieved_object.set_first_and_last_connector_info(first_input_connector, last_output_connector)
        return retrieved_object
