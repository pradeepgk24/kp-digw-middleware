from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline
from middleware.common.entity_management.entities.entity_pipeline_template import EntityPipelineTemplate


class ObjectAirflowNotificationsResolver(ConfigPartResolver):
    """
    Resolve airflow notifications related configuration
    """

    def resolve_model_to_config(self, entity_object, **kwargs) -> (str, dict):
        """
        Resolve object airflow notifications

        @param entity_object can be EntityPipeline, EntityPipelineTemplate or EntityWorkflow
        @parm kwargs
        """
        config_part = {}
        airflow_notifications = entity_object.notification.entity_airflow_notifications
        if not airflow_notifications:
            return None, config_part

        # first handle on success, if it is enabled
        if airflow_notifications.on_success and airflow_notifications.on_success.enabled:
            self.map_object_attr_to_dict_bulk(
                airflow_notifications.on_success,
                config_part,
                [
                    (["email_recipients"],
                     ["airflow_event_handlers", "on_task_success", "email_message", "to"]),
                    (["email_subject"],
                     ["airflow_event_handlers", "on_task_success", "email_message", "subject"]),
                    (["email_content"],
                     ["airflow_event_handlers", "on_task_success", "email_message", "html_content"])
                ]
            )
            # add value all_tables True, so the notification will be for all tables
            config_part["airflow_event_handlers"]["on_task_success"]["all_tables"] = True
        # second handle on failure, if its enabled
        if airflow_notifications.on_failure and airflow_notifications.on_failure.enabled:
            self.map_object_attr_to_dict_bulk(
                airflow_notifications.on_failure,
                config_part,
                [
                    (["email_recipients"],
                     ["airflow_event_handlers", "on_task_failure", "email_message", "to"]),
                    (["email_subject"],
                     ["airflow_event_handlers", "on_task_failure", "email_message", "subject"]),
                    (["email_content"],
                     ["airflow_event_handlers", "on_task_failure", "email_message", "html_content"])
                ]
            )
            # add value all_tables True, so the notification will be for all tables
            config_part["airflow_event_handlers"]["on_task_failure"]["all_tables"] = True
        # will be place into global configuration
        return None, config_part
