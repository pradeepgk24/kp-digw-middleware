import datetime
from sqlalchemy import and_, or_
from middleware.common.metadatabase.clients.meta_database_client import MetaDatabaseClient
from middleware.common.metadatabase.model.difw_metadb_model import Notifications


class NotificationsMetadataProvider(MetaDatabaseClient):
    """
    Database client which served actions related with notifications
    """

    def insert_notification(self, notification: Notifications, user_id: str):
        """
        creates a notification in MetaDB for the given project

        @param notification
        @param user_id
        """
        self.logger.info(f"User {user_id} is going to create notification name {notification.NOTIFICATION_NAME} ")
        return self.insert_record(notification, user_id)

    def update_notification(self, notification: Notifications, user_id: str):
        """
        updates notification in MetaDB for the given project

        @param notification
        @param user_id
        """
        self.logger.info(f"User {user_id} is going to retrieve notification with id {notification.NOTIFICATION_ID} ")
        return self.update_record(notification, user_id)

    def delete_notification(self, notification_id: int):
        """
        delete notification in MetaDB.

        @param notification_id
        """
        self.logger.info(f"Going to delete notification with id {notification_id} ")
        return Notifications(NOTIFICATION_ID=notification_id).delete(self.session)

    def get_notification(self, notification_id: int, user_id: str):
        """
        get notification in MetaDB for the given project

        @param notification_id
        @param user_id
        """
        self.logger.info(f"User {user_id} is going to retrieve notification with id {notification_id} ")
        return Notifications(NOTIFICATION_ID=notification_id).get_unique(self.session)

    def get_notifications(self, user_id: str, project_id: str):
        """
        get notification in MetaDB for the given project

        @param user_id
        @param project_id
        """
        self.logger.info(f"User {user_id} going to get all notifications  where project_id is {project_id}")
        return Notifications.get_many(self.session, and_(Notifications.PROJECT_ID == project_id))

    # pylint: disable=too-many-function-args
    def get_valid_notifications(self, user_id: str, project_ids=None):
        """
        Gets all valid notifications details from Metadata DB.

        @param project_ids:
        @param user_id: logon user isid
        @return:
        """
        self.logger.info(f"User {user_id} going to get all notification details where project_id in {project_ids}")
        current_epoch_time = datetime.datetime.now()
        # TODO https://issues.merck.com/browse/NGA-4417 get rid of hardcode in refactor
        # pylint: disable=singleton-comparison
        # if VALID TO is not configured from user then the notification will be
        # displayed forever until the user wants to disable the notifications,
        # and other notification will work to run normal as currently there now ,
        # they would display based on time range between VALID FROM and VALID TO
        # fields.
        return Notifications.get_many(self.session,
                                      filter_condition=and_(
                                          or_(
                                              Notifications.VALID_FROM <= current_epoch_time,
                                              Notifications.VALID_FROM.is_(None)
                                          ),
                                          or_(
                                              Notifications.VALID_TO >= current_epoch_time,
                                              Notifications.VALID_TO.is_(None)
                                          ),
                                          Notifications.IS_ENABLED == True,
                                          Notifications.PROJECT_ID.in_((project_ids, "difw_admin_project"))
                                      )
                                      )
