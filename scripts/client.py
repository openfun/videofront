import os
import requests


class Client(object):

    def __init__(self, host, token=None, username=None, password=None):
        self.host = host
        self.token = token or os.environ.get('VIDEOFRONT_TOKEN')
        if not self.token:
            if not username or not password:
                raise ValueError(
                    "You need to either define an authentication token "
                    "or a pair username/password. Both can be obtained by "
                    "running the 'createuser' management command.\n"
                    "The token can also be set as the VIDEOFRONT_TOKEN environment variable."
                )
            self.token = self.get_token(username, password)

    def endpoint(self, name):
        return self.host + '/api/v1/' + name

    def get_token(self, username, password):
        response = requests.post(
            self.endpoint('auth-token/'),
            data={
                'username': username,
                'password': password,
            }
        )
        response_data = response.json()
        return response_data['token']

    def get(self, endpoint):
        return self._request('get', endpoint)

    def post(self, endpoint):
        return self._request('post', endpoint)

    def _request(self, method, endpoint):
        func = getattr(requests, method)
        return func(
            self.endpoint(endpoint),
            headers={'Authorization': 'Token ' + self.token}
        ).json()

