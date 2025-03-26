from middleware.common.entity_management.entities.entity_object import EntityObject


class EntitySns(EntityObject):
    """
    Entity SNS
    """

    def __init__(self, event_type: str = None, identifier: str = None,
                 topic_arn: str = None, target_arn: str = None, phone_number: str = None,
                 html_message: str = None, other_sns_options: list = None):
        """
        Initialize the EntitySns instance.
        """
        self._event_type = event_type
        self._identifier = identifier
        self._topic_arn = topic_arn
        self._target_arn = target_arn
        self._phone_number = phone_number
        self._html_message = html_message
        self._other_sns_options = other_sns_options if other_sns_options else []

    @property
    def event_type(self):
        """
        Get the type of the event that triggers the SNS notification.

        @return: The event type.
        @rtype: str
        """
        return self._event_type

    @property
    def identifier(self):
        """
        Get the unique identifier for the SNS notification.

        @return: The SNS notification identifier.
        @rtype: str
        """
        return self._identifier

    @property
    def topic_arn(self):
        """
        Get the ARN of the SNS topic.

        @return: The SNS topic ARN.
        @rtype: str
        """
        return self._topic_arn

    @property
    def target_arn(self):
        """
        Get the ARN of the target that receives the SNS notification.

        @return: The target ARN.
        @rtype: str
        """
        return self._target_arn

    @property
    def phone_number(self):
        """
        Get the phone number to which SNS notifications are sent.

        @return: The phone number.
        @rtype: str
        """
        return self._phone_number

    @property
    def html_message(self):
        """
        Get the HTML message content for SNS notifications.

        @return: The HTML message content.
        @rtype: str
        """
        return self._html_message

    @property
    def other_sns_options(self):
        """
        Get the list of additional SQS options.

        @return: A list of dictionaries representing additional SQS options.
        @rtype: list
        """
        return self._other_sns_options

    @staticmethod
    def from_json_dict(sns_recipient_model):
        """
        Create an instance of EntitySns from a JSON-like dictionary.

        @param sns_recipient_model: A dictionary containing the SNS recipient model data.
        @return: An instance of EntitySns initialized with the provided data.
        @rtype: EntitySns
        """
        if not sns_recipient_model:
            return None
        return EntitySns(
            event_type=sns_recipient_model.get('eventType'),
            identifier=sns_recipient_model.get('identifier'),
            topic_arn=sns_recipient_model.get('topicArn'),
            target_arn=sns_recipient_model.get('targetArn'),
            phone_number=sns_recipient_model.get('phoneNumber'),
            html_message=sns_recipient_model.get('htmlMessage'),
            other_sns_options=[
                {"optionKey": option['optionKey'], "optionValue": option['optionValue']}
                for option in sns_recipient_model.get('otherSnsOptions', [])
            ]
        )

    def to_json_dict(self):
        """
        Convert the EntitySns instance to a JSON-like dictionary.

        @return: A dictionary representation of the EntitySns instance.
        @rtype: dict
        """
        return {
            "eventType": self.event_type,
            "identifier": self.identifier,
            "topicArn": self.topic_arn,
            "targetArn": self.target_arn,
            "phoneNumber": self.phone_number,
            "htmlMessage": self.html_message,
            "otherSnsOptions": [
                {"optionKey": option['optionKey'], "optionValue": option['optionValue']}
                for option in self.other_sns_options
            ] if self.other_sns_options else [],
        }

