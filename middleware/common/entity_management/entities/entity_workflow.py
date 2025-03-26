import json
from datetime import datetime
from middleware.api.common.helpers import convert_to_bool
from middleware.common.entity_management.entities.entity_acl import EntityACL
from middleware.common.entity_management.entities.entity_base_pipeline import EntityBasePipeline
from middleware.common.entity_management.entities.entity_workflow_advanced_options import EntityWorkflowAdvancedOptions
from middleware.common.entity_management.entities.entity_workflow_notification import EntityWorkflowNotification
from middleware.common.helpers.datetime_formater import from_datetime_to_str, from_str_to_datetime
from middleware.common.metadatabase.model.difw_metadb_model import Objects, ObjectsACL, ObjectComponentsHierarchy, \
    ObjectComponents, Components
from middleware.common.entity_management.entities.entity_workflow_step import EntityWorkflowStep
from middleware.common.entity_management.entities.entity_airflow_notifications import EntityAirflowNotifications
from middleware.common.entity_management.entities.entity_schedule import EntitySchedule
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum


class EntityWorkflow(EntityObject):
    """
    Entity Workflow.
    """

    def __init__(self, workflow_name: str, workflow_version: str = None, display_name: str = None,
                 description: str = None, framework_version: str = None, is_enabled=None, resource_prefix: str = None,
                 status: str = None, enable_deffer_operators=None, schedule: EntitySchedule = None,
                 notification: EntityWorkflowNotification = None,
                 advanced_options: EntityWorkflowAdvancedOptions = None, acl: list = None,
                 steps: [EntityWorkflowStep] = None,
                 airflow_link=None, dag_id=None, last_runtime: str = None, next_run: datetime = None,
                 last_run: datetime = None, is_draft: bool = None):
        self._workflow_name = workflow_name
        self._workflow_version = workflow_version
        self._display_name = display_name
        self._description = description
        self._framework_version = framework_version
        self._is_enabled = is_enabled
        self._resource_prefix = resource_prefix
        self._status = status
        self._enable_deffer_operators = enable_deffer_operators
        self._schedule_entity = schedule
        self._notification = notification
        self._advanced_options = advanced_options
        self._acl = acl
        self._steps = steps
        self._airflow_link = airflow_link
        self._dag_id = dag_id
        self._last_runtime = last_runtime
        self._next_run = next_run
        self._last_run = last_run
        self._is_draft = is_draft

    @property
    def is_draft(self):
        """
        get is_draft

        return is_draft

        """
        return self._is_draft

    def set_is_draft(self, is_draft):
        """
        Set last_runtime.

        @return: last_runtime
        """
        self._is_draft = is_draft

    @property
    def workflow_name(self):
        """
        Get entity_name.

        @return entity_name
        """
        return self._workflow_name

    @property
    def workflow_version(self):
        """
        Get entity_version.

        @return entity_version
        """
        return self._workflow_version

    @property
    def display_name(self):
        """
        Get display_name.

        @return display_name
        """
        return self._display_name

    @property
    def description(self):
        """
        Get description.

        @return description
        """
        return self._description

    @property
    def framework_version(self):
        """
        Get difw_core_version.

        @return difw_core_version
        """
        return self._framework_version

    @property
    def is_enabled(self):
        """
        get is_enabled

        return is_enabled

        """
        return self._is_enabled

    @property
    def resource_prefix(self):
        """
        Get resource_prefix.

        @return resource_prefix
        """
        return self._resource_prefix

    def set_resource_prefix(self, resource_prefix):
        """
        Set resource_prefix.

        @param resource_prefix: new value of resource_prefix
        """
        self._resource_prefix = resource_prefix

    @property
    def airflow_link(self):
        """
        get airflow_link

        return airflow_link name

        """
        return self._airflow_link

    def set_airflow_link(self, airflow_link):
        """
        Set airflow_link.

        @return airflow_link
        """
        self._airflow_link = airflow_link

    @property
    def dag_id(self):
        """
        get dag_id

        return dag_id name

        """
        return self._dag_id

    def set_dag_id(self, dag_id):
        """
        Set dag_id.

        @return: dag_id
        """
        self._dag_id = dag_id

    @property
    def status(self):
        """
        Get status.

        @return status
        """
        return self._status

    def set_status(self, status):
        """
        Set status

        @param status: new value of status
        """
        self._status = status

    @property
    def enable_deffer_operators(self):
        """
        Get enable_deffer_operators.

        @return enable_deffer_operators
        """
        return self._enable_deffer_operators

    def set_enable_deffer_operators(self, enable_deffer_operators):
        """
        Set enable_deffer_operators

        @param enable_deffer_operators: new value of enable_deffer_operators
        """
        self._enable_deffer_operators = enable_deffer_operators

    @property
    def advanced_options(self):
        """
        get advanced_options

        return advanced_options
        """
        if self._advanced_options is None:
            self._advanced_options = EntityWorkflowAdvancedOptions()
        return self._advanced_options

    def set_advanced_options(self, advanced_options):
        """
        Set advanced_options

        @param advanced_options: new value of advanced_options
        """
        self._advanced_options = advanced_options

    @property
    def acl(self):
        """
        Get acl

        @return acl
        """
        if self._acl is None:
            self._acl = list()
        return self._acl

    @property
    def last_runtime(self):
        """
        get last_runtime

        return last_runtime

        """
        return self._last_runtime

    def set_last_runtime(self, last_runtime):
        """
        Set last_runtime.

        @return: last_runtime
        """
        self._last_runtime = last_runtime

    @property
    def next_run(self):
        """
        get next_run

        return next_run

        """
        return self._next_run

    def set_next_run(self, next_run):
        """
        Set next_run.

        @return: next_run
        """
        self._next_run = next_run

    @property
    def last_run(self):
        """
        get last_run

        return last_run

        """
        return self._last_run

    def set_last_run(self, last_run):
        """
        Set last_run.

        @return: last_run
        """
        self._last_run = last_run

    def set_workflow_name(self, workflow_name):
        """
        Set workflow_name.

        @return: workflow_name
        """
        self._workflow_name = workflow_name

    def set_is_enabled(self, is_enabled):
        """
        Set is_enabled.

        @return: is_enabled
        """
        self._is_enabled = is_enabled

    @property
    def notification(self):
        """
        Get airflow notifications.

        @return  airflow notifications.
        """
        if self._notification is None:
            self._notification = EntityAirflowNotifications()
        return self._notification

    def set_notification(self, notification):
        """
        Set notification.

        @return: notification
        """
        self._notification = notification

    @property
    def schedule_entity(self):
        """
        Get schedule.

        @return schedule
        """
        if self._schedule_entity is None:
            self._schedule_entity = EntitySchedule()
        return self._schedule_entity

    @property
    def schedule(self):
        """
        Get schedule.

        @return: schedule
        """
        return self.schedule_entity.schedule

    def set_schedule(self, schedule):
        """
        Set schedule

        @param schedule: new value of schedule
        """
        self.schedule_entity.set_schedule(schedule)

    @property
    def lower_bound_start_date(self):
        """
        Get lower_bound_start_date.

        @return: lower_bound_start_date
        """
        return self.schedule_entity.lower_bound_start_date

    def set_lower_bound_start_date(self, lower_bound_start_date):
        """
        Set lower_bound_start_date

        @param lower_bound_start_date: new value of lower_bound_start_date
        """
        self.schedule_entity.set_lower_bound_start_date(lower_bound_start_date)

    @property
    def initial_load_start_date(self):
        """
        Get initial_load_start_date.

        @return: initial_load_start_date
        """
        return self.schedule_entity.initial_load_start_date

    def set_initial_load_start_date(self, initial_load_start_date):
        """
        Set initial_load_start_date

        @param initial_load_start_date: new value of initial_load_start_date
        """
        self.schedule_entity.set_initial_load_start_date(initial_load_start_date)

    @property
    def steps(self):
        """
        Get steps.

        @return steps
        """
        if self._steps is None:
            self._steps = []
        return self._steps

    @property
    def _object_full_name(self):
        """
        Create full name of object
        """
        return f"{self.workflow_name}.{ObjectTypesEnum.workflow.value}"

    @staticmethod
    def from_json_dict(workflow_model):
        """
        Create class instance from model/dict/request
        """

        workflow_entity = EntityWorkflow(
            workflow_name=workflow_model.get('workflowName'),
            workflow_version=workflow_model.get('workflowVersion', '1.0.0'),
            display_name=workflow_model['displayName'],
            description=workflow_model.get('description', None),
            framework_version=workflow_model['frameworkVersion'],
            resource_prefix=workflow_model['resourcePrefix'],
            status=workflow_model.get('status', None),
            enable_deffer_operators=convert_to_bool(workflow_model.get('enableDefferOperators', False)),
            schedule=EntitySchedule.from_json_dict(workflow_model.get('scheduling', {})),
            notification=EntityWorkflowNotification.from_json_dict(workflow_model.get('notifications', {})),
            advanced_options=EntityWorkflowAdvancedOptions.from_json_dict(workflow_model.get('advancedOptions', {})),
            dag_id=workflow_model.get("dagId"),
            airflow_link=workflow_model.get("airflowLink"),
            acl=[EntityACL.from_json_dict_object_acl(request_acl)
                 for request_acl in workflow_model.get("acl", [])],
            steps=[],
            is_enabled=convert_to_bool(workflow_model.get("isEnabled", False))
        )
        for step in workflow_model.get('steps', []):
            entity_step = EntityWorkflowStep.from_json_dict(step)
            entity_step.set_linked_workflow(workflow_entity)
            workflow_entity.steps.append(entity_step)

        return workflow_entity

    def to_json_dict(self, limited_view: bool = False):
        """
        return json definition of Entity Workflow

        @return: json object of Entity Workflow
        """
        json_dict = {
            'workflowName': self.workflow_name,
            'workflowVersion': self.workflow_version,
            "displayName": self.display_name,
            "description": self.description,
            "isEnabled": self.is_enabled,
            "frameworkVersion": self.framework_version,
            "resourcePrefix": self.resource_prefix,
            "airflowLink": self.airflow_link,
            "dagId": self.dag_id,
            "status": self.status,
            "enableDefferOperators": self.enable_deffer_operators,
            "scheduling": self.schedule_entity.to_json_dict() if self.schedule_entity else None,
            "notifications": self.notification.to_json_dict() if self.notification else None,
            "runtime": {
                "lastRuntime": self.last_runtime,
                "nextRun": from_datetime_to_str(self.next_run),
                "lastRun": from_datetime_to_str(self.last_run)
            },
            "advancedOptions": self.advanced_options.to_json_dict(),
            "acl": [acl_item.to_json_dict() for acl_item in self.acl],
            "steps": [step.to_json_dict() for step in self.steps]
        }
        if limited_view:
            # Remove the keys that are not needed in a limited view
            keys_to_remove = ["workflowVersion", "frameworkVersion", "resourcePrefix", "airflowLink",
                              "enableDefferOperators", "dagId", "notifications", "advancedOptions",
                              "steps"]
            self.remove_keys(json_dict, keys_to_remove)
        return json_dict

    def to_json_dict_orchestrator_info(self):
        """
        return json definition of orchestrator information

        @return: json object of orchestrator information
        """
        return {
            'workflowName': self.workflow_name,
            "status": self.status,
            "runtime": {
                "lastRuntime": self.last_runtime,
                "nextRun": from_datetime_to_str(self.next_run),
                "lastRun": from_datetime_to_str(self.last_run)
            }
        }

    @property
    def db_workflow_properties_mapping(self):
        """
        List of mapping of DB properties instance attributes and via versa
        """
        return [
            ('resourcePrefix', 'PROPERTY_STRING_VALUE', "resource_prefix"),
            ('schedule', 'PROPERTY_STRING_VALUE', "schedule"),
            ('initialLoadStartDate', 'PROPERTY_STRING_VALUE', "initial_load_start_date",
             from_datetime_to_str, from_str_to_datetime),
            ('lowerBoundStartDate', 'PROPERTY_STRING_VALUE', "lower_bound_start_date",
             from_datetime_to_str, from_str_to_datetime),
            ('airflowLink', 'PROPERTY_STRING_VALUE', "airflow_link"),
            ('dagId', 'PROPERTY_STRING_VALUE', "dag_id"),
            ('enableDefferOperators', 'PROPERTY_BOOL_VALUE', "enable_deffer_operators"),
            ('advancedOptions', 'PROPERTY_LONGTEXT_VALUE', "advanced_options", json.dumps,
             EntityWorkflowAdvancedOptions.from_str_dict),
            ('notification', 'PROPERTY_LONGTEXT_VALUE', "notification", json.dumps,
             EntityWorkflowNotification.from_str_dict)
        ]

    def to_metadb_object(self):
        db_object = Objects(OBJECT_NAME=self.workflow_name, OBJECT_VERSION=self.workflow_version,
                            OBJECT_TYPE=ObjectTypesEnum.workflow, DISPLAY_NAME=self.display_name,
                            DESCRIPTION=self.description,
                            IS_DRAFT=True if self.status and self.status.lower() == 'drafted' else False,
                            IS_LATEST=True, IS_ENABLED=True, DIFW_CORE_VERSION=self.framework_version,
                            OBJECT_FULL_NAME=self._object_full_name)
        # set pipeline acls
        for acl_item in self.acl:
            db_object.rel_objects_acl.append(
                ObjectsACL(OBJECT_FULL_NAME=self._object_full_name, OBJECT_VERSION=self.workflow_version,
                           SUBJECT_ID=acl_item.subject.subject_id, RELATION_TYPE=acl_item.relation_type))

        # set properties
        db_object.rel_object_properties.extend(
            EntityBasePipeline.convert_entity_attributes_to_object_properties(
                self, self.db_workflow_properties_mapping, self._object_full_name, self.workflow_version))

        components_db_object = []
        object_components_pairs = {}
        for step in self.steps:
            # tried setting component details using the relation, but unfortunately it was not working so as
            # had to set component objects separately until we find a route to solve using relations
            component = Components(
                COMPONENT_NAME=step.component_name, DESCRIPTION=step.description,
                DEFINITION=json.dumps(step.definition, indent=4), COMPONENT_TYPE_NAME=step.definition['componentType'],
                COMPONENT_TYPE_CATEGORY=step.definition['componentCategory'],
                DIFW_CORE_VERSION=step.linked_workflow.framework_version,
                PROPERTIES={"crossComponentDependencyOperator": step.cross_component_dependency_operator}
            )
            # assign component id only in case it exists
            if step.component_id:
                component.COMPONENT_ID = step.component_id

            components_db_object.append(component)
            # create a pair of component name and associated ObjectComponents item
            object_components_pairs[step.component_name] = ObjectComponents(
                COMPONENT_ID=step.component_id if step.component_id else None,
                OBJECT_FULL_NAME=self._object_full_name,
                OBJECT_VERSION=self.workflow_version,
                COMPONENT_NAME=step.component_name,
                COMPONENT_COORDINATES=None if not step.component_coordinates else
                json.dumps(step.component_coordinates, indent=4)
            )

        # update object components
        db_object.rel_object_components.extend(object_components_pairs.values())

        # loop again to resolve child components
        for step in self.steps:
            for upstream_dependency in step.dependencies:
                parent_component = object_components_pairs[upstream_dependency.component_name]
                child_component = object_components_pairs[step.component_name]
                child_component.rel_parent_components_hierarchy.append(ObjectComponentsHierarchy(
                    PARENT_OBJECT_FULL_NAME=parent_component.OBJECT_FULL_NAME,
                    PARENT_OBJECT_VERSION=parent_component.OBJECT_VERSION,
                    CHILD_OBJECT_FULL_NAME=child_component.OBJECT_FULL_NAME,
                    CHILD_OBJECT_VERSION=child_component.OBJECT_VERSION,
                    CHILD_COMPONENT_ID=child_component.COMPONENT_ID,
                    PARENT_COMPONENT_ID=parent_component.COMPONENT_ID,
                    PROPERTIES=upstream_dependency.to_json_dict(),
                    intern_child_object_component_reference=child_component,
                    intern_parent_object_component_reference=parent_component
                ))

        return db_object, components_db_object

    @staticmethod
    def from_metadb_object(db_workflow_object: Objects):
        """
        Convert db object to entity object
        """
        if db_workflow_object is None:
            return None

        acl = []
        if db_workflow_object.rel_objects_acl:
            for db_acl in db_workflow_object.rel_objects_acl:
                acl.append(EntityACL.from_metadb_object_objects_acl(db_acl))

        steps = EntityWorkflowStep.from_metadb_objects(db_workflow_object.rel_object_components)
        steps_id_name_mapping = {step.component_id: step.component_name for step in steps}
        # loop all dependence to achieve correct mapping of step name
        for step in steps:
            for dependency in step.dependencies:
                dependency.set_component_name(steps_id_name_mapping.get(dependency.component_id))
        entity_workflow = EntityWorkflow(
            description=db_workflow_object.DESCRIPTION,
            display_name=db_workflow_object.DISPLAY_NAME,
            is_enabled=db_workflow_object.IS_ENABLED,
            framework_version=db_workflow_object.DIFW_CORE_VERSION,
            is_draft=db_workflow_object.IS_DRAFT,
            acl=acl,
            steps=steps,
            workflow_name=db_workflow_object.OBJECT_NAME,
            workflow_version=db_workflow_object.OBJECT_VERSION
        )

        EntityWorkflow.convert_object_properties_to_entity_attributes(
            entity_workflow,
            entity_workflow.db_workflow_properties_mapping,
            db_workflow_object.rel_object_properties
        )
        return entity_workflow

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of entity objects
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntityWorkflow.from_metadb_object(db_object))
        return result

    def clean_step_identifiers(self):
        """
        Method for cleaning step identifier. It should be used as pre-process before creation of whatever object
        containing the steps/components
        """
        for step in self.steps:
            step.set_component_id(None)

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

