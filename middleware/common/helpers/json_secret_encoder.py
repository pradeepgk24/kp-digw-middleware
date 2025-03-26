from json import JSONEncoder

from common.secrets.secrets import SecretValue


class JsonSecretEncoder(JSONEncoder):
    """
    Json encoder to solve serialization of the secrets value
    """

    def default(self, o):
        if isinstance(o, SecretValue):
            # if the object is secretValue type then return only secret name and key
            return {
                "secretName": o.secret_name,
                "secretKey": o.secret_key
            }
        return o.__dict__