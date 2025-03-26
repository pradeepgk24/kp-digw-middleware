import json


from middleware.common.entity_management.entities.entity_airflow_notification import EntityAirflowNotification
from middleware.common.entity_management.entities.entity_object import EntityObject


class EntityAirflowNotifications(EntityObject):
    """
    Entity Airflow Notifications which consist of two separate notification
    """

    def __init__(self, on_success: EntityAirflowNotification = None, on_failure: EntityAirflowNotification = None):
        self._on_success = on_success
        self._on_failure = on_failure

    @property
    def on_success(self):
        """
        get on_success notification detail

        @return on_success notification
        """
        return self._on_success

    def set_on_success(self, on_success):
        """
        Set on_success

        @param on_success: new value of on_success
        """
        self._on_success = on_success

    @property
    def on_failure(self):
        """
        get on_failure notification detail

        @return on_failure notification
        """
        return self._on_failure

    def set_on_failure(self, on_failure):
        """
        Set on_failure

        @param on_failure: new value of on_failure
        """
        self._on_failure = on_failure

    @staticmethod
    def from_json_dict(airflow_notifications_model):
        """
        Create class instance from model/dict/request
        """
        if not airflow_notifications_model:
            return None
        return EntityAirflowNotifications(
            on_success=EntityAirflowNotification.from_json_dict(airflow_notifications_model.get('onSuccess')),
            on_failure=EntityAirflowNotification.from_json_dict(airflow_notifications_model.get('onFailure'))
        )

    def to_json_dict(self):
        """
        Return a JSON representation of EntityWorkflowNotifications
        """
        airflow_notifications_out = {}
        if self.on_success:
            airflow_notifications_out["onSuccess"] = self.on_success.to_json_dict()
        if self.on_failure:
            airflow_notifications_out["onFailure"] = self.on_failure.to_json_dict()
        return airflow_notifications_out

