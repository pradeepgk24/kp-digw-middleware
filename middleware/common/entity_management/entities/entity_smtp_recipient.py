from middleware.api.common.helpers import SortAndPaginate
from middleware.common.entity_management.entities.entity_object import EntityObject


class EntitySmtpRecipient(EntityObject):
    """
    Entity SMTP Recipients

    """

    def __init__(self, event_type: str = None, identifier: str = None,
                 email_from: str = None, email_to: list = None, email_cc: list = None,
                 email_bcc: list = None, charset: str = None, subject: str = None,
                 email_html_content: str = None):

        self._event_type = event_type
        self._identifier = identifier
        self._email_from = email_from
        self._email_to = email_to
        self._email_cc = email_cc
        self._email_bcc = email_bcc
        self._charset = charset
        self._subject = subject
        self._email_html_content = email_html_content

    @property
    def event_type(self):
        """
        Get the type of event that triggers the email notification.

        @return: The type of event.
        @rtype: str
        """
        return self._event_type

    @property
    def identifier(self):
        """
        Get the unique identifier for the recipient configuration.

        @return: The unique identifier.
        @rtype: str
        """
        return self._identifier

    @property
    def email_from(self):
        """
        Get the sender's email address.

        @return: The sender's email address.
        @rtype: str
        """
        return self._email_from

    @property
    def email_to(self):
        """
        Get the list of recipient addresses

        @return: list of recipient addresses
        @rtype: list
        """
        return self._email_to

    @property
    def email_cc(self):
        """
        Get the cc list of recipient addresses

        @return: cc list of recipient addresses
        @rtype: list
        """
        return self._email_cc

    @property
    def email_bcc(self):
        """
        Get the bcc list of recipient addresses

        @return: bcc list of recipient addresses
        @rtype: list
        """
        return self._email_bcc

    @property
    def charset(self):
        """
        Get the character set used for the email content.

        @return: The character set.
        @rtype: str
        """
        return self._charset

    @property
    def subject(self):
        """
        Get the subject line of the email.

        @return: The subject line.
        @rtype: str
        """
        return self._subject

    @property
    def email_html_content(self):
        """
        Get the HTML content of the email.

        @return: The HTML content.
        @rtype: str
        """
        return self._email_html_content

    @staticmethod
    def from_json_dict(recipient_model):
        """
        Create an instance of EntitySmtpRecipient from a JSON-like dictionary.

        @rtype: EntitySmtpRecipient
        """
        if not recipient_model:
            return None
        # reparse email addresses if they are passed as strings
        email_to = recipient_model.get('emailTo', None)
        if not isinstance(email_to, list):
            email_to = SortAndPaginate.clean_and_relist_listed_strings(email_to)
        email_cc = recipient_model.get('emailCc', None)
        if not isinstance(email_cc, list):
            email_cc = SortAndPaginate.clean_and_relist_listed_strings(email_cc)
        email_bcc = recipient_model.get('emailBcc', None)
        if not isinstance(email_bcc, list):
            email_bcc = SortAndPaginate.clean_and_relist_listed_strings(email_bcc)
        return EntitySmtpRecipient(
            event_type=recipient_model.get('eventType'),
            identifier=recipient_model.get("identifier"),
            email_from=recipient_model.get('emailFrom', "difw@merck.com"),
            email_to=email_to,
            email_cc=email_cc,
            email_bcc=email_bcc,
            charset=recipient_model.get('charset'),
            subject=recipient_model.get('subject'),
            email_html_content=recipient_model.get('emailHtmlContent')
        )

    def to_json_dict(self):
        """
        Convert the EntitySmtpRecipient instance to a JSON-like dictionary.

        @return: A dictionary representation of the EntitySmtpRecipient instance.
        @rtype: dict
        """
        return {
            "eventType": self.event_type,
            "identifier": self.identifier,
            "emailFrom": self.email_from,
            "emailTo": self.email_to,
            "emailCc": self.email_cc,
            "emailBcc": self.email_bcc,
            "charset": self.charset,
            "subject": self.subject,
            "emailHtmlContent": self.email_html_content
        }

