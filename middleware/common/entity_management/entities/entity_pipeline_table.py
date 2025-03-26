# pylint: skip-file
import json

from middleware.common.entity_management.entities.entity_advanced_options import EntityAdvancedOptions
from middleware.common.entity_management.entities.entity_base_pipeline import EntityBasePipeline
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import Objects, ObjectComponents
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum


class EntityPipelineTableStep(EntityObject):
    """
    Entity pipeline table steps
    """

    def __init__(self, component_name: str, overwrite_model_attributes: list,
                 origin_table_name, origin_table_version, component_id: str = None):
        self._component_name = component_name
        self._component_id = component_id
        self._overwrite_model_attributes = overwrite_model_attributes
        self._origin_table_name = origin_table_name
        self._origin_table_version = origin_table_version
        self._overwrite_model_attributes = overwrite_model_attributes

    @property
    def overwrite_model_attributes(self):
        """
        get overwrite_model_attributes

        @return overwrite_model_attributes
        """
        if self._overwrite_model_attributes is None:
            self._overwrite_model_attributes = []
        return self._overwrite_model_attributes

    @property
    def component_name(self):
        """
        get component_name

        @return component_name
        """
        return self._component_name

    @property
    def component_id(self):
        """
        get component_id

        @return component_id
        """
        return self._component_id

    @property
    def origin_table_name(self):
        """
        get origin_table_name

        @return origin_table_name
        """
        return self._origin_table_name

    @property
    def origin_table_version(self):
        """
        get origin_table_version

        @return origin_table_version
        """
        return self._origin_table_version

    @staticmethod
    def from_json_dict(pipeline_table_step_model, origin_table_name, origin_table_version):
        """
        Create class instance from model/dict/request
        """
        if not pipeline_table_step_model:
            return None
        return EntityPipelineTableStep(
            component_name=pipeline_table_step_model["componentName"],
            overwrite_model_attributes=pipeline_table_step_model.get("overwriteModelAttributes", {}),
            origin_table_name=origin_table_name, origin_table_version=origin_table_version
        )

    def to_json_dict(self):
        """
        Return a JSON representation of Entity Pipeline table
        """
        return {
            "componentName": self.component_name,
            "overwriteModelAttributes": self.overwrite_model_attributes
        }

    def to_metadb_object(self) -> ObjectComponents:
        object_component = ObjectComponents(
            OBJECT_FULL_NAME=self.origin_table_name,
            OBJECT_VERSION=self.origin_table_version,
            COMPONENT_NAME=self.component_name,
            OVERWRITE_COMPONENT_DEFINITION=json.dumps(self.overwrite_model_attributes, indent=4)
        )
        if self.component_id:
            object_component.COMPONENT_ID = self.component_id
        return object_component

    @staticmethod
    def from_metadb_object(db_table_step_object: ObjectComponents):
        """
        @param db_table_step_object
        """
        return EntityPipelineTableStep(
            component_name=db_table_step_object.COMPONENT_NAME, component_id=db_table_step_object.COMPONENT_ID,
            overwrite_model_attributes=json.loads(db_table_step_object.OVERWRITE_COMPONENT_DEFINITION),
            origin_table_name=db_table_step_object.OBJECT_FULL_NAME,
            origin_table_version=db_table_step_object.OBJECT_VERSION
        )


