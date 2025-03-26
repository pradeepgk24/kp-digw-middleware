# pylint: skip-file
import base64
import re

from common.api_clients.common.api_client import ApiClient, ApiObjectModel
from common.secrets.secrets_manger import SecretsManager
from middleware.common.helpers.exception import NoDataError


class MSDApiClient(ApiClient):
    """
    Api client for MSD internal APIs
    """

    msd_api_version = 'v2'

    def __init__(self, api_url, lambda_secrets_manager: SecretsManager, api_key=None, secret_manager_connection=None):
        self.api_url = api_url
        self.api_key = api_key
        self.secret_manager_connection = secret_manager_connection
        self.lambda_secrets_manager = lambda_secrets_manager

    def _create_request_header(self, headers: dict, url: str) -> dict:
        """
        Create request header

        @param headers: request headers to be added
        @return: request
        """
        api_credentials = self._get_api_credentials({'key', 'secret'})
        request_header = dict()
        if self.api_key:
            request_header['X-Merck-APIKey'] = self.api_key
        else:
            self.api_key = api_credentials['key']
            request_header['X-Merck-APIKey'] = self.api_key

        api_secret = api_credentials['secret']
        auth_str = self.api_key + ':' + api_secret
        request_header['Authorization'] = 'Basic ' + base64.b64encode(auth_str.encode()).decode('utf-8')

        if re.findall('authentication-service', url):
            request_header.pop('X-Merck-APIKey')

        if isinstance(headers, dict):
            request_header.update(headers)
        return request_header

    def _get_api_credentials(self, keys: set[str]) -> dict[str, str]:
        """
        Get the API credentials from secret manager

        @param keys: the set of API keys
        @return: the list of API credentials associated with the key
        """
        result = {}
        sm = self.lambda_secrets_manager.get_secret_string_data(self.secret_manager_connection)
        for key in keys:
            try:
                result[key] = sm[key]
            except KeyError:
                raise Exception(f"Secret manager {self.secret_manager_connection} is missing API key. "
                                f"It should be stored in {key}.")
        return result

    @staticmethod
    def _parse_api_client_response_get_groups(response):
        """
        Parse the response from the API for the internal directory
        """
        result = []
        res_json = response.json()
        for security_group in res_json['_embedded']['securityGroups']:
            result.append({'name': security_group['name'], 'displayName': security_group['displayName']})
        return {'items': result}

    @staticmethod
    def _process_response(response, url_call, response_callback):
        """

        :param response:
        :param url_call:
        :param response_callback:
        :return:
        """
        if response.status_code in [200, 204]:
            return response_callback(response)
        if response.status_code == 404:
            raise NoDataError(f"subject not found")
        raise Exception(f"Call to Merck Internal API {url_call} was not successful\n"
                        f"status_code={response.status_code} \n"
                        f"reason={response.content}")

    def get_security_group_by_name(self, security_group_name: str) -> ApiObjectModel:
        """
        Get SG by name

        @param security_group_name: Security group to be fetched from the API
        @return: API object model for the security group name
        @rtype: ApiObjectModel
        """
        return self._call_api(f"https://{self.api_url}/internal-directory/{self.msd_api_version}"
                              f"/securityGroups/{security_group_name}", 'get')

    def get_security_group_by_isid(self, isid: str) -> ApiObjectModel:
        """
        Get all security groups by isid

        @param isid: isid of the user
        @return: API object model for the security groups API call
        @rtype: ApiObjectModel
        """
        return self._call_api(f"https://{self.api_url}/internal-directory/{self.msd_api_version}"
                              f"/users/{isid}/securityGroups", 'get',
                              response_callback=MSDApiClient._parse_api_client_response_get_groups)

    def get_security_groups(self, security_group_filter) -> ApiObjectModel:
        """
        Get all security Groups
        """
        return self._call_api(f"https://{self.api_url}/internal-directory/{self.msd_api_version}"
                              f"/securityGroups", 'get', uri_parameters={"filter": f"name={security_group_filter}*"},
                              response_callback=MSDApiClient._parse_api_client_response_get_groups)

    def get_user_info(self, token: str) -> ApiObjectModel:
        """
        Get user info using the Merck Authentication Service API GET method

        Example:
            Url: https://iapi-test.merck.com/authentication-service/v2/userinfo
        HTTP Headers:
            Content-Type: application/json
            Authorization: 'Bearer 2YotnFZFEjr1zCsicMWpAA'

        API response:
            {
              "isid": "jsmith",
              "sub": "jsmith",
              "given_name": "John",
              "family_name": "Smith",
              "email": "john.smith@merck.com"
            }

        @param token: Merck Authentication Service API token
        @type token: str
        @return: API response for the userinfo request
        @rtype: ApiObjectModel
        """
        return self._call_api(f"https://{self.api_url}/authentication-service/{self.msd_api_version}/userinfo",
                              'get', headers={"Authorization": f"Bearer {token}"},
                              response_callback=lambda res: res.json(), urlencoded_post=True)

    def get_or_refresh_token(self, token: str, refresh: bool) -> ApiObjectModel:
        """
        Get or refresh token using the Merck Authentication Service API POST method

        Example:
            Url: https://iapi-test.merck.com/authentication-service/v2/token
            HTTP Headers:
                Content-Type': 'application/x-www-form-urlencoded
            HTTP Body:
                grant_type=authorization_code&code=SplxlOBeZQQYbYS6WxSbIA

            API response:
                {
                  "issued_at": 1612274196369,
                  "access_token": "2YotnFZFEjr1zCsicMWpAA",
                  "expires_in": 1800,
                  "token_type": "Bearer",
                  "scope": "default",
                  "state": "GaC2FD8h_Xro4SMc17YBqpJYSYZI",
                  "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",
                  "refresh_token_expires_in": 43199,
                  "refresh_count": 0,
                  "client_id": "xCD1neP06VeTE3206161GpJ"
                }

        @param refresh_token: refresh token from the Authentication Service API
        @type refresh_token: str
        @return: API response
        @rtype: ApiObjectModel
        """
        grant_type = "refresh_token" if refresh else "authorization_code"
        code = "refresh_token" if refresh else "code"
        return self._call_api(f"https://{self.api_url}/authentication-service/{self.msd_api_version}/token",
                              'post', request_data={"grant_type": grant_type, code: token}, urlencoded_post=True)

    def revoke_token(self, access_token: str):
        """
        Revoke the token from the Authentication Service API POST method

        Example:
            Url: https://iapi-test.merck.com/authentication-service/v2/revoke
            HTTP Headers:
                Content-Type': 'application/x-www-form-urlencoded
            HTTP Body:
                token=C7HU3wXvx3Gc00akEnI9z2E1cL1e

        @param access_token: the access token from Authentication Service API which needs to be revoked
        @type access_token: str
        @return: API response
        @rtype: dict
        """
        return self._call_api(f"https://{self.api_url}/authentication-service/{self.msd_api_version}/revoke",
                              'post', response_callback=lambda res: res,
                              request_data={"token": access_token}, urlencoded_post=True)

    def send_email(self, headers: dict, data: dict) -> ApiObjectModel:
        """
        Send email via merck email api POST method

        Example:
            Url: https://iapi-dev.merck.com/email-service/v1/messages
            Headers:
                --header 'Accept: application/problem+json'
                --header 'Authorization: Bearer 123'
                --header 'Content-Type: application/json'
            Body:

        @param headers: contains token from Authentication Service API
        @param data
        @type : data
        @return: API response
        @rtype: dict
        """
        return self._call_api(f"https://iapi.merck.com/email-service/v1/messages", 'post',
                              response_callback=lambda res: res,
                              headers=headers, request_data=data)