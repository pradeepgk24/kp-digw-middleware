import time
import logging
import traceback
import json
import sys
from botocore.exceptions import ClientError
from middleware.api.common.http_method_utils import create_error_response
from middleware.common.helpers.exception import NoDataError, EntityConflictError, EntityDisabledError, \
    FailedConnectionError, BadRequest, AuthorizationError, AuthTokenError

logger = logging.getLogger()


def timer(func):
    """Log the runtime of the decorated function"""

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()
        response = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        logger.info(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        return response

    return wrapper_timer


def sdk_call(request):
    """
    Decorator for API calls

    :param request:
    :return:
    """

    @functools.wraps(request)
    def wrapper(*args, **kwargs):
        try:
            res = request(*args, **kwargs)
            status_code = 200
            if "ResponseMetadata" in res:
                status_code = res["ResponseMetadata"].get("HTTPStatusCode", 200)
                del res["ResponseMetadata"]
            response = {'statusCode': status_code, 'body': json.dumps(res, default=str)}
            return response
        except ClientError as exc:
            response = {'statusCode': exc.response['ResponseMetadata']['HTTPStatusCode'],
                        'body': json.dumps(exc.response['Error'])}
            return response

    return wrapper


def enable_cors(func):
    """Enables the CORS for the APIs"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if isinstance(response, dict):
            cors_headers = {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': '*'}
            response['headers'] = cors_headers
        return response

    return wrapper


# pylint: disable=broad-except
def catch_uncaught_errors(func):
    """catches and returns uncaught errors"""

    @functools.wraps(func)
    # pylint: disable=too-many-branches
    def wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
        except AuthTokenError:
            logger.error("Auth token error during API call", exc_info=True)
            response = create_error_response(error_message="Auth token error during API call",
                                             status_code=401, details=str(sys.exc_info()[1]),
                                             stack_trace=str(traceback.format_exc()))
        except NoDataError:
            logger.error("Data not found error during API call", exc_info=True)
            response = create_error_response(error_message="Data not found error during API call",
                                             status_code=404, details=str(sys.exc_info()[1]),
                                             stack_trace=str(traceback.format_exc()))
        except EntityConflictError:
            logger.error("Data with same identifiers already exists", exc_info=True)
            response = create_error_response(error_message="Data conflict",
                                             status_code=409, details=str(sys.exc_info()[1]),
                                             stack_trace=str(traceback.format_exc()))
        except EntityDisabledError:
            logger.error("Subject is disabled", exc_info=True)
            response = create_error_response(error_message="Subject is disabled",
                                             status_code=410, details=str(sys.exc_info()[1]),
                                             stack_trace=str(traceback.format_exc()))
        except BadRequest:
            logger.error("Bad request error during API call", exc_info=True)
            response = create_error_response(error_message="Bad request",
                                             status_code=400, details=str(sys.exc_info()[1]),
                                             stack_trace=str(traceback.format_exc()))
        except AuthorizationError:
            logger.error("Authorization error during API call", exc_info=True)
            response = create_error_response(error_message="Insufficient permissions",
                                             status_code=403, details=str(sys.exc_info()[1]),
                                             stack_trace=str(traceback.format_exc()))
        except FailedConnectionError:
            logger.error("Failed to establish connectivity during API call", exc_info=True)
            # TODO: the status code should be changed to something else
            response = create_error_response(error_message="Failed to establish connectivity",
                                             status_code=401, details=str(sys.exc_info()[1]),
                                             stack_trace=str(traceback.format_exc()))
        except:  # pylint: disable=bare-except
            logger.error("Internal server error", exc_info=True)
            response = create_error_response(error_message="Internal server error",
                                             status_code=500, details=str(sys.exc_info()[1]),
                                             stack_trace=str(traceback.format_exc()))
        return response

    return wrapper