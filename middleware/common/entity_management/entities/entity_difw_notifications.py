from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_smtp_service import EntitySmtpService
from middleware.common.entity_management.entities.entity_sns import EntitySns


class EntityDifwNotifications(EntityObject):
    """
    Entity DIFW  Notifications
    """

    def __init__(self, identifier: str = None, smtp_service: EntitySmtpService = None, sns_service: [EntitySns] = None):
        """
        Initialize the EntityDifwNotifications instance.

        """
        self._identifier = identifier
        self._smtp_service = smtp_service
        self._sns_service = sns_service

    @property
    def identifier(self):
        """
        Get the unique identifier for the notification.

        @return: The unique identifier.
        @rtype: str
        """
        return self._identifier

    @property
    def smtp_service(self):
        """
        Get the SMTP service configuration.

        @return: The SMTP service configuration.
        @rtype: EntitySmtpService
        """
        return self._smtp_service

    @property
    def sns_service(self):
        """
        Get the list of SNS service configurations.

        @return: The list of SNS service configurations.
        @rtype: list of EntitySns
        """
        return self._sns_service

    @staticmethod
    def from_json_dict(notification_model):
        """
        Create an instance of EntityDifwNotification from a JSON-like dictionary.

        @param notification_model: A dictionary containing the notification model data.
        @return: An instance of EntityDifwNotification initialized with the provided data.
        @rtype: EntityDifwNotifications
        """
        if not notification_model:
            return None
        return EntityDifwNotifications(
            identifier=notification_model.get('identifier'),
            smtp_service=EntitySmtpService.from_json_dict(notification_model.get('smtpService', {})),
            sns_service=[
                EntitySns.from_json_dict(recipient) for recipient in
                notification_model.get('snsService', {}).get('recipients', [])
            ] if 'snsService' in notification_model else None
        )

    def to_json_dict(self):
        """
        Convert the EntityDifwNotifications instance to a JSON-like dictionary.

        @return: A dictionary representation of the EntityDifwNotifications instance.
        @rtype: dict
        """
        notifications = {
            "identifier": self.identifier
        }
        if self.smtp_service:
            notifications.update({"smtpService": self.smtp_service.to_json_dict()})
        if self.sns_service:
            notifications.update({"snsService": {"recipients": [sns_recipient.to_json_dict()
                                                                for sns_recipient in self.sns_service]}})
        return notifications
