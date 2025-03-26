from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_workflow import EntityWorkflow


class WorkflowAirflowConfigResolver(ConfigPartResolver):
    """
    Resolve airflow related configuration
    """

    def resolve_model_to_config(self, entity_workflow: EntityWorkflow, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.
        For more see ConfigPartResolver.resolve_model_to_config
        """
        config_part = {}
        self.map_object_attr_to_dict_bulk(
            entity_workflow,
            config_part,
            [
                (["advanced_options", "entity_airflow_options", "dag_instance_parameters"],
                 ["dag_instance_parameters"]),
                (["advanced_options", "entity_airflow_options", "dag_concurrency"], ["dag_concurrency"])
            ]
        )
        config_airflow_pools = []
        for pool in entity_workflow.advanced_options.entity_airflow_options.airflow_pools:
            config_acl = {
                "name": pool.name,
                "slots": pool.slots
            }
            if pool.default is not None:
                config_acl["default"] = pool.default
            config_airflow_pools.append(config_acl)
        if config_airflow_pools:
            config_part["airflow_pools"] = config_airflow_pools
        return None, config_part
