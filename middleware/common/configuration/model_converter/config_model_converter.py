import copy

from middleware.common.entity_management.secrets_management import SecretsManagement


class ConfigModelConverter:
    """
    Common class for converter modules
    """

    JOB_TYPE_PLATFORM_DEFAULT_MAPPING = {
        "glue": {"supportedJobTypes": ["spark"]},
        "databricks": {"supportedJobTypes": ["spark_databricks"]}
    }

    MODEL_TYPE_STRING = "string"
    MODEL_TYPE_OPTIONS = "options"
    MODEL_TYPE_NUMBER = "number"
    MODEL_TYPE_TIMESTAMP = "timestamp"
    MODEL_TYPE_SECRET = "secret"
    MODEL_TYPE_DICTIONARY = "dictionary"
    MODEL_TYPE_OBJECT = "object"
    MODEL_TYPE_OBJECT_GROUP = "objectGroup"
    MODEL_TYPE_BOOL = "boolean"
    MODEL_TYPE_LIST = "list"
    MODEL_TYPE_S3OBJECT = "s3object"

    DIFW_STEP_CATEGORY_INPUT = "input"
    DIFW_STEP_CATEGORY_OUTPUT = "output"
    DIFW_STEP_CATEGORY_PROCESS = "process"
    DIFW_STEP_CATEGORY_TRANSFORMATION = "transformation"

    DIFW_JOB_CATEGORY_STEPS = "steps"
    DIFW_JOB_CATEGORY_SNIFFER = "sniffer"
    DIFW_JOB_CATEGORY_OPERATOR = "operator"

    MODEL_STEP_CATEGORY_IN_CONNECTOR = "input_connector"

    BASIC_MODEL_TYPES = [MODEL_TYPE_STRING, MODEL_TYPE_NUMBER, MODEL_TYPE_TIMESTAMP, MODEL_TYPE_DICTIONARY,
                         MODEL_TYPE_OPTIONS, MODEL_TYPE_BOOL, MODEL_TYPE_S3OBJECT]

    AWS_ACCESS_KEY_ID_DEFINITION = {
        "attributeName": "aws_access_key_id",
        "type": {
            "objectType": "secret"
        }
    }

    AWS_SECRET_ACCESS_KEY_DEFINITION = {
        "attributeName": "aws_secret_access_key",
        "type": {
            "objectType": "secret"
        }
    }

    S3_ASSUME_ROLE_ATTR_DEFINITION = {
        "attributeName": "s3_assume_role",
        "type": {
            "objectType": "string"
        }
    }

    SPARK_ASSUME_ROLE_ATTR_DEFINITION = {
        "attributeName": "spark_assume_role",
        "type": {
            "objectType": "string"
        }
    }

    def __init__(self, logger, secrets_management: SecretsManagement):
        self.logger = logger
        self.secrets_management = secrets_management

    @staticmethod
    def copy_and_replace_template_attr(attr_template: dict, attr_value):
        """
        Take definition of attr_template, copy it and assign correct value

        :param attr_template: template of attribute
        :param attr_value: new value of attribute

        :return attr_template: new representation of attribute
        """
        copy_attr = copy.deepcopy(attr_template)
        copy_attr["value"] = attr_value
        return copy_attr
