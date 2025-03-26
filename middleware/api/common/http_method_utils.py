import json


def create_error_response(error_message, stack_trace="", status_code=500, details=None):
    """Creates error response in the format accepted by AWS API gateway"""
    body = {"result": error_message, 'details': details, "stackTrace": stack_trace}
    return {'statusCode': status_code, 'body': json.dumps(body)}