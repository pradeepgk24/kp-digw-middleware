from middleware.api.common.helpers import convert_to_bool
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_smtp_recipient import EntitySmtpRecipient


class EntitySmtpService(EntityObject):
    """
    Entity SMTP Service
    """

    def __init__(self, smtp_host: str = None, smtp_port: int = None, service_ssl: bool = None,
                 service_starttls: bool = None, smtp_username_secret_name: str = None,
                 smtp_username_secret_key: str = None, smtp_password_secret_name: str = None,
                 smtp_password_secret_key: str = None, recipients: [EntitySmtpRecipient] = None):
        """
        Initialize the EntitySmtpService instance.

        """
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._service_ssl = service_ssl
        self._service_starttls = service_starttls
        self._smtp_username_secret_name = smtp_username_secret_name
        self._smtp_username_secret_key = smtp_username_secret_key
        self._smtp_password_secret_name = smtp_password_secret_name
        self._smtp_password_secret_key = smtp_password_secret_key
        self._recipients = recipients

    @property
    def smtp_host(self):
        """
        Get the hostname of the SMTP server.

        @return: The SMTP server hostname.
        @rtype: str
        """
        return self._smtp_host

    @property
    def smtp_port(self):
        """
        Get the port number of the SMTP server.

        @return: The SMTP server port number.
        @rtype: str
        """
        return self._smtp_port

    @property
    def service_ssl(self):
        """
        Check whether SSL is used for the SMTP service.

        @return: True if SSL is used, False otherwise.
        @rtype: bool
        """
        return self._service_ssl

    @property
    def service_starttls(self):
        """
        Check whether STARTTLS is used for the SMTP service.

        @return: True if STARTTLS is used, False otherwise.
        @rtype: bool
        """
        return self._service_starttls

    @property
    def smtp_username_secret_name(self):
        """
        Get the smtp_username_secret_name for authenticating with the SMTP server.

        @return: The SMTP server username secret name.
        @rtype: str
        """
        return self._smtp_username_secret_name

    def set_smtp_username_secret_name(self, smtp_username_secret_name):
        """
        Set new value of the smtp_username_secret_name
        @param smtp_username_secret_name: new value
        """
        self._smtp_username_secret_name = smtp_username_secret_name

    @property
    def smtp_username_secret_key(self):
        """
        Get the smtp_username_secret_key for authenticating with the SMTP server.

        @return: The SMTP server username secret key.
        @rtype: str
        """
        return self._smtp_username_secret_key

    def set_smtp_username_secret_key(self, smtp_username_secret_key):
        """
        Set new value of the smtp_username_secret_key
        @param smtp_username_secret_key: new value
        """
        self._smtp_username_secret_key = smtp_username_secret_key

    @property
    def smtp_password_secret_name(self):
        """
        Get the smtp_password_secret_name for authenticating with the SMTP server.

        @return: The SMTP server password secret name.
        @rtype: str
        """
        return self._smtp_password_secret_name

    def set_smtp_password_secret_name(self, smtp_password_secret_name):
        """
        Set new value of the smtp_password_secret_name
        @param smtp_password_secret_name: new value
        """
        self._smtp_password_secret_name = smtp_password_secret_name

    @property
    def smtp_password_secret_key(self):
        """
        Get the smtp_password_secret_key for authenticating with the SMTP server.

        @return: The SMTP server username secret key.
        @rtype: str
        """
        return self._smtp_password_secret_key

    def set_smtp_password_secret_key(self, smtp_password_secret_key):
        """
        Set new value of the smtp_password_secret_key
        @param smtp_password_secret_key: new value
        """
        self._smtp_password_secret_key = smtp_password_secret_key

    @property
    def recipients(self):
        """
        Get the list of email recipients.

        @return: A list of EntitySmtpRecipient objects.
        @rtype: list[EntitySmtpRecipient]
        """
        return self._recipients

    @staticmethod
    def from_json_dict(smtp_service_model):
        """
        Create an instance of EntitySmtpService from a JSON-like dictionary.

        @param smtp_service_model: A dictionary containing the SMTP service model data.
        @return: entity
        @rtype: EntitySmtpService
        """
        if not smtp_service_model:
            return None
        return EntitySmtpService(
            smtp_host=smtp_service_model.get('smtpHost'),
            smtp_port=int(smtp_service_model.get('smtpPort', 25)),
            service_ssl=convert_to_bool(smtp_service_model.get('serviceSSL', False)),
            service_starttls=convert_to_bool(smtp_service_model.get('serviceStartTLS', False)),
            smtp_username_secret_name=smtp_service_model.get('smtpUsername', {}).get("secretName"),
            smtp_username_secret_key=smtp_service_model.get('smtpUsername', {}).get("secretKey"),
            smtp_password_secret_name=smtp_service_model.get('smtpPassword', {}).get("secretName"),
            smtp_password_secret_key=smtp_service_model.get('smtpPassword', {}).get("secretKey"),
            recipients=[EntitySmtpRecipient.from_json_dict(recipient) for recipient in
                        smtp_service_model.get('recipients')]
        )

    def to_json_dict(self):
        """
        Convert the EntitySmtpService instance to a JSON-like dictionary.

        @return: A dictionary representation of the EntitySmtpService instance.
        @rtype: dict
        """
        smtp_service = {
            "smtpHost": self.smtp_host,
            "smtpPort": self.smtp_port,
            "serviceSSL": self.service_ssl,
            "serviceStartTLS": self.service_starttls,
            "recipients": [recipient.to_json_dict() for recipient in self.recipients] if self.recipients else []
        }
        if self.smtp_username_secret_name or self.smtp_password_secret_name:
            smtp_service["smtpUsername"] = {
                "secretName": self.smtp_username_secret_name,
                "secretKey": self.smtp_username_secret_key
            }
            smtp_service["smtpPassword"] = {
                "secretName": self.smtp_password_secret_name,
                "secretKey": self.smtp_password_secret_key
            }
        return smtp_service