class EntityPipelineTable(EntityObject):
    """
    Entity Pipeline table
    """
    _DATA_TYPE_MAPPING = [
        ('table.sourceTableName', 'PROPERTY_STRING_VALUE', 'source_table_name'),
        ('table.targetTableName', 'PROPERTY_STRING_VALUE', 'target_table_name'),
        ('table.loadType', 'PROPERTY_STRING_VALUE', 'load_type'),
        ('table.incrementalCondition', 'PROPERTY_STRING_VALUE', 'incremental_condition'),
        ('table.primaryKeys', 'PROPERTY_STRING_VALUE', 'primary_keys', str, EntityObject._convert_str_to_list),
        ('table.incrementalStrategyNoUpdate', 'PROPERTY_BOOL_VALUE', 'incremental_strategy_no_update'),
        ('table.staticPartitions', 'PROPERTY_STRING_VALUE', 'static_partitions', json.dumps, json.loads),
        ('table.dynamicPartitions', 'PROPERTY_STRING_VALUE', 'dynamic_partitions', str,
         EntityObject._convert_str_to_list),
        ('table.advancedOptions', 'PROPERTY_LONGTEXT_VALUE', "advanced_options", json.dumps,
         EntityAdvancedOptions.from_str_dict),
        ('table.airflowPoolName', 'PROPERTY_STRING_VALUE', 'airflow_pool_name'),
        ('table.airflowPoolSlots', 'PROPERTY_INT_VALUE', 'airflow_pool_slots'),
        ('table.refreshRate', 'PROPERTY_STRING_VALUE', 'refresh_rate'),
        ('table.dependsOn', 'PROPERTY_STRING_VALUE', 'depends_on', str,
         EntityObject._convert_str_to_list)
    ]

    def __init__(self, table_name: str, source_table_name: str = None, target_table_name: str = None,
                 load_type: str = None, incremental_condition: str = None,
                 primary_keys: list = None, incremental_strategy_no_update: bool = None, static_partitions: dict = None,
                 dynamic_partitions: list = None, steps: [EntityPipelineTableStep] = None,
                 advanced_options: EntityAdvancedOptions = None,
                 framework_version: str = None, parent_pipeline=None, airflow_pool_name: str = None,
                 airflow_pool_slots: int = None, refresh_rate: str = None, depends_on: [str] = None):
        self._table_name = table_name
        self._source_table_name = source_table_name
        self._target_table_name = target_table_name
        self._load_type = load_type
        self._incremental_condition = incremental_condition
        self._primary_keys = primary_keys
        self._incremental_strategy_no_update = incremental_strategy_no_update
        self._static_partitions = static_partitions
        self._dynamic_partitions = dynamic_partitions
        self._advanced_options = advanced_options
        self._steps = steps
        self._framework_version = framework_version
        self._parent_pipeline = parent_pipeline
        self._airflow_pool_name = airflow_pool_name
        self._airflow_pool_slots = airflow_pool_slots
        self._refresh_rate = refresh_rate
        self._depends_on = depends_on

    @property
    def refresh_rate(self):
        """
        get refresh_rate

        @return refresh_rate
        """
        return self._refresh_rate

    def set_refresh_rate(self, refresh_rate):
        """
        set new value of refresh_rate

        @param refresh_rate
        """
        self._refresh_rate = refresh_rate

    @property
    def depends_on(self):
        """
        get depends_on

        @return depends_on
        """
        return self._depends_on

    def set_depends_on(self, depends_on):
        """
        set new value of depends_on

        @param depends_on: new value of depends_on
        """
        self._depends_on = depends_on

    @property
    def airflow_pool_name(self):
        """
        get airflow_pool_name

        @return airflow_pool_name
        """
        return self._airflow_pool_name

    def set_airflow_pool_name(self, airflow_pool_name):
        """
        set airflow_pool_name

        @param airflow_pool_name: new value of airflow_pool
        """
        self._airflow_pool_name = airflow_pool_name

    @property
    def airflow_pool_slots(self):
        """
        get airflow_pool

        @return airflow_pool
        """
        return self._airflow_pool_slots

    def set_airflow_pool_slots(self, airflow_pool_slots):
        """
        set airflow_pool

        @param airflow_pool_slots: new value of airflow_pool_slots
        """
        self._airflow_pool_slots = airflow_pool_slots

    @property
    def parent_pipeline(self):
        """
        get parent_pipeline

        @return parent_pipeline
        """
        return self._parent_pipeline

    def set_parent_pipeline(self, parent_pipeline):
        """
        set parent_pipeline

        @param parent_pipeline: new value of parent_pipeline
        """
        self._parent_pipeline = parent_pipeline

    @property
    def table_version(self):
        """
        get table_version

        @return table_version
        """
        return "1.0.0"

    @property
    def framework_version(self):
        """
        get framework_version

        @return framework_version
        """
        return self._framework_version

    @property
    def steps(self) -> [EntityPipelineTableStep]:
        """
        get steps

        @return steps
        """
        if self._steps is None:
            self._steps = []
        return self._steps

    @property
    def advanced_options(self) -> EntityAdvancedOptions:
        """
        get advanced_options

        @return advanced_options
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
    def dynamic_partitions(self):
        """
        get dynamic_partitions

        @return dynamic_partitions
        """
        return self._dynamic_partitions

    def set_dynamic_partitions(self, dynamic_partitions):
        """
        set dynamic_partitions

        @param dynamic_partitions: new value of dynamic_partitions
        """
        self._dynamic_partitions = dynamic_partitions

    @property
    def static_partitions(self):
        """
        get static_partitions

        @return static_partitions
        """
        return self._static_partitions

    def set_static_partitions(self, static_partitions):
        """
        set static_partitions

        @param static_partitions: new value of static_partitions
        """
        self._static_partitions = static_partitions

    @property
    def incremental_strategy_no_update(self):
        """
        get incremental_strategy_no_update

        @return incremental_strategy_no_update
        """
        return self._incremental_strategy_no_update

    def set_incremental_strategy_no_update(self, incremental_strategy_no_update):
        """
        set incremental_strategy_no_update

        @param incremental_strategy_no_update: new value of incremental_strategy_no_update
        """
        self._incremental_strategy_no_update = incremental_strategy_no_update

    @property
    def primary_keys(self):
        """
        get primary_keys

        @return primary_keys
        """
        return self._primary_keys

    def set_primary_keys(self, primary_keys):
        """
        set primary keys

        @param primary_keys: new value of primary_keys
        """
        self._primary_keys = primary_keys

    @property
    def incremental_condition(self):
        """
        get incremental_condition

        @return incremental_condition
        """
        return self._incremental_condition

    def set_incremental_condition(self, incremental_condition):
        """
        set incremental_condition

        @param incremental_condition: new value of incremental_condition
        """
        self._incremental_condition = incremental_condition

    @property
    def load_type(self):
        """
        get load_type

        @return load_type
        """
        return self._load_type

    def set_load_type(self, load_type):
        """
        set load_type

        @param load_type: new value of load_type
        """
        self._load_type = load_type

    @property
    def source_table_name(self):
        """
        get source_table_name

        @return source_table_name
        """
        return self._source_table_name

    def set_source_table_name(self, source_table_name):
        """
        set source_table_name

        @param source_table_name: new value of source_table_name
        """
        self._source_table_name = source_table_name

    @property
    def target_table_name(self):
        """
        get target_table_name

        @return target_table_name
        """
        return self._target_table_name

    def set_target_table_name(self, target_table_name):
        """
        set target_table_name

        @param target_table_name: new value of target_table_name
        """
        self._target_table_name = target_table_name

    @property
    def table_name(self):
        """
        get table_name

        @return table_name
        """
        return self._table_name

    @property
    def _full_name(self):
        """
        Create full name of table
        """
        return f"{self.parent_pipeline.pipeline_name}.{self.table_name}.{ObjectTypesEnum.pipeline_table.value}"

    @staticmethod
    def from_json_dict(pipeline_table_model, parent_pipeline_entity, framework_version):
        """
        Create class instance from model/dict/request

        @param pipeline_table_model:
        @param parent_pipeline_entity
        @param framework_version

        """
        if not pipeline_table_model:
            return None
        entity_pipeline_table = EntityPipelineTable(
            table_name=pipeline_table_model["tableName"],
            source_table_name=pipeline_table_model.get("sourceTableName"),
            target_table_name=pipeline_table_model.get("targetTableName"),
            load_type=pipeline_table_model.get("loadType", "full"),
            incremental_condition=pipeline_table_model.get("incrementalCondition"),
            primary_keys=pipeline_table_model.get("primaryKeys", []),
            incremental_strategy_no_update=pipeline_table_model.get("incrementalStrategyNoUpdate", False),
            static_partitions=pipeline_table_model.get("staticPartitions", {}),
            dynamic_partitions=pipeline_table_model.get("dynamicPartitions", []),
            advanced_options=EntityAdvancedOptions.from_json_dict(pipeline_table_model.get('advancedOptions', {})),
            parent_pipeline=parent_pipeline_entity,
            framework_version=framework_version,
            airflow_pool_name=pipeline_table_model.get("airflowPool", {}).get("poolName"),
            airflow_pool_slots=pipeline_table_model.get("airflowPool", {}).get("poolSlots"),
            refresh_rate=pipeline_table_model.get("refreshRate"),
            depends_on=pipeline_table_model.get("dependsOn"),
        )
        entity_pipeline_table.steps.extend([
            EntityPipelineTableStep.from_json_dict(table_step, entity_pipeline_table._full_name, "1.0.0")
            for table_step in pipeline_table_model.get("steps", [])])
        return entity_pipeline_table

    def to_json_dict(self):
        """
        Return a JSON representation of Entity Pipeline table
        """
        dict_out = {
            "tableName": self.table_name,
            "loadType": self.load_type,
            "incrementalCondition": self.incremental_condition,
            "primaryKeys": self.primary_keys,
            "incrementalStrategyNoUpdate": self.incremental_strategy_no_update,
            "staticPartitions": self.static_partitions,
            "dynamicPartitions": self.dynamic_partitions,
            "advancedOptions": self.advanced_options.to_json_dict() if self.advanced_options else None,
            "steps": [table_step.to_json_dict() for table_step in self.steps],
            "airflowPool": {},
            "refreshRate": self.refresh_rate,
            "dependsOn": self.depends_on
        }
        if self.source_table_name:
            dict_out["sourceTableName"] = self.source_table_name
        if self.target_table_name:
            dict_out["targetTableName"] = self.target_table_name
        if self._airflow_pool_name:
            dict_out["airflowPool"].update({"poolName": self._airflow_pool_name})
        if self._airflow_pool_slots:
            dict_out["airflowPool"].update({"poolSlots": self._airflow_pool_slots})
        return dict_out

    def to_metadb_object(self):
        table_object = Objects(OBJECT_NAME=self.table_name, OBJECT_VERSION=self.table_version,
                               OBJECT_TYPE=ObjectTypesEnum.pipeline_table, DISPLAY_NAME=self.table_name,
                               DESCRIPTION=f"table {self.table_name}",
                               IS_DRAFT=False,
                               IS_LATEST=True,
                               IS_ENABLED=True,
                               DIFW_CORE_VERSION=self.framework_version,
                               OBJECT_FULL_NAME=self._full_name,
                               PARENT_OBJECT_FULL_NAME=self.parent_pipeline.pipeline_name,
                               PARENT_OBJECT_VERSION=self.parent_pipeline.pipeline_version)
        step_object_components = []
        for table_step in self.steps:
            step_object_components.append(table_step.to_metadb_object())
        table_object.rel_object_components = step_object_components
        table_object.rel_object_properties.extend(
            EntityBasePipeline.convert_entity_attributes_to_object_properties(
                self, self._DATA_TYPE_MAPPING, self._full_name, self.table_version))
        return table_object

    @staticmethod
    def from_metadb_object(db_object: Objects):
        """

        @param db_object
        """
        if not db_object:
            return None
        # create entity with basic attributes
        entity_pipeline_table = EntityPipelineTable(
            framework_version=db_object.DIFW_CORE_VERSION,
            steps=[EntityPipelineTableStep.from_metadb_object(table_step) for table_step in
                   db_object.rel_object_components],
            table_name=db_object.OBJECT_NAME)
        # convert object properties to entity properties/attributes
        EntityBasePipeline.convert_object_properties_to_entity_attributes(
            entity_pipeline_table,
            EntityPipelineTable._DATA_TYPE_MAPPING,
            db_object.rel_object_properties
        )
        return entity_pipeline_table

    @staticmethod
    def from_metadb_objects(db_table_objects: [Objects]):
        """
        Convert db_table_objects into list of EntityPipelineTable

        @param db_table_objects: list of db objects
        @return: list of EntityPipelineTable objects
        """
        tables = []
        if db_table_objects:
            for table_component in db_table_objects:
                tables.append(EntityPipelineTable.from_metadb_object(table_component))
        return tables
