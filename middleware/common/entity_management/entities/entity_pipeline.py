import json
from datetime import datetime

from middleware.api.common.helpers import convert_to_bool
from middleware.common.entity_management.entities.entity_base_pipeline import EntityBasePipeline
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_catalogs import EntityCatalogs
from middleware.common.entity_management.entities.entity_pipeline_table import EntityPipelineTable
from middleware.common.helpers.datetime_formater import from_datetime_to_str
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.entity_management.entities.entity_pipeline_steps import EntityPipelineSteps
from middleware.common.entity_management.entities.entity_pipeline_notifications import EntityPipelineNotification
from middleware.common.entity_management.entities.entity_schedule import EntitySchedule
from middleware.common.entity_management.entities.entity_advanced_options import EntityAdvancedOptions
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.metadatabase.model.difw_metadb_model import Objects, ObjectsACL
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum


class EntityPipeline(EntityBasePipeline):
    """
    Entity Pipeline.
    """

    def __init__(self, pipeline_name: str, pipeline_version=None, display_name=None,
                 description=None, framework_version=None, resource_prefix=None, platform=None, status=None,
                 enable_deferred_operators=None, schedule=None, notification=None, tags: dict = None,
                 advanced_options=None, catalogs=None, acl=None, steps: list = None, is_enabled=None, airflow_link=None,
                 dag_id=None, tables: [EntityPipelineTable] = None, last_runtime: str = None,
                 next_run: datetime = None, last_run: datetime = None, is_draft: bool = None,
                 runtime_steps: [dict] = None):

        super().__init__(pipeline_name, pipeline_version, display_name, description, framework_version, resource_prefix,
                         platform, status, enable_deferred_operators, schedule, notification, tags,
                         advanced_options, catalogs, acl, steps)
        self._pipeline_name = pipeline_name
        self._pipeline_version = pipeline_version
        self._is_enabled = is_enabled
        self._airflow_link = airflow_link
        self._dag_id = dag_id
        self._tables = tables
        self._last_runtime = last_runtime
        self._next_run = next_run
        self._last_run = last_run
        self._is_draft = is_draft
        self._runtime_steps = runtime_steps

    @property
    def runtime_steps(self) -> list:
        """
        get runtime_steps

        @return: runtime_steps
        """
        if self._runtime_steps is None:
            self._runtime_steps = []
        return self._runtime_steps

    def set_runtime_steps(self, runtime_steps: list):
        """
        Set runtime_steps.

        @param runtime_steps:
        """
        self._runtime_steps = runtime_steps

    @property
    def last_runtime(self) -> str:
        """
        get last_runtime

        @return: last_runtime
        """
        return self._last_runtime

    def set_last_runtime(self, last_runtime: str):
        """
        Set last_runtime.

        @param last_runtime:
        """
        self._last_runtime = last_runtime

    @property
    def is_draft(self) -> bool:
        """
        get is_draft

        @return: is_draft flag
        """
        return self._is_draft

    def set_is_draft(self, is_draft: bool):
        """
        Set is_draft.

        @param is_draft:
        """
        self._is_draft = is_draft

    @property
    def next_run(self) -> datetime:
        """
        get next_run

        @return: next_run
        """
        return self._next_run

    def set_next_run(self, next_run: datetime):
        """
        Set next_run.

        @return: next_run
        """
        self._next_run = next_run

    @property
    def last_run(self) -> datetime:
        """
        get last_run

        @return: last_run
        """
        return self._last_run

    def set_last_run(self, last_run: datetime):
        """
        Set last_run.

        @param last_run:
        """
        self._last_run = last_run

    @property
    def pipeline_name(self) -> str:
        """
        get pipeline_name

        @return: pipeline_name
        """
        return self._pipeline_name

    def set_pipeline_name(self, pipeline_name: str):
        """
        Set pipeline_name.

        @param pipeline_name:
        """
        self._pipeline_name = pipeline_name

    @property
    def pipeline_version(self) -> str:
        """
        get pipeline_version

        @return: pipeline_version
        """
        return self._pipeline_version

    @property
    def airflow_link(self) -> str:
        """
        get airflow_link

        @return: airflow_link
        """
        return self._airflow_link

    def set_airflow_link(self, airflow_link: str):
        """
        Set airflow_link.

        @param airflow_link:
        """
        self._airflow_link = airflow_link

    @property
    def dag_id(self) -> str:
        """
        get dag_id

        @return: dag_id
        """
        return self._dag_id

    def set_dag_id(self, dag_id: str):
        """
        Set dag id.

        @param dag_id:
        """
        self._dag_id = dag_id

    @property
    def is_enabled(self) -> bool:
        """
        get is_enabled

        @return: is_enabled flag
        """
        return self._is_enabled

    @property
    def tables(self) -> [EntityPipelineTable]:
        """
        get tables

        @return: list of tables
        """
        if self._tables is None:
            self._tables = []
        return self._tables

    def set_tables(self, tables: [EntityPipelineTable]):
        """
        Set tables.

        @param tables:
        """
        self._tables = tables

    def set_is_enabled(self, is_enabled: bool):
        """
        Set is_enabled.

        @param is_enabled:
        """
        self._is_enabled = is_enabled

    @property
    def db_properties_mapping(self):
        """
        List of mapping of DB properties instance attributes and via versa
        """
        properties_mapping = super().db_properties_mapping
        properties_mapping.append(('airflowLink', 'PROPERTY_STRING_VALUE', "airflow_link"))
        properties_mapping.append(('dagId', 'PROPERTY_STRING_VALUE', "dag_id"))
        properties_mapping.append(('runtimeSteps', 'PROPERTY_LONGTEXT_VALUE', "runtime_steps", json.dumps, json.loads))
        return properties_mapping

    @staticmethod
    def from_json_dict(pipeline_model, is_create: bool = False):
        """
        Create class instance from model/dict/request
        @param pipeline_model: dict of model
        @param is_create: bool passed as True if we are creating the pipeline, to filter out the shared_template acls
        """

        pipeline_entity = EntityPipeline(
            pipeline_name=pipeline_model.get('pipelineName'),
            pipeline_version=pipeline_model.get('pipelineVersion', '1.0.0'),
            display_name=pipeline_model['displayName'],
            description=pipeline_model.get('description', None),
            framework_version=pipeline_model['frameworkVersion'],
            resource_prefix=pipeline_model['resourcePrefix'],
            platform=pipeline_model['platform'],
            status=pipeline_model.get('status', None),
            enable_deferred_operators=convert_to_bool(pipeline_model.get('enableDefferOperators', False)),
            schedule=EntitySchedule.from_json_dict(pipeline_model.get('scheduling', {})),
            notification=EntityPipelineNotification.from_json_dict(pipeline_model.get('notifications', {})),
            tags=pipeline_model.get('tags'),
            advanced_options=EntityAdvancedOptions.from_json_dict(pipeline_model.get('advancedOptions', {})),
            catalogs=EntityCatalogs.from_json_dict(pipeline_model.get("catalogs")),
            dag_id=pipeline_model.get("dagId"),
            airflow_link=pipeline_model.get("airflowLink"),
            acl=[EntityACL.from_json_dict_object_acl(request_acl)
                 for request_acl in pipeline_model.get("acl", [])],
            steps=[EntityPipelineSteps.from_json_dict(step, pipeline_model['frameworkVersion']) for step in
                   pipeline_model['steps']],
            runtime_steps=pipeline_model.get("runtimeSteps", []),
            is_enabled=convert_to_bool(pipeline_model.get("isEnabled", False))
        )
        if is_create:
            # as part of create we want to save only shared relation, if pipeline is created from template there is
            # also shared_template relation which we need to not add, owners are added later in upsert
            pipeline_entity.set_acl(
                EntityACL.filter_entity_acls(pipeline_entity.acl, ObjectsACLRelationTypesEnum.shared))
        pipeline_entity.set_tables(
            [EntityPipelineTable.from_json_dict(pipeline_table, pipeline_entity,
                                                pipeline_model['frameworkVersion']) for pipeline_table in
             pipeline_model.get("tables", [])])
        return pipeline_entity

    def to_json_dict(self, limited_view: bool = False):
        """
        return json definition of Entity Pipeline

        @return: json object of Entity Pipeline
        """
        json_dict = {
            'pipelineName': self.pipeline_name,
            'pipelineVersion': self.pipeline_version,
            "displayName": self.display_name,
            "description": self.description,
            "isEnabled": self.is_enabled,
            "frameworkVersion": self.framework_version,
            "resourcePrefix": self.resource_prefix,
            "platform": self.platform,
            "airflowLink": self.airflow_link,
            "dagId": self.dag_id,
            "status": self.status,
            "enableDefferOperators": self.enable_deffer_operators,
            "scheduling": self.schedule_entity.to_json_dict() if self.schedule_entity else None,
            "notifications": self.notification.to_json_dict() if self.notification else None,
            "firstInputConnectorType": self.first_input_connector,
            "lastOutputConnectorType": self.last_output_connector,
            "tags": self.tags if self.tags else {},
            "runtime": {
                "lastRuntime": self.last_runtime,
                "nextRun": from_datetime_to_str(self.next_run),
                "lastRun": from_datetime_to_str(self.last_run)
            },
            "advancedOptions": self.advanced_options.to_json_dict() if self.advanced_options else None,
            "catalogs": self.catalogs.to_json_dict() if self.catalogs else {},
            "acl": [acl_item.to_json_dict() for acl_item in self.acl],
            "runtimeSteps": self.runtime_steps,
            "steps": [step.to_json_dict() for step in self.steps],
            "tables": [table.to_json_dict() for table in self.tables]
        }
        if limited_view:
            # Remove the keys that are not needed in a limited view
            keys_to_remove = ["pipelineVersion", "frameworkVersion", "resourcePrefix", "platform", "airflowLink",
                              "enableDefferOperators", "dagId", "notifications", "tags", "advancedOptions",
                              "steps", "catalogs", "runtimeSteps",
                              "tables", "firstInputConnectorType", "lastOutputConnectorType"]
            self.remove_keys(json_dict, keys_to_remove)
        return json_dict

    @property
    def _object_full_name(self):
        """
        Create full name of object
        """
        return f"{self.pipeline_name}.{ObjectTypesEnum.pipeline.value}"

    def to_json_dict_orchestrator_info(self):
        """
        json definition of orchestrator information

        @return: json object of orchestrator information
        """
        return {
            'pipelineName': self.pipeline_name,
            "status": self.status,
            "runtime": {
                "lastRuntime": self.last_runtime,
                "nextRun": from_datetime_to_str(self.next_run),
                "lastRun": from_datetime_to_str(self.last_run)
            }
        }

    def to_metadb_object(self):
        db_object, db_object_components = super().to_metadb_object()
        # You can add any additional fields specific to pipeline here
        # For example you want to update OBJECT TYPE
        db_object.OBJECT_TYPE = ObjectTypesEnum.pipeline
        db_object.IS_ENABLED = self.is_enabled
        db_object.OBJECT_FULL_NAME = self._object_full_name

        # set pipeline acls
        for acl_item in self.acl:
            db_object.rel_objects_acl.append(
                ObjectsACL(OBJECT_FULL_NAME=self._object_full_name,
                           OBJECT_VERSION=self.entity_version,
                           SUBJECT_ID=acl_item.subject.subject_id,
                           RELATION_TYPE=acl_item.relation_type))

        db_table_components = []
        for table in self.tables:
            db_table_components.append(table.to_metadb_object())
        db_object.rel_children_objects = db_table_components
        return db_object, db_object_components

    @staticmethod
    def from_metadb_object(db_pipeline_object: Objects):
        """
        Convert db object to entity object
        """
        if db_pipeline_object is None:
            return None

        acl = []
        if db_pipeline_object.rel_objects_acl:
            for db_acl in db_pipeline_object.rel_objects_acl:
                acl.append(EntityACL.from_metadb_object_objects_acl(db_acl))

        steps = EntityPipelineSteps.from_metadb_objects(db_pipeline_object.rel_object_components)
        tables = EntityPipelineTable.from_metadb_objects(db_pipeline_object.rel_children_objects)

        entity_pipeline = EntityPipeline(
            pipeline_name=db_pipeline_object.OBJECT_NAME,
            pipeline_version=db_pipeline_object.OBJECT_VERSION,
            description=db_pipeline_object.DESCRIPTION,
            display_name=db_pipeline_object.DISPLAY_NAME,
            is_enabled=db_pipeline_object.IS_ENABLED,
            framework_version=db_pipeline_object.DIFW_CORE_VERSION,
            is_draft=db_pipeline_object.IS_DRAFT,
            acl=acl,
            steps=steps,
            tables=tables
        )
        EntityBasePipeline.convert_object_properties_to_entity_attributes(
            entity_pipeline,
            entity_pipeline.db_properties_mapping,
            db_pipeline_object.rel_object_properties
        )
        return entity_pipeline

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of entity objects
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntityPipeline.from_metadb_object(db_object))
        return result

    @property
    def get_project_owner(self) -> str:
        """
        obtain project owner from acl

        @return: str of project owner if given else None
        @rtype: str
        """
        for acl in self.acl:
            if acl.subject.subject_type == SubjectTypesEnum.project \
                    and acl.relation_type == ObjectsACLRelationTypesEnum.owner:
                return acl.subject.subject_id
        return None
