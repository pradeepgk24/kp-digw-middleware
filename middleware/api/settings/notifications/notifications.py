import json
from middleware.common.entity_management.notifications_management import NotificationsManagement
from middleware.api.common.http_method_utils import create_error_response
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.helpers import get_env_or_header_value, convert_to_bool
from middleware.common.entity_management.entities.entity_notifications import EntityNotifications


class NotificationsLambda(AWSLambdaEventHandler):
    """
    Lambda class for Notifications API
    """

    def __init__(self, event: DIFWAPIGatewayProxyEvent, context, logger, lambda_secrets_manager):
        super().__init__(event, context, logger, lambda_secrets_manager)
        self.notifications_management = NotificationsManagement(
            logger=self.logger, metadatabase_connection=get_env_or_header_value(
                event=self.event, env_name='METADATA_CONNECTION', header_name='metadata-connection',
                logger=self.logger),
            lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
            selected_subjects=self.selected_subjects)

    # pylint: disable=inconsistent-return-statements
    def _invoke_create_notification(self):
        """
        Invoke method call to create notification.
        """
        self.logger.info("Calling _invoke_create_notification")
        request_body = self.event.json_body
        inserted_record = self.notifications_management.create_notification(
            EntityNotifications.from_json_dict(request_body, self.selected_subjects)
        )
        if inserted_record:
            return {'statusCode': 201, 'body': json.dumps(
                {"result": "created", "notification_id": inserted_record.notification_id,
                 "details": f"Notification with name {inserted_record.notification_name} was created"})}

    # pylint: disable=inconsistent-return-statements
    def _invoke_update_notification(self):
        """
        Invoke method call to update notification.
        """
        self.logger.info("Calling _invoke_update_notification")
        notification_name = self.event.path_parameters.get('notificationId')
        request_body = self.event.json_body
        notification_to_update = EntityNotifications.from_json_dict(request_body, self.selected_subjects)
        notification_to_update.set_notification_id(self.event.path_parameters.get('notificationId'))
        updated_record = self.notifications_management.update_notification(notification_to_update)
        if updated_record:
            return {
                'statusCode': 200,
                'body': json.dumps({"result": "updated",
                                    "details": f"Notification with id {notification_name} is updated"})
            }

    def _invoke_delete_notification(self):
        """
        Invoke method call to delete notification
        """
        self.logger.info("Calling _invoke_delete_notification")
        self.notifications_management.delete_notification(self.event.path_parameters.get('notificationId'))
        return {'statusCode': 200, 'body': json.dumps(
            {"result": "deleted",
             "details": f"Notification with id {self.event.path_parameters.get('notificationId')}"
                        f" was deleted"})}

    def _invoke_get_notification(self):
        """
        Invoke method call to get notification detail
        """
        self.logger.info("Calling _invoke_get_notification")
        notification_name = self.event.path_parameters.get('notificationId')
        response_object = self.notifications_management.get_notification(notification_name)
        return {'statusCode': 200, 'body': json.dumps(response_object.to_json_dict())}

    def _invoke_get_all_notifications(self):
        """
        Invoke method call get all notifications
        """
        self.logger.info("Calling _invoke_get_all_notifications")
        notifications = self.notifications_management.get_all_notifications()
        return {'statusCode': 200, 'body': json.dumps(
                            {"items": [notification.to_json_dict() for notification in notifications]})}

    def _invoke_get_valid_notifications(self):
        """
        Invoke method call get valid notifications for current project and global project - difw_admin_project

        @return: API response
        """
        self.logger.info("Calling _invoke_get_valid_notifications")
        notifications = self.notifications_management.get_valid_notifications()
        # Make a call to Metadata DB to get valid notifications
        return {'statusCode': 200, 'body': json.dumps(
                                    {"items": [notification.to_json_dict() for notification in notifications]})}

    # pylint: disable=inconsistent-return-statements
    def _invoke_enable_or_disable_notification(self):
        """
        Invoke method call to enable or disable notification.
        """
        self.logger.info("Calling _invoke_enable_or_disable_notification")
        notification_id = self.event.path_parameters.get('notificationId')
        enable_or_disable_flag = 'enabled' if convert_to_bool(self.event.json_body['isEnabled']) else 'disabled'
        update_record = self.notifications_management.enable_or_disable_notification(
            notification_id=int(notification_id), enable=convert_to_bool(self.event.json_body['isEnabled']))
        if update_record:
            return {
                'statusCode': 200,
                'body': json.dumps({"result": f" notification {enable_or_disable_flag}",
                                    "details": f"Notification with id {notification_id} was {enable_or_disable_flag}"})
            }

    # pylint: disable=too-many-return-statements
    def invoke(self):
        """
        Lambda function implementation
        @return:
        """
        # ************************************* CREATE NOTIFICATION CALL *****************************************
        if self.event.http_method == 'POST' and self.event.resource.endswith("notifications"):
            return self._invoke_create_notification()
        # **************************************UPDATE NOTIFICATION CALL ******************************************
        if self.event.http_method == 'PUT' and self.event.resource.endswith("notifications/{notificationId}"):
            return self._invoke_update_notification()
        # ************************************* DELETE NOTIFICATION CALL ******************************************
        if self.event.http_method == 'DELETE' and self.event.resource.endswith("notifications/{notificationId}"):
            return self._invoke_delete_notification()
        # **************************************GET NOTIFICATION CALL **********************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith("notifications/{notificationId}"):
            return self._invoke_get_notification()
        # **************************************GET ALL NOTIFICATIONS CALL ******************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith("notifications"):
            return self._invoke_get_all_notifications()
        # **************************************GET VALID NOTIFICATIONS**********************************************
        if self.event.http_method == 'GET' and self.event.resource.endswith("notifications/valid"):
            return self._invoke_get_valid_notifications()
        # **************************************ENABLE/DISABLE NOTIFICATION CALL **************************************
        if self.event.http_method == 'PATCH' and self.event.resource.endswith("notifications/{notificationId}"):
            return self._invoke_enable_or_disable_notification()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct components method was chosen")
