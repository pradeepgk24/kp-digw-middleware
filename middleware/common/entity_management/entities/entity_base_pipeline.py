# pylint: skip-file
import json

from middleware.common.entity_management.entities.entity_catalogs import EntityCatalogs
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.helpers.datetime_formater import from_datetime_to_str, from_str_to_datetime
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.metadatabase.model.difw_metadb_model import Objects, \
    ObjectComponents, Components, ObjectComponentsHierarchy
from middleware.common.entity_management.entities.entity_pipeline_steps import EntityPipelineSteps
from middleware.common.entity_management.entities.entity_pipeline_notifications import EntityPipelineNotification
from middleware.common.entity_management.entities.entity_schedule import EntitySchedule
from middleware.common.entity_management.entities.entity_advanced_options import EntityAdvancedOptions


class EntityBasePipeline(EntityObject):
    """
    Entity Base Pipeline.
    """

    def __init__(self, entity_name: str, entity_version: str = None, display_name: str = None, description: str = None,
                 framework_version: str = None, resource_prefix: str = None,
                 platform: str = None, status: str = None, enable_deffer_operators: bool = None,
                 schedule: EntitySchedule = None, notification: EntityPipelineNotification = None,
                 tags: dict = None, advanced_options: EntityAdvancedOptions = None, catalogs: EntityCatalogs = None,
                 acl: list = None, steps: EntityPipelineSteps = None):
        self._entity_name = entity_name
        self._entity_version = entity_version
        self._display_name = display_name
        self._description = description
        self._framework_version = framework_version
        self._resource_prefix = resource_prefix
        self._platform = platform
        self._status = status
        self._enable_deffer_operators = enable_deffer_operators
        self._schedule_entity = schedule
        self._notification = notification
        self._tags = tags
        self._advanced_options = advanced_options
        self._acl = acl
        self._steps = steps
        self._first_input_connector = None
        self._last_output_connector = None
        self._catalogs = catalogs

    @property
    def entity_name(self):
        """
        Get entity_name.

        @return: entity_name
        """
        return self._entity_name

    @property
    def entity_version(self):
        """
        Get entity_version.

        @return: entity_version
        """
        return self._entity_version

    @property
    def resource_prefix(self):
        """
        Get resource_prefix.

        @return: resource_prefix
        """
        return self._resource_prefix

    def set_resource_prefix(self, resource_prefix):
        """
        Set resource_prefix.

        @param resource_prefix: new value of resource_prefix
        """
        self._resource_prefix = resource_prefix

    @property
    def display_name(self):
        """
        Get display_name.

        @return: display_name
        """
        return self._display_name

    @property
    def description(self):
        """
        Get description.

        @return: description
        """
        return self._description

    @property
    def platform(self):
        """
        Get platform.

        @return: platform
        """
        return self._platform

    def set_platform(self, platform):
        """
        Set platform.

        @param platform: new value of platform
        """
        self._platform = platform

    @property
    def tags(self):
        """
        Get tags.

        @return: tags
        """
        return self._tags

    def set_tags(self, tags):
        """
        Set tags

        @param tags: new value of tags
        """
        self._tags = tags

    @property
    def schedule_entity(self):
        """
        Get schedule.

        @return: schedule
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
    def lower_bound_start_date(self):
        """
        Get lower_bound_start_date.

        @return: lower_bound_start_date
        """
        return self.schedule_entity.lower_bound_start_date

    def set_lower_bound_start_date(self, lower_bound_start_date):
        """
        Set lower_bound_start_date

        @param lower_bound_start_date: new value of lowerBoundStartDate
        """
        self.schedule_entity.set_lower_bound_start_date(lower_bound_start_date)

    @property
    def advanced_options(self):
        """
        get advanced_options

        return advanced_options
        """
        if self._advanced_options is None:
            self._advanced_options = EntityAdvancedOptions()
        return self._advanced_options

    def set_advanced_options(self, advanced_options):
        """
        Set advanced_options

        @param advanced_options: new value of advanced_options
        """
        self._advanced_options = advanced_options

    @property
    def framework_version(self):
        """
        Get difw_core_version.

        @return: difw_core_version
        """
        return self._framework_version

    @property
    def steps(self) -> [EntityPipelineSteps]:
        """
        Get steps.

        @return: steps
        """
        if self._steps is None:
            self._steps = []
        return self._steps

    @property
    def acl(self):
        """
        Get acl

        @return: acl
        """
        if self._acl is None:
            self._acl = list()
        return self._acl

    def set_acl(self, acl):
        """
        Set acl

        @param acl: new value of acl
        """
        self._acl = acl

    @property
    def notification(self):
        """
        Get notification.

        @return: notification
        """
        if self._notification is None:
            self._notification = EntityPipelineNotification()
        return self._notification

    def set_notification(self, notification):
        """
        Set notification

        @param notification: new value of notification
        """
        self._notification = notification

    @property
    def status(self):
        """
        try to make it similar to abstract method to json dict
        Get status.

        @return: status
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

        @return: enable_deffer_operators
        """
        return self._enable_deffer_operators

    def set_enable_deffer_operators(self, enable_deffer_operators):
        """
        Set enable_deffer_operators

        @param enable_deffer_operators: new value of enable_deffer_operators
        """
        self._enable_deffer_operators = enable_deffer_operators

    @property
    def first_input_connector(self):
        """
        Get first_input_connector.

        @return: first_input_connector
        """
        return self._first_input_connector

    @property
    def last_output_connector(self):
        """
        Get last_output_connector.

        @return: last_output_connector
        """
        return self._last_output_connector

    def set_first_and_last_connector_info(self, first_input_connector, last_output_connector):
        """
        Set set_first_and_last_connector_info.

        @return: set_first_and_last_connector_info
        """
        self._first_input_connector = first_input_connector
        self._last_output_connector = last_output_connector

    @property
    def db_properties_mapping(self):
        """
        List of mapping of DB properties instance attributes and via versa
        """
        return [
            ('resourcePrefix', 'PROPERTY_STRING_VALUE', "resource_prefix"),
            ('platform', 'PROPERTY_STRING_VALUE', "platform"),
            ('schedule', 'PROPERTY_STRING_VALUE', "schedule"),
            ('tags', 'PROPERTY_LONGTEXT_VALUE', "tags", json.dumps, json.loads),
            ('advancedOptions', 'PROPERTY_LONGTEXT_VALUE', "advanced_options", json.dumps,
             EntityAdvancedOptions.from_str_dict),
            ('catalogs', 'PROPERTY_LONGTEXT_VALUE', 'catalogs', json.dumps, EntityCatalogs.from_str_dict),
            ('enableDefferOperators', 'PROPERTY_BOOL_VALUE', "enable_deffer_operators"),
            ('initialLoadStartDate', 'PROPERTY_STRING_VALUE', "initial_load_start_date",
             from_datetime_to_str, from_str_to_datetime),
            ('lowerBoundStartDate', 'PROPERTY_STRING_VALUE', "lower_bound_start_date",
             from_datetime_to_str, from_str_to_datetime),
            ('notification', 'PROPERTY_LONGTEXT_VALUE', "notification", json.dumps,
             EntityPipelineNotification.from_str_dict),
        ]

    def to_metadb_object(self, is_pipeline_template=False):
        """
        Convert to metadb related objects

        @return:
        """
        object_full_name = f"{self.entity_name}.{ObjectTypesEnum.pipeline_template.value}" \
            if is_pipeline_template else f"{self.entity_name}.{ObjectTypesEnum.pipeline.value}"
        db_object = Objects(OBJECT_NAME=self.entity_name, OBJECT_VERSION=self.entity_version,
                            OBJECT_TYPE=ObjectTypesEnum.pipeline, DISPLAY_NAME=self.display_name,
                            DESCRIPTION=self.description,
                            IS_DRAFT=True if self.status and self.status.lower() == 'drafted' else False,
                            IS_LATEST=True,
                            IS_ENABLED=True, DIFW_CORE_VERSION=self.framework_version,
                            OBJECT_FULL_NAME=object_full_name
                            )

        # set properties
        db_object.rel_object_properties.extend(
            EntityBasePipeline.convert_entity_attributes_to_object_properties(
                self, self.db_properties_mapping, object_full_name, self.entity_version))

        components_db_object = []
        object_components_pairs = {}
        for step in self.steps:
            # tried setting component details using the relation, but unfortunately it was not working so as
            # had to set component objects separately until we find a route to solve using relations
            component = Components(
                COMPONENT_NAME=step.component_name,
                DESCRIPTION=step.description,
                DEFINITION=json.dumps(step.definition, indent=4),
                COMPONENT_TYPE_NAME=step.definition['componentType'],
                COMPONENT_TYPE_CATEGORY=step.definition['componentCategory'],
                DIFW_CORE_VERSION=step.framework_version
            )
            # assign component id only in case it exists
            if step.component_id:
                component.COMPONENT_ID = step.component_id

            components_db_object.append(component)
            # create pair of component name and associated ObjectComponents item
            object_components_pairs[step.component_name] = ObjectComponents(
                COMPONENT_ID=step.component_id if step.component_id else None,
                OBJECT_FULL_NAME=object_full_name,
                OBJECT_VERSION=self.entity_version,
                COMPONENT_NAME=step.component_name,
                COMPONENT_COORDINATES=None if not step.component_coordinates else
                json.dumps(step.component_coordinates, indent=4)
            )

        # update object components
        db_object.rel_object_components.extend(object_components_pairs.values())

        # loop again to resolve child components
        for step in self.steps:
            if step.child_component_name:
                parent_component = object_components_pairs[step.component_name]
                child_component = object_components_pairs[step.child_component_name]
                parent_component.rel_child_components_hierarchy.append(ObjectComponentsHierarchy(
                    CHILD_COMPONENT_ID=child_component.COMPONENT_ID,
                    CHILD_OBJECT_FULL_NAME=child_component.OBJECT_FULL_NAME,
                    CHILD_OBJECT_VERSION=child_component.OBJECT_VERSION,
                    PARENT_COMPONENT_ID=parent_component.COMPONENT_ID,
                    PARENT_OBJECT_FULL_NAME=parent_component.OBJECT_FULL_NAME,
                    PARENT_OBJECT_VERSION=parent_component.OBJECT_VERSION,
                    PROPERTIES={},
                    intern_child_object_component_reference=child_component,
                    intern_parent_object_component_reference=parent_component
                ))

        return db_object, components_db_object

    @staticmethod
    def from_metadb_object(db_object: Objects):
        """
        Convert db object to entity object
        """

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of entity objects
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntityBasePipeline.from_metadb_object(db_object))
        return result

    def clean_step_identifiers(self):
        """
        Method for cleaning step identifier. It should be used as pre-process before creation of whatever object
        containing the steps/components
        """
        for step in self.steps:
            step.set_component_id(None)

    @property
    def catalogs(self):
        """
        get catalogs

        return catalogs
        """
        if self._catalogs is None:
            self._catalogs = EntityCatalogs()
        return self._catalogs

    def set_catalogs(self, catalogs):
        """
        set catalogs

        @param catalogs: new value of catalogs
        """
        self._catalogs = catalogs
