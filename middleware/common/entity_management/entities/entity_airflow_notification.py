from middleware.api.common.helpers import convert_to_bool, SortAndPaginate
from middleware.common.entity_management.entities.entity_object import EntityObject


class EntityAirflowNotification(EntityObject):
    """
    Entity Airflow Notification
    """

    def __init__(self, enabled: bool = None, email_recipients: list = None,
                 email_subject: str = None,
                 email_content: str = None):
        self._enabled = enabled
        self._email_recipients = email_recipients
        self._email_subject = email_subject
        self._email_content = email_content

    @property
    def enabled(self):
        """
        get enabled flag

        @return enabled
        """
        return self._enabled

    def set_enabled(self, enabled):
        """
        Set enabled

        @param enabled: new value of enabled
        """
        self._enabled = enabled

    @property
    def email_recipients(self):
        """
        get email_recipient

        @return email_recipient email
        """
        if not self._email_recipients:
            return []

        return self._email_recipients

    def set_email_recipients(self, email_recipients):
        """
        Set email_recipients

        @param email_recipients: New value of email_recipients
        """
        self._email_recipients = email_recipients

    @property
    def email_subject(self):
        """
        get email_subject

        @return email_subject
        """
        return self._email_subject

    def set_email_subject(self, email_subject):
        """
        Set email_subject

        @param email_subject: new value email_subject
        @return: new value email_subject
        """
        self._email_subject = email_subject

    @property
    def email_content(self):
        """
        get email_content

        @return on failure email
        """
        return self._email_content

    def set_email_content(self, email_content):
        """
        Set email_content

        @param email_content: new value of email_content
        """
        self._email_content = email_content

    @staticmethod
    def from_json_dict(airflow_notification_model):
        """
        Create class instance from model/dict/request
        """
        if not airflow_notification_model:
            return None
        # parse recipients in both cases - if passed in as list or string
        recipients = airflow_notification_model.get('emailRecipients', None)
        if not isinstance(recipients, list):
            recipients = SortAndPaginate.clean_and_relist_listed_strings(recipients)
        return EntityAirflowNotification(
            enabled=convert_to_bool(airflow_notification_model.get('enabled', False)),
            email_recipients=recipients,
            email_subject=airflow_notification_model.get('emailSubject'),
            email_content=airflow_notification_model.get("emailContentHtml")
        )

    def to_json_dict(self):
        """
        Return a JSON representation of EntityAirflowNotification
        """
        return {
                   "enabled": self.enabled,
                   "emailRecipients": self.email_recipients,
                   "emailSubject": self.email_subject,
                   "emailContentHtml": self.email_content
               }