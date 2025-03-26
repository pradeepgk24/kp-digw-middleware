class RestApiError(Exception):
    """
    Exception caused by REST API responses
    """


class GeneratorValidationError(Exception):
    """
    Exception throw in case of Generator validation error
    """


class AuthorizationError(Exception):
    """
    Exception throw in case of authorization error
    """


class WrongDeclarationOfModelClass(Exception):
    """
    Exception throw in case of wrong declaration of MetaDB entity model class
    """


class BadRequest(Exception):
    """
    Exception throw in case that something is missing in Http request
    """


class GeneratorError(Exception):
    """
    Exception thrown in case of Generator Error
    """


class ValidationException(RuntimeError):
    """
    Validation exception
    """


class EntityConflictError(Exception):
    """
    Exception thrown in case that some entity already exists
    """


class NoDataError(Exception):
    """
    Exception to handle no data
    """


class EntityDisabledError(Exception):
    """
    Exception to handle if subject exists but it is disabled
    """


class FailedConnectionError(Exception):
    """
    Exception to handle failed connection - not established one
    """


class AuthTokenError(Exception):
    """
    Exception to handle failed authentication - token related
    """

class ConfigurationModelConvertorError(Exception):
    """
    Exception to handle failed configuration model convertor
    """