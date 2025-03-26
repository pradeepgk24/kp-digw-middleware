# pylint: skip-file

from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import Notifications
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum


class EntityNotifications(EntityObject):
    """
    Entity Notifications.
    """

    def __init__(self, notification_name, project_id, text, title, hex_rgb_color, valid_from, valid_to,
                 notification_id=None,
                 is_enabled: bool = True
                 ):
        self._notification_name = notification_name
        self._project_id = project_id
        self._text = text
        self._title = title
        self._hex_rgb_color = hex_rgb_color
        self._valid_from = valid_from
        self._valid_to = valid_to
        self._notification_id = notification_id
        self._is_enabled = is_enabled

    @property
    def notification_id(self):
        """
        Get notification id

        @return: notification id
        """
        return self._notification_id

    def set_notification_id(self, notification_id):
        """
        Set notification_id.

        @return: notification_id
        """
        self._notification_id = notification_id

    @property
    def notification_name(self):
        """
        Get notification name

        @return: notification name
        """
        return self._notification_name

    @property
    def project_id(self):
        """
        Get project id.

        @return: project id
        """
        return self._project_id

    @property
    def text(self):
        """
        Get text

        @return: text
        """
        return self._text

    @property
    def title(self):
        """
        Get title

        @return: title
        """
        return self._title

    @property
    def hex_rgb_color(self):
        """
        Get hex rgb color

        @return: hex rgb color
        """
        return self._hex_rgb_color

    @property
    def valid_from(self):
        """
        Get valid from

        @return: valid from
        """
        if not self._valid_from:
            return None
        return str(self._valid_from)

    @property
    def valid_to(self):
        """
        Get valid to

        @return: valid to
        """
        if not self._valid_to:
            return None
        return str(self._valid_to)

    @property
    def is_enabled(self):
        """
        Get is_enabled

        @return: is_enabled
        """
        return self._is_enabled

    def set_is_enabled(self, is_enabled):
        """
        Set notification_id.
        @param is_enabled:

        @return: new value of is_enabled.
        """
        self._is_enabled = is_enabled

    def to_json_dict(self):
        """
        return json definition of notifications

        @return: json object of notifications
        """
        return {
            'notificationId': self.notification_id,
            'notificationName': self.notification_name,
            "projectOwner": self.project_id,
            'text': self.text,
            'title': self.title,
            'hexRgbColor': self.hex_rgb_color,
            'validFrom': self.valid_from if self.valid_from else None,
            'validTo': self.valid_to if self.valid_to else None,
            'isEnabled': True if self._is_enabled == 1 else False
        }

    def to_metadb_object(self):
        """
        Convert to metadb related objects

        @return: notifications
        """
        return Notifications(NOTIFICATION_NAME=self.notification_name, PROJECT_ID=self.project_id,
                             TEXT=self.text, TITLE=self.title, HEX_RGB_COLOR=self.hex_rgb_color,
                             VALID_FROM=self.valid_from,
                             VALID_TO=self.valid_to, NOTIFICATION_ID=self.notification_id, IS_ENABLED=self.is_enabled)

    @staticmethod
    def from_metadb_object(db_object: Notifications):
        """
        Convert db object to entity object
        """
        if db_object is None:
            return None
        return EntityNotifications(db_object.NOTIFICATION_NAME, db_object.PROJECT_ID, db_object.TEXT,
                                   db_object.TITLE, db_object.HEX_RGB_COLOR, db_object.VALID_FROM, db_object.VALID_TO,
                                   db_object.NOTIFICATION_ID,
                                   db_object.IS_ENABLED)

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of  entity objects
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntityNotifications.from_metadb_object(db_object))
        return result

    @staticmethod
    def from_json_dict(json_dict, selected_subjects):
        """
        Create instance from json dictionary
        """
        return EntityNotifications(
            notification_name=json_dict.get('notificationName'),
            text=json_dict.get('text'),
            title=json_dict.get('title'),
            hex_rgb_color=json_dict.get('hexRgbColor'),
            valid_from=json_dict.get('validFrom'),
            valid_to=json_dict.get('validTo'),
            project_id=[subject.subject_id for subject in selected_subjects if
                        subject.subject_type == SubjectTypesEnum.project][0] if selected_subjects else [],
            is_enabled=json_dict.get('isEnabled', True)
        )
