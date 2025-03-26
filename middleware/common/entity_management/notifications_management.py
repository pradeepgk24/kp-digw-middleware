from middleware.common.entity_management.entities.entity_notifications import EntityNotifications
from middleware.common.entity_management.entity_management import EntityManagement
from middleware.common.metadatabase.notifications_metadata_provider import NotificationsMetadataProvider
from middleware.common.helpers.exception import AuthorizationError, NoDataError
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.security.action_type import ActionType


# pylint: disable=too-many-instance-attributes
class NotificationsManagement(EntityManagement):
    """
    Notifications management

    """

    # pylint: disable=too-many-arguments
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._auth_validator = None
        self._auth_management = None
        self._notifications_metadata_provider = None

    @property
    def notifications_metadata_provider(self):
        """
        Notifications metadata provider property
        """
        if self._notifications_metadata_provider is None:
            self._notifications_metadata_provider = NotificationsMetadataProvider(self.logger,
                                                                                  self.metadatabase_connection,
                                                                                  self.lambda_secrets_manager)
        return self._notifications_metadata_provider

    def create_notification(self, notification: EntityNotifications):

        """
        Creates Notification Metadata Database if they do not exist.

        @param notification: notification to create
        @return

        """
        # Validate create notification permission
        self.logger.info(f"Going to validate create notification permission for user {self.user_isid}")
        if self.auth_validator.validate(ActionType.CREATE_NOTIFICATION,
                                        {
                                            "notificationType": SubjectTypesEnum.project.value}) == \
                PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"The user {self.user_isid} does not have create access to notification -"
                f" {notification.notification_name}")
        # insert notification details into Meta DB.
        return EntityNotifications.from_metadb_object(
            self.notifications_metadata_provider.insert_notification(notification.to_metadb_object(),
                                                                     self.user_isid))

    def update_notification(self, notification: EntityNotifications):

        """
        Updates Notification Metadata Database if they do not exist.

        @param notification: notification to update
        @return

        """
        self.logger.info(f"Going to update notification with id {notification.notification_id}")
        # check if the notification to be updated is  existing in MetaDB or not and then
        # raise no data errors accordingly.
        self.get_notification(notification.notification_id)
        # Validate update notification permission
        self.logger.info(f"Going to validate update notification permission for user {self.user_isid}")
        if self.auth_validator.validate(ActionType.UPDATE_NOTIFICATION,
                                        {"notificationType": SubjectTypesEnum.project.value}
                                        ) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"The user {self.user_isid} does not have update access to notification id- "
                f"{notification.notification_id}")
        # update notification details into Meta DB.
        return EntityNotifications.from_metadb_object(
            self.notifications_metadata_provider.update_notification(notification.to_metadb_object(),
                                                                     self.user_isid))

    def delete_notification(self, notification_id):

        """
        Deletes Notification Metadata Database if they do not exist.

        @param notification_id: notification id to be deleted
        @return

        """
        self.logger.info(f"user {self.user_isid} is going to delete notification  - {notification_id}")
        # check if the notification to be deleted exists in Meta DB if not raise No data error
        self.get_notification(notification_id)
        # Validate delete notification permission
        self.logger.info(f"Going to validate delete notification permission for user {self.user_isid}")
        if self.auth_validator.validate(ActionType.DELETE_NOTIFICATION,
                                        {"notificationType": SubjectTypesEnum.project.value}
                                        ) == PermissionEffectsEnum.deny:
            raise AuthorizationError(
                f"The user {self.user_isid} does not have delete access to notification with id - {notification_id}")
        # delete notification from Meta DB.
        return self.notifications_metadata_provider.delete_notification(notification_id=notification_id)

    def get_notification(self, notification_id):
        """
        Gets the notification detail based on the given notification id

        @param notification_id: notification id to be retrieved
        return
        """
        self.logger.info(f"Going to retrieve notification with id {notification_id}")
        notification = EntityNotifications.from_metadb_object(
            self.notifications_metadata_provider.get_notification(notification_id, self.user_isid))
        if notification is None:
            raise NoDataError(f"Notification with id {notification_id} does not exists in db")
        return notification

    def get_all_notifications(self):
        """
        Gets all the notifications that are the defined for the project

        """
        self.logger.info(f"Going to retrieve  all notification for project id - {self.project_id}")
        # get all notifications from DB that are created under a given project.
        notifications_all = EntityNotifications.from_metadb_objects(
            self.notifications_metadata_provider.get_notifications(self.user_isid, self.project_id))
        # if there are no templates then raise no data error
        if not notifications_all:
            raise NoDataError(f"There are no notification defined for project - {self.project_id}")
        result_notifications = []
        for notification in notifications_all:
            result_notifications.append(notification)
        return result_notifications

    def get_valid_notifications(self):
        """
        Get all valid notifications that are defined for project

        """
        self.logger.info(f"Going to retrieve valid notifications for project id - {self.project_id}")
        # get valid notification details from meta DB.
        valid_notifications = EntityNotifications.from_metadb_objects(
            self.notifications_metadata_provider.get_valid_notifications(self.user_isid, self.project_id
                                                                         ))
        result_valid_notifications = []
        for notification in valid_notifications:
            result_valid_notifications.append(notification)
        return result_valid_notifications

    def enable_or_disable_notification(self, notification_id: int, enable=True):

        """
        Enables/Disable Notification in Metadata Database

        @param notification_id: notification id to be enabled or disabled
        @param enable
        @return

        """

        self.logger.info(f"Going to {'enable' if enable else 'disable'} notification with id {notification_id}")
        notification_to_update = self.get_notification(notification_id)
        # update the enable flag sent from request
        notification_to_update.set_is_enabled(enable)
        # update  notification details into Meta DB.
        return self.update_notification(notification_to_update)
