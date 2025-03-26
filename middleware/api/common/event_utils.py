from typing import Dict, Optional
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent


class DIFWAPIGatewayProxyEvent(APIGatewayProxyEvent):
    """Override some of the functionality present in aws power tool"""

    @property
    def headers(self) -> Dict[str, str]:
        return {key.lower(): value for key, value in self["headers"].items()}

    @property
    # pylint: disable=unsubscriptable-object
    # TODO Shall be removed in NGA-2453
    def query_string_parameters(self) -> Optional[Dict[str, str]]:
        if not self.get("queryStringParameters"):
            return {}
        return self.get("queryStringParameters")

    @property
    # pylint: disable=unsubscriptable-object
    # TODO Shall be removed in NGA-2453
    def path_parameters(self) -> Optional[Dict[str, str]]:
        if not self.get("pathParameters"):
            return {}
        return self.get("pathParameters")