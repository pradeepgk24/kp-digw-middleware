from middleware.common.entity_management.entities.entity_component_template import EntityComponentTemplate
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline
from middleware.common.entity_management.entities.entity_pipeline_template import EntityPipelineTemplate
from middleware.common.entity_management.entities.entity_workflow import EntityWorkflow
from middleware.common.metadatabase.model.types.component_templates_acl_relation_types_enum import \
    ComponentTemplatesACLRelationTypesEnum
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum


class EntityGlobalObject(EntityObject):
    object_mapping = {
        ObjectTypesEnum.pipeline: {
            "entity": EntityPipeline,
            "identifier_key": "pipelineName",
            "identifier_value": "pipeline_name",
            "name_key": "pipeline_name",
            "attributes": {
                "source_key": "first_input_connector",
                "target_key": "last_output_connector"
            }
        },
        ObjectTypesEnum.pipeline_template: {
            "entity": EntityPipelineTemplate,
            "identifier_key": "pipelineTemplateName",
            "identifier_value": "pipeline_template_name",
            "name_key": "pipeline_template_name",
            "attributes": {
                "source_key": "first_input_connector",
                "target_key": "last_output_connector"
            }
        },
        ObjectTypesEnum.workflow: {
            "entity": EntityWorkflow,
            "identifier_key": "workflowName",
            "identifier_value": "workflow_name",
            "name_key": "workflow_name",
            "attributes": {}
        },
        ObjectTypesEnum.component_template: {
            "entity": EntityComponentTemplate,
            "identifier_key": "templateId",
            "identifier_value": "template_id",
            "name_key": "template_name",
            "attributes": None
        }
    }

    def __init__(self, entity, object_type: ObjectTypesEnum, project_id: str = None, project_name: str = None,
                 environment: str = None, object_attributes: dict = None):
        self._entity = entity
        self._object_type = object_type
        self._project_id = project_id
        self._project_name = project_name
        self._environment = environment
        self._object_attributes = object_attributes

    @property
    def entity(self):
        """
        Get the entity

        @return: entity.
        """
        return self._entity

    @property
    def object_type(self):
        """
        Get the type of the object.

        @return: Object type.
        """
        return self._object_type

    @property
    def project_id(self):
        """
        Get the project_id

        @return: project_id.
        """
        return self._project_id

    def set_project_id(self, project_id):
        """
        Set the project_id

        @param project_id: New project_id
        """
        self._project_id = project_id

    @property
    def project_name(self):
        """
        Get the name of the regular UI project where the object belongs.

        @return: Name of the project.
        """
        return self._project_name

    def set_project_name(self, project_name):
        """
        Set the project_name

        @param project_name: New project_name
        """
        self._project_name = project_name

    @property
    def environment(self):
        """
        Get the environment of the project to which the object belongs.

        @return: Environment of the project.
        """
        return self._environment

    def set_environment(self, environment):
        """
        Set the environment

        @param environment: New environment
        """
        self._environment = environment

    @property
    def object_attributes(self):
        """
        Get the object_attributes

        @return: object_attributes
        """
        return self._object_attributes

    def to_json_dict(self):
        """
        Convert the CustomEntity instance to a JSON-compatible dictionary.

        @return: JSON-compatible dictionary representing the CustomEntity instance.
        """
        dict_out = {
            "objectType": self.object_type.value,
            "description": self.entity.description,
            "projectInstanceName": "DIFW_UI",
            "projectId": self.project_id,
            "projectName": self.project_name,
            "environment": self.environment,
            "objectAttributes": self.object_attributes
        }
        # additional properties are type dependant, and we will obtain them from the mapping
        object_type_mapping = self.object_mapping.get(self.object_type)
        dict_out["objectIdentifiers"] = [
            {object_type_mapping["identifier_key"]: getattr(self.entity, object_type_mapping["identifier_value"])}]
        dict_out["name"] = getattr(self.entity, object_type_mapping["name_key"])
        # in case of pipelines and pipeline templates we want to add the object_attributes, for component templates
        # the object_attributes are already there as part of self.object_attributes
        if object_type_mapping["attributes"]:
            dict_out["objectAttributes"] = {
                "source": getattr(self.entity, object_type_mapping["attributes"]["source_key"]),
                "target": getattr(self.entity, object_type_mapping["attributes"]["target_key"])
            }
        return dict_out

    @staticmethod
    def from_metadb_objects(db_objects: list, is_component_template: bool = False):
        """
        Convert list of db objects to list of entity objects
        @param db_objects: list of objects
        @param is_component_template: true if passed in are component templates
        """
        if not db_objects:
            return []
        result = []
        if is_component_template:
            for db_object in db_objects:
                entity_component_template = EntityComponentTemplate.from_metadb_object(db_object)
                # in case of component template the object_attributes are handled here,
                # as we have all necessary information for it
                object_attributes = {
                    "category": entity_component_template.entity_component_type.component_category.value,
                    "type": entity_component_template.entity_component_type.component_type_name,
                    "frameworkVersion": entity_component_template.entity_component_type.difw_core_version}
                result.append(EntityGlobalObject(
                    entity=entity_component_template,
                    object_type=ObjectTypesEnum.component_template,
                    object_attributes=object_attributes))
            # set project ids and project name
            return EntityGlobalObject.set_project_id_and_project_name(result)

        for db_object in db_objects:
            object_type = db_object.OBJECT_TYPE
            object_type_mapping = EntityGlobalObject.object_mapping.get(object_type)
            result.append(
                EntityGlobalObject(entity=object_type_mapping.get("entity").from_metadb_object(db_object),
                                   object_type=object_type))
        # set project ids and project name
        return EntityGlobalObject.set_project_id_and_project_name(result)

    @staticmethod
    def set_project_id_and_project_name(global_objects: []):
        """
        method to set project id and project name
        """
        for global_object in global_objects:
            for acl in global_object.entity.acl:
                # if its is owner and project, set the values
                if (acl.relation_type == ObjectsACLRelationTypesEnum.owner or
                    acl.relation_type == ComponentTemplatesACLRelationTypesEnum.owner) and \
                        acl.subject.subject_type == SubjectTypesEnum.project:
                    global_object.set_project_name(acl.subject.display_name)
                    global_object.set_project_id(acl.subject.subject_id)
                    break
        return global_objects
