from middleware.common.entity_management.entities.entity_base_pipeline import EntityBasePipeline
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_catalogs import EntityCatalogs
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.entity_management.entities.entity_pipeline_steps import EntityPipelineSteps
from middleware.common.entity_management.entities.entity_pipeline_notifications import EntityPipelineNotification
from middleware.common.entity_management.entities.entity_schedule import EntitySchedule
from middleware.common.entity_management.entities.entity_advanced_options import EntityAdvancedOptions
from middleware.common.metadatabase.model.difw_metadb_model import Objects, ObjectsACL


class EntityPipelineTemplate(EntityBasePipeline):
    """
    Entity Pipeline Template
    """

    def __init__(self, pipeline_template_name: str, pipeline_template_version=None, display_name=None,
                 description=None, framework_version=None, resource_prefix=None, platform=None, status=None,
                 enable_deferred_operators=None, schedule=None, notification=None, tags: dict = None,
                 advanced_options: EntityAdvancedOptions = None, catalogs=None, acl=None, steps: list = None):
        super().__init__(pipeline_template_name, pipeline_template_version, display_name, description,
                         framework_version, resource_prefix, platform, status,
                         enable_deferred_operators, schedule, notification, tags, advanced_options, catalogs,
                         acl, steps)
        self._pipeline_template_name = pipeline_template_name

    @property
    def pipeline_template_name(self):
        """
        get pipeline template name

        return pipeline template_name
        """
        return self._pipeline_template_name

    @staticmethod
    def from_json_dict(pipeline_template_model):
        """
        Create class instance from model/dict/request
        """
        return EntityPipelineTemplate(
            pipeline_template_name=pipeline_template_model['pipelineTemplateName'],
            pipeline_template_version=pipeline_template_model.get('pipelineTemplateVersion', '1.0.0'),
            display_name=pipeline_template_model['displayName'],
            description=pipeline_template_model['description'],
            framework_version=pipeline_template_model['frameworkVersion'],
            resource_prefix=pipeline_template_model['resourcePrefix'],
            platform=pipeline_template_model['platform'],
            status=pipeline_template_model.get('status', "drafted"),
            enable_deferred_operators=pipeline_template_model.get('enableDefferOperators', False),
            schedule=EntitySchedule.from_json_dict(pipeline_template_model.get('scheduling', {})),
            notification=EntityPipelineNotification.from_json_dict(pipeline_template_model.get('notifications', {})),
            tags=pipeline_template_model.get('tags'),
            advanced_options=EntityAdvancedOptions.from_json_dict(pipeline_template_model.get('advancedOptions', {})),
            catalogs=EntityCatalogs.from_json_dict(pipeline_template_model.get("catalogs")),
            acl=[EntityACL.from_json_dict_object_acl(request_acl)
                 for request_acl in pipeline_template_model.get("acl", [])],
            steps=[
                EntityPipelineSteps.from_json_dict(step, pipeline_template_model['frameworkVersion']) for step in
                pipeline_template_model['steps']]
        )

    @property
    def _object_full_name(self):
        """
        Create full name of object
        """
        return f"{self.pipeline_template_name}.{ObjectTypesEnum.pipeline_template.value}"

    def to_json_dict(self, limited_view: bool = False, default_project_values: bool = False):
        """
        return json definition of Entity Pipeline Template

        :return: json object of Entity Pipeline Template
        """
        json_dict = {
            'pipelineTemplateName': self._pipeline_template_name,
            "displayName": self.display_name,
            "description": self.description,
            "frameworkVersion": self.framework_version,
            "resourcePrefix": self.resource_prefix,
            "platform": self.platform,
            "status": self.status,
            "firstInputConnectorType": self.first_input_connector,
            "lastOutputConnectorType": self.last_output_connector,
            "enableDefferOperators": self.enable_deffer_operators,
            "scheduling": self.schedule_entity.to_json_dict() if self.schedule_entity else None,
            "notifications": self.notification.to_json_dict() if self.notification else None,
            "tags": self.tags,
            "advancedOptions": self.advanced_options.to_json_dict() if self.advanced_options else None,
            "catalogs": self.catalogs.to_json_dict() if self.catalogs else None,
            "acl": [acl_item.to_json_dict() for acl_item in self.acl],
            "steps": [step.to_json_dict() for step in self.steps]
        }
        if limited_view:
            # Remove the keys that are not needed in a limited view
            keys_to_remove = ["frameworkVersion", "resourcePrefix", "platform", "enableDefferOperators",
                              "scheduling", "notifications", "tags", "advancedOptions", "catalogs", "steps"]
            self.remove_keys(json_dict, keys_to_remove)

        if default_project_values:
            # update the un necessary keys to empty values or  empty list or empy dict
            json_dict.update({
                "firstInputConnectorType": None,
                "lastOutputConnectorType": None,
                "scheduling": {},
                "notifications": {},
                "acl": [],
                "steps": []
            })
            return json_dict
        return json_dict

    def to_metadb_object(self):
        db_object, component_db_object = super().to_metadb_object(is_pipeline_template=True)
        # You can add any additional fields specific to pipeline template here
        # For example you want to update OBJECT TYPE
        db_object.OBJECT_TYPE = ObjectTypesEnum.pipeline_template
        db_object.OBJECT_FULL_NAME = self._object_full_name

        # set pipeline template acls.
        for acl_item in self.acl:
            db_object.rel_objects_acl.append(
                ObjectsACL(OBJECT_FULL_NAME=self._object_full_name,
                           OBJECT_VERSION=self.entity_version,
                           SUBJECT_ID=acl_item.subject.subject_id,
                           RELATION_TYPE=acl_item.relation_type))
        return db_object, component_db_object

    @staticmethod
    def from_metadb_object(db_object_pipeline_template: Objects):
        """
        Convert db object to entity pipeline template
        """

        if db_object_pipeline_template is None:
            return None

        acl = []
        if db_object_pipeline_template.rel_objects_acl:
            for db_acl in db_object_pipeline_template.rel_objects_acl:
                acl.append(EntityACL.from_metadb_object_objects_acl(db_acl))

        steps = EntityPipelineSteps.from_metadb_objects(db_object_pipeline_template.rel_object_components)

        entity_pipeline_template = EntityPipelineTemplate(
            pipeline_template_name=db_object_pipeline_template.OBJECT_NAME,
            pipeline_template_version=db_object_pipeline_template.OBJECT_VERSION,
            description=db_object_pipeline_template.DESCRIPTION,
            display_name=db_object_pipeline_template.DISPLAY_NAME,
            framework_version=db_object_pipeline_template.DIFW_CORE_VERSION,
            acl=acl,
            steps=steps)
        EntityBasePipeline.convert_object_properties_to_entity_attributes(
            entity_pipeline_template,
            entity_pipeline_template.db_properties_mapping,
            db_object_pipeline_template.rel_object_properties
        )
        return entity_pipeline_template

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of entity pipeline templates
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntityPipelineTemplate.from_metadb_object(db_object))
        return result

