import json

from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_difw_notifications import EntityDifwNotifications
from middleware.common.entity_management.entities.entity_airflow_notifications import EntityAirflowNotifications


class EntityPipelineNotification(EntityObject):
    """
    Entity Pipeline Notifications, this entity is used in EntityPipeline and EntityPipelineTemplate
    """

    def __init__(self, entity_airflow_notifications: EntityAirflowNotifications = None,
                 entity_difw_notifications: [EntityDifwNotifications] = None):
        self._entity_airflow_notifications = entity_airflow_notifications
        self._entity_difw_notifications = entity_difw_notifications

    @property
    def entity_airflow_notifications(self) -> EntityAirflowNotifications:
        """
        Get airflow_notifications detail

        @return airflow_notifications details
        """
        if self._entity_airflow_notifications is None:
            self._entity_airflow_notifications = EntityAirflowNotifications()
        return self._entity_airflow_notifications

    def set_entity_airflow_notifications(self, entity_airflow_notifications: EntityAirflowNotifications):
        """
        Set entity_airflow_notifications

        @param entity_airflow_notifications: new value of entity_airflow_notifications
        """
        self._entity_airflow_notifications = entity_airflow_notifications

    @property
    def entity_difw_notifications(self) -> list:
        """
        Get difw notifications detail

        @return list of difw notifications details
        """
        if self._entity_difw_notifications is None:
            self._entity_difw_notifications = []
        return self._entity_difw_notifications

    def set_difw_notifications(self, difw_notifications: list):
        """
        Set difw_notifications

        @param difw_notifications: new value of difw_notifications (list of EntityDifwNotifications)
        """
        self._entity_difw_notifications = difw_notifications

    def to_json_dict(self):
        """
        Return a JSON representation of Entity pipeline notifications
        """
        notifications_out = {}
        # if to prevent of printing empty airflow notifications
        if self.entity_airflow_notifications and self.entity_airflow_notifications.to_json_dict():
            notifications_out["airflowNotification"] = \
                self.entity_airflow_notifications.to_json_dict() if self.entity_airflow_notifications else {}
        if self.entity_difw_notifications:
            notifications_out["difwNotifications"] = \
                {"notifications": [notification.to_json_dict() for notification in
                                   self.entity_difw_notifications] if self.entity_difw_notifications else []}
        return notifications_out

    @staticmethod
    def from_json_dict(notifications: dict):
        """
        Return instance of EntityPipelineNotification created from json dict

        @param notifications: dict representation of notifications
        """
        return EntityPipelineNotification(
            entity_airflow_notifications=EntityAirflowNotifications.from_json_dict(
                notifications.get("airflowNotification")),
            entity_difw_notifications=[
                EntityDifwNotifications.from_json_dict(notification)
                for notification in notifications.get("difwNotifications", {}).get("notifications", [])
            ]
        )

    @staticmethod
    def from_str_dict(notification: str):
        """
        Return instance of EntityPipelineNotification created from str rep of json

        :param notification: str representation of notification
        """
        return EntityPipelineNotification.from_json_dict(json.loads(notification))

