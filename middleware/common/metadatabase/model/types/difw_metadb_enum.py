# pylint: skip-file
import enum


class DifwMetadbEnum(enum.Enum):

    @classmethod
    def from_str(cls, str_key):
        if str_key:
            return getattr(cls, str_key)
        return None

    @classmethod
    def get_values(cls):
        return [item.value for item in cls]