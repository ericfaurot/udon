#
# Copyright (c) 2019 Eric Faurot <eric@faurot.net>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import base64
import json
import time

try:
    import requests
except ImportError:
    requests = None


def parse_jwt(value):
    def b64decode(buf):
        buf += "=" * ((4 - len(buf) % 4) % 4)
        return base64.b64decode(buf)
    parts= value.split(".")
    return { 'header': json.loads(b64decode(parts[0])),
             'content': json.loads(b64decode(parts[1])),
             'signature': parts[2],
             'signed': '.'.join(parts[:1]) }


class AuthError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message

class AuthRequired(AuthError):
    pass

class InvalidCredentials(AuthError):
    pass

class ExpiredCredentials(AuthError):
    pass


class ExpireCache:
    def __init__(self):
        self.cache = {}

    def purge(self, timestamp = None):
        if timestamp is None:
            timestamp = time.time()
        for key in [ key for (key, (timeout, _)) in self.cache.items() if timeout <= timestamp ]:
            del self.cache[key]

    def __len__(self):
        return len(self.cache)

    def __getitem__(self, key):
        return self.get(key)

    def get(self, key, timestamp = None):
        if timestamp is None:
            timestamp = time.time()
        timeout, value = self.cache.get(key, (None, None))
        if timeout is None:
            raise KeyError(key)
        if timeout <= timestamp:
            del self.cache[key]
            self.purge(timestamp)
            raise ExpiredCredentials(value)
        return value

    def set(self, key, value, timeout):
        self.cache[key] = timeout, value

    def unset(self, key):
        del self.cache[key]


class Portal:

    def __init__(self):
        self.cache = ExpireCache()

    def user_noauth(self, request):
        raise AuthRequired

    def user_public(self, request):
        raise AuthRequired

    def user_bearer(self, request, access_token, jwt):
        raise NotImplementedError

    def user(self, request):
        auth = request.headers.get("Authorization")
        if not auth:
            return self.user_noauth(request)

        parts = auth.split(' ', 1)
        scheme = parts[0]

        if scheme == 'Public':
            return self.user_public(request)

        if scheme == 'Bearer':
            access_token = parts[1].strip()
            try:
                return self.cache.get(access_token)
            except KeyError:
                try:
                    jwt = parse_jwt(access_token)
                    timeout = jwt['content']['exp']
                except:
                    raise InvalidCredentials("Invalid authorization token")
                user = self.user_bearer(request, access_token, jwt)
                self.cache.set(access_token, user, timeout)
                return user

        raise InvalidCredentials("Invalid authorization scheme")


class OpenIDClient:

    def __init__(self, host, realm, client_id, client_secret, verify = True):
        self.verify = verify
        self.realm = realm
        self.host = host
        self.client_id = client_id
        self.client_secret = client_secret

    def _url(self, action):
        return "%s/auth/realms/%s/protocol/openid-connect/%s" % (self.host, self.realm, action)

    def _request(self, method, action, data = None, headers = None):
        return requests.request(method, self._url(action), verify = self.verify, data = data, headers = headers)

    def login(self, username, password):
        return self._request('POST', 'token', data = { 'client_id': self.client_id,
                                                       'client_secret': self.client_secret,
                                                       'scope': 'openid',
                                                       'grant_type': 'password',
                                                       'username': username,
                                                       'password': password }).json()

    def refresh(self, refresh_token):
        return self._request('POST', 'token', data = { 'client_id': self.client_id,
                                                       'client_secret': self.client_secret,
                                                       'grant_type': 'refresh_token',
                                                       'refresh_token': refresh_token }).json()

    def logout(self, refresh_token):
        return self._request('POST', 'logout', data = { 'client_id': self.client_id,
                                                        'client_secret': self.client_secret,
                                                        'refresh_token': refresh_token }).status_code == 204

    def userinfo(self, access_token):
        return self._request('GET', 'userinfo', headers = { 'Authorization': 'Bearer ' + access_token }).json()
