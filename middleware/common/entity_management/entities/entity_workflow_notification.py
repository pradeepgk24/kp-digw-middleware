import json

from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_airflow_notifications import EntityAirflowNotifications


class EntityWorkflowNotification(EntityObject):
    """
    Entity Workflow Notification, this entity is used in EntityWorkflow
    """

    def __init__(self, entity_airflow_notifications: EntityAirflowNotifications = None):
        self._entity_airflow_notifications = entity_airflow_notifications

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

    def to_json_dict(self):
        """
        Return a JSON representation of Entity Workflow notification
        """
        notifications_out = {}
        # if to prevent of printing empty airflow notifications
        if self.entity_airflow_notifications and self.entity_airflow_notifications.to_json_dict():
            notifications_out["airflowNotification"] = \
                self.entity_airflow_notifications.to_json_dict() if self.entity_airflow_notifications else {}
        return notifications_out

    @staticmethod
    def from_json_dict(notifications: dict):
        """
        Return instance of EntityWorkflowNotification created from json dict

        @param notifications: dict representation of notifications
        """
        return EntityWorkflowNotification(
            entity_airflow_notifications=EntityAirflowNotifications.from_json_dict(
                notifications.get("airflowNotification", {}))
        )

    @staticmethod
    def from_str_dict(notification: str):
        """
        Return instance of EntityWorkflowNotification created from str rep of json

        @param notification: str representation of notification
        """
        return EntityWorkflowNotification.from_json_dict(json.loads(notification))
