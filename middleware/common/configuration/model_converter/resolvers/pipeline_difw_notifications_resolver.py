from common.secrets.secrets import SecretValue
from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_pipeline import EntityPipeline


class PipelineDifwNotificationsResolver(ConfigPartResolver):
    """
    Resolve DIFW notifications related configuration
    """

    def resolve_model_to_config(self, entity_pipeline: EntityPipeline, **kwargs) -> (str, dict):
        """
        Main implementation of model to configuration converter.

        @param entity_pipeline
        @param kwargs
        """
        config_part = {"notification_system": {"services": {}, "message_types": {}}}
        events_notifications_for_context = {}
        services, message_types, events_notifications = {}, {}, {}
        for entity_difw_notification in entity_pipeline.notification.entity_difw_notifications:
            if entity_difw_notification.smtp_service:
                services, message_types, events_notifications = self._resolve_smtp_service_config(
                    entity_difw_notification)
            elif entity_difw_notification.sns_service:
                services, message_types, events_notifications = self._resolve_sns_service_config(
                    entity_difw_notification)
            config_part["notification_system"]["services"].update(services)
            config_part["notification_system"]["message_types"].update(message_types)
            events_notifications_for_context.update(events_notifications)
        events_notifications = {"event_notifications": events_notifications_for_context}
        if events_notifications:
            self.converter.add_context_property("event_notifications", events_notifications)
        # if there are no services, we will return only empty dictionary
        if not config_part["notification_system"]["services"]:
            config_part = {}
        return None, config_part

    def _resolve_smtp_service_config(self, entity_difw_notification):
        """
        resolve  SMTP service configurations.

        @param entity_difw_notification
        """
        smtp_config = {}

        # notification identifier
        identifier = entity_difw_notification.identifier

        config_part_service = {}
        self.map_object_attr_to_dict_bulk(
            entity_difw_notification,
            config_part_service,
            [
                (["smtp_service", "smtp_host"],
                 [identifier, "options", "smtp_host"]),
                (["smtp_service", "smtp_port"],
                 [identifier, "options", "smtp_port"]),
                (["smtp_service", "service_ssl"],
                 [identifier, "options", "smtp_ssl"]),
                (["smtp_service", "service_starttls"],
                 [identifier, "options", "smtp_starttls"]),
            ]
        )
        config_part_service[identifier]["module"] = "email_service"
        if entity_difw_notification.smtp_service.smtp_username_secret_name:
            config_part_service[identifier]["options"]["smtp_user"] = SecretValue(
                self._resolve_secret_manager_name({
                    "secretName": entity_difw_notification.smtp_service.smtp_username_secret_name}),
                entity_difw_notification.smtp_service.smtp_username_secret_key)
            config_part_service[identifier]["options"]["smtp_password"] = SecretValue(
                self._resolve_secret_manager_name({
                    "secretName": entity_difw_notification.smtp_service.smtp_username_secret_name}),
                entity_difw_notification.smtp_service.smtp_password_secret_key)

        config_recipients = {}
        events_notifications = {}
        for recipient in entity_difw_notification.smtp_service.recipients:
            config_part = {}
            self.map_object_attr_to_dict_bulk(
                recipient,
                config_part,
                [
                    (["email_from"], ["default_parameters", "from"]),
                    (["email_to"], ["default_parameters", "to"]),
                    (["email_cc"], ["default_parameters", "cc"]),
                    (["email_bcc"], ["default_parameters", "bcc"]),
                    (["charset"], ["default_parameters", "mime_charset"]),
                    (["subject"], ["default_parameters", "subject"]),
                    (["email_html_content"], ["default_parameters", "html_content"]),
                ]
            )
            # add mapping to the service identifier
            config_part["service"] = identifier
            config_recipients[recipient.identifier] = config_part

            events_notifications[recipient.event_type] = {
                recipient.identifier: {"message_type": recipient.identifier}}
        if config_part_service:
            smtp_config["services"] = config_part_service
        if config_recipients:
            smtp_config["message_types"] = config_recipients
        return config_part_service, config_recipients, events_notifications

    def _resolve_sns_service_config(self, entity_difw_notification):
        """
        Process SNS service configurations.
        @param entity_difw_notification
        """
        sns_config = {"services": {
            entity_difw_notification.identifier: {"module": "sns_service"}
        }}
        config_part_event_types = {}
        events_notifications = {}
        # part for message_types
        for recipient in entity_difw_notification.sns_service:
            # add mapping back onto the notification identifier
            config_part = {"service": entity_difw_notification.identifier}
            self.map_object_attr_to_dict_bulk(
                recipient,
                config_part,
                [
                    (["topic_arn"], ["default_parameters", "topicArn"]),
                    (["target_arn"], ["default_parameters", "targetArn"]),
                    (["phone_number"], ["default_parameters", "phoneNumber"]),
                    (["html_message"], ["default_parameters", "message"])
                ]
            )
            if recipient.other_sns_options:
                config_part["default_parameters"]["other_sns_options"] = \
                    {option["optionKey"]: option["optionValue"] for option in recipient.other_sns_options}
            config_part_event_types[recipient.identifier] = config_part
            events_notifications[recipient.event_type] = {recipient.identifier: {"message_type": recipient.identifier}}

        if config_part_event_types:
            sns_config["message_types"] = config_part_event_types
        return sns_config["services"], sns_config["message_types"], events_notifications