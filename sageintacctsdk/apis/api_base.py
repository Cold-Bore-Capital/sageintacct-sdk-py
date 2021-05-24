"""
API Base class with util functions
"""
import json
import datetime
import uuid
from typing import Dict
from urllib.parse import unquote
import re

import xmltodict
import requests

from ..exceptions import SageIntacctSDKError, ExpiredTokenError, InvalidTokenError, NoPrivilegeError,\
    WrongParamsError, NotFoundItemError, InternalServerError
from .constants import dimensions_fields_mapping

class ApiBase:
    """The base class for all API classes."""

    def __init__(self, dimension: str = None, pagesize: int = 2000, post_legacy_method: str = None):
        self.__sender_id = None
        self.__sender_password = None
        self.__session_id = None
        self.__api_url = 'https://api.intacct.com/ia/xml/xmlgw.phtml'
        self.__dimension = dimension
        self.__pagesize = pagesize
        self.__post_legacy_method = post_legacy_method

    def set_sender_id(self, sender_id: str):
        """
        Set the sender id for APIs
        :param sender_id: sender id
        :return: None
        """
        self.__sender_id = sender_id

    def set_sender_password(self, sender_password: str):
        """
        Set the sender password for APIs
        :param sender_password: sender id
        :return: None
        """
        self.__sender_password = sender_password

    def get_session_id(self, user_id: str, company_id: str, user_password: str):
        """
        Sets the session id for APIs
        :param access_token: acceess token (JWT)
        :return: session id
        """

        timestamp = datetime.datetime.now()
        dict_body = {
            'request': {
                'control': {
                    'senderid': self.__sender_id,
                    'password': self.__sender_password,
                    'controlid': timestamp,
                    'uniqueid': False,
                    'dtdversion': 3.0,
                    'includewhitespace': False
                },
                'operation': {
                    'authentication': {
                        'login': {
                            'userid': user_id,
                            'companyid': company_id,
                            'password': user_password
                        }
                    },
                    'content': {
                        'function': {
                            '@controlid': str(uuid.uuid4()),
                            'getAPISession': None
                        }
                    }
                }
            }
        }

        response = self.__post_request(dict_body, self.__api_url)

        if response['authentication']['status'] == 'success':
            session_details = response['result']['data']['api']
            self.__api_url = session_details['endpoint']
            self.__session_id = session_details['sessionid']

            return self.__session_id

        else:
            raise SageIntacctSDKError('Error: {0}'.format(response['errormessage']))

    def set_session_id(self, session_id: str):
        """
        Set the session id for APIs
        :param session_id: session id
        :return: None
        """
        self.__session_id = session_id

    def __support_id_msg(self, errormessages):
        """Finds whether the error messages is list / dict and assign type and error assignment.

        Parameters:
            errormessages (dict / list): error message received from Sage Intacct.

        Returns:
            Error message assignment and type.
        """
        error = {}
        if isinstance(errormessages['error'], list):
            error['error'] = errormessages['error'][0]
            error['type'] = 'list'
        elif isinstance(errormessages['error'], dict):
            error['error'] = errormessages['error']
            error['type'] = 'dict'

        return error

    def __decode_support_id(self, errormessages):
        """Decodes Support ID.

        Parameters:
            errormessages (dict / list): error message received from Sage Intacct.

        Returns:
            Same error message with decoded Support ID.
        """
        support_id_msg = self.__support_id_msg(errormessages)
        data_type = support_id_msg['type']
        error = support_id_msg['error']
        if (error and error['description2']):
            message = error['description2']
            support_id = re.search('Support ID: (.*)]', message)
            if support_id.group(1):
                decoded_support_id = unquote(support_id.group(1))
                message = message.replace(support_id.group(1), decoded_support_id)

        # Converting dict to list even for single error response
        if data_type == 'dict':
            errormessages['error'] = [errormessages['error']]
    
        errormessages['error'][0]['description2'] = message if message else None

        return errormessages

    def __post_request(self, dict_body: dict, api_url: str):
        """Create a HTTP post request.

        Parameters:
            data (dict): HTTP POST body data for the wanted API.
            api_url (str): Url for the wanted API.

        Returns:
            A response from the request (dict).
        """

        api_headers = {
            'content-type': 'application/xml'
        }
        body = xmltodict.unparse(dict_body)

        response = requests.post(api_url, headers=api_headers, data=body)

        parsed_xml = xmltodict.parse(response.text, force_list={self.__dimension})
        parsed_response = json.loads(json.dumps(parsed_xml))

        if response.status_code == 200:
            if parsed_response['response']['control']['status'] == 'success':
                api_response = parsed_response['response']['operation']

            if parsed_response['response']['control']['status'] == 'failure':
                exception_msg = self.__decode_support_id(parsed_response['response']['errormessage'])
                raise WrongParamsError('Some of the parameters are wrong', exception_msg)

            if api_response['authentication']['status'] == 'failure':
                raise InvalidTokenError('Invalid token / Incorrect credentials', api_response['errormessage'])

            if api_response['result']['status'] == 'success':
                return api_response

            if api_response['result']['status'] == 'failure':
                exception_msg = self.__decode_support_id(api_response['result']['errormessage'])

                for error in exception_msg['error']:
                    if error['description2'] and 'You do not have permission for API' in error['description2']:
                        raise InvalidTokenError('The user has insufficient privilege', exception_msg)

                raise WrongParamsError('Error during {0}'.format(api_response['result']['function']), exception_msg)

        if response.status_code == 400:
            raise WrongParamsError('Some of the parameters are wrong', parsed_response)

        if response.status_code == 401:
            raise InvalidTokenError('Invalid token / Incorrect credentials', parsed_response)

        if response.status_code == 403:
            raise NoPrivilegeError('Forbidden, the user has insufficient privilege', parsed_response)

        if response.status_code == 404:
            raise NotFoundItemError('Not found item with ID', parsed_response)

        if response.status_code == 498:
            raise ExpiredTokenError('Expired token, try to refresh it', parsed_response)

        if response.status_code == 500:
            raise InternalServerError('Internal server error', parsed_response)

        raise SageIntacctSDKError('Error: {0}'.format(parsed_response))

    def format_and_send_request(self, data: Dict):
        """Format data accordingly to convert them to xml.

        Parameters:
            data (dict): HTTP POST body data for the wanted API.

        Returns:
            A response from the __post_request (dict).
        """

        key = next(iter(data))
        timestamp = datetime.datetime.now()

        dict_body = {
            'request': {
                'control': {
                    'senderid': self.__sender_id,
                    'password': self.__sender_password,
                    'controlid': timestamp,
                    'uniqueid': False,
                    'dtdversion': 3.0,
                    'includewhitespace': False
                },
                'operation': {
                    'authentication': {
                        'sessionid': self.__session_id
                    },
                    'content': {
                        'function': {
                            '@controlid': str(uuid.uuid4()),
                            key: data[key]
                        }
                    }
                }
            }
        }

        response = self.__post_request(dict_body, self.__api_url)
        return response['result']

    def post(self, data: Dict):
        if self.__dimension in ('CCTRANSACTION', 'EEXPENSES', 'EPPAYMENT'):
            return self.__construct_post_legacy_payload(data)

        return self.__construct_post_payload(data)
    
    def __construct_post_payload(self, data: Dict):
        payload = {
            'create': {
                self.__dimension: data
            }
        }

        return self.format_and_send_request(payload)

    def __construct_post_legacy_payload(self, data: Dict):
        payload = {
            self.__post_legacy_method: data
        }

        return self.format_and_send_request(payload)

    def count(self):
        get_count = {
            'query': {
                'object': self.__dimension,
                'select': {
                    'field': 'RECORDNO'
                },
                'pagesize': '1'
            }
        }

        response = self.format_and_send_request(get_count)
        return int(response['data']['@totalcount'])

    def get(self, field: str, value: str, fields: list = None):
        """Get data from Sage Intacct based on filter.

        Parameters:
            field (str): A parameter to filter by the field. (required).
            value (str): A parameter to filter by the field - value. (required).

        Returns:
            Dict.
        """
        data = {
            'readByQuery': {
                'object': self.__dimension,
                'fields': ','.join(fields) if fields else '*',
                'query': "{0} = '{1}'".format(field, value),
                'pagesize': '1000'
            }
        }

        return self.format_and_send_request(data)['data']

    def get_all(self, field: str = None, value: str = None, fields: list = None):
        """Get all data from Sage Intacct

        Returns:
            List of Dict.
        """
        complete_data = []
        count = self.count()
        pagesize = self.__pagesize

        for offset in range(0, count, pagesize):
            data = {
                'query': {
                    'object': self.__dimension,
                    'select': {
                        'field': fields if fields else dimensions_fields_mapping[self.__dimension]
                    },
                    'pagesize': pagesize,
                    'offset': offset
                }
            }

            if field and value:
                data['query']['filter'] = {
                    'equalto': {
                        'field': field,
                        'value': value
                    }
                }

            paginated_data = self.format_and_send_request(data)['data'][self.__dimension]
            complete_data.extend(paginated_data)

        return complete_data
