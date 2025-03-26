import json

from middleware.api.common.aws_event_handler import AWSLambdaEventHandler
from middleware.api.common.http_method_utils import create_error_response


class LoggingLambda(AWSLambdaEventHandler):
    """
    Lambda class for logging API, there should be no authentication going on for the
    requests going into the logging API
    """
    def _invoke_send_logs(self):
        """
        Invoke method call for sending logs to cloudwatch logstream
        :return: API response
        """
        self.logger.info("Calling _invoke_send_logs")
        request_body = self.event.json_body
        # ui_logger is for filtering of the messages from the UI in AWS cloudwatch
        extra_fields = {'ui_logger': True,
                        'subjects': request_body.get('subjects')}
        self.logger.info(request_body.get('errorMessage'), extra=extra_fields)
        return {'statusCode': 200, 'body': json.dumps({
            "result": "Log saved"
        })}

    def invoke(self):
        """
        Invoke lambda function logic

        :return:
        """
        # *******************************  SEND LOGS TO CLOUDWATCH*****************************************************
        if self.event.http_method == "POST" and self.event.resource.endswith("/logging"):
            return self._invoke_send_logs()
        self.logger.warning(
            f"Method:{self.event.http_method} and Resource:{self.event.resource}\n does not fit any chosen method")
        return create_error_response("No correct logging method was chosen")
