from cookielib import CookieJar, Cookie
import sys
import urllib
import urllib2
try:
    import simplejson as json
except ImportError:
    import json

from ripestat import VERSION


class StatAPI(object):
    """
    A Python wrapper around the RIPEstat Data API.
    """
    RIPE_ACCESS = "https://access.ripe.net"
    DATA_API = "https://stat.ripe.net/data/"

    class Error(Exception):
        """
        The base class for exceptions raised by this class.
        """

    class ServerError(Error):
        """
        Raised when an unsuccesful response is received from the server.
        """
        def __init__(self, http_error):
            serialized = http_error.read()
            self.response = json.loads(serialized)
            self.args = [m[1] for m in self.response["messages"] if m[0] ==
                "error"]

    class VersionError(Error):
        """
        Raised when there is a mismatch between expected and actual version
        numbers.
        """
        def __init__(self, call, requested, actual):
            StatAPI.Error.__init__(self, "expected version {1}.x of the '{0}' "
                "data call; found {2}".format(call, requested, actual))

    def __init__(self, caller_id, base_url=DATA_API, token=None):
        self.base_url = base_url

        self.cookiejar = StatCookieJar(token)

        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(
            self.cookiejar))

        # These are the parts of the User-Agent that stay constant
        self.ua_parts = [
            "ripestat-text/%s" % VERSION,
            "python/" + ".".join(str(v) for v in sys.version_info[:3]),
            "platform/" + sys.platform
        ]
        # The caller_id is added to the User-Agent header.
        # It can be changed after instantiation.
        self.caller_id = caller_id

    def get_session(self):
        """
        Carry out a single request in order to get a session cookie.
        """
        if self.cookiejar.token:
            return self.cookiejar.token
        self.get_response()
        return self.cookiejar.token

    def get_data(self, call, query=None, version=None):
        """
        Execute and deserialize a single RIPEstat data call, possibly
        requesting a specific version.
        """
        json_response = self.get_response("%s/data.json" % call, query)
        response = json.loads(json_response)
        if version is not None:
            maj_version, min_version = response["version"].split(".", 2)
            if int(maj_version) != version:
                raise self.VersionError(call, version, response["version"])
        return DataResponse(response)

    def get_response(self, url=None, query=None):
        """
        Return the (serialized) body of a raw data response.
        """
        if url:
            url = "%s/%s" % (self.base_url.rstrip("/"), url)
        else:
            url = self.base_url
        if not url.startswith("http"):
            url = "https://" + url
        if query:
            url += "?" + urllib.urlencode(query)

        try:
            response = self.open(url).read()
        except urllib2.HTTPError as exc:
            raise self.ServerError(exc)
        return response.decode("UTF-8")

    def open(self, url, *args, **kwargs):
        """
        Wrapper around the urllib2 opener that sets a User-Agent header
        based on the calling application, the running mode
        """
        if isinstance(url, basestring):
            url = urllib2.Request(url)
        ua_parts = self.ua_parts
        if self.caller_id:
            ua_parts = [self.caller_id] + ua_parts
        url.add_header("User-agent", " ".join(ua_parts))
        return self.opener.open(url, *args, **kwargs)


    def login(self, username, password):
        """
        Authenticate with the RIPE NCC Access framework by asking for a
        password from the user.
        """
        response = self.open(self.RIPE_ACCESS, urllib.urlencode({
                "username": username,
                "password": password,
                "originalUrl": "",
            }))
        return "Welcome," in response.read()


class StatCookieJar(CookieJar):
    """
    CookieJar that remembers and reinserts RIPE NCC Access cookies.
    """
    CROWD_COOKIE = "crowd.token_key"
    STAT_COOKIE = "stat-session"

    def __init__(self, token=None):
        CookieJar.__init__(self)

        if token:
            parts = token.split("_")
            if len(parts) == 2:
                crowd, stat = parts
                self.make_cookie(self.CROWD_COOKIE, crowd)
                self.make_cookie(self.STAT_COOKIE, stat)

    def make_cookie(self, name, value):
        """
        Create and set a cookie with the given name and value.
        """
        cookie = Cookie(
            name=name,
            value=value,
            domain='.ripe.net',
            path='/',

            version=0,
            port=None,
            port_specified=False,
            domain_specified=False,
            domain_initial_dot=False,
            path_specified=None,
            secure=True,
            expires=None,
            discard=None,
            comment=None,
            comment_url=None,
            rest=None,
        )
        self.set_cookie(cookie)

    @property
    def token(self):
        """
        Generate a serialized token suitable for setting in the TOKEN variable.
        """
        session = ""
        token = ""
        for cookie in self:
            if cookie.name == self.CROWD_COOKIE:
                token = cookie.value
            elif cookie.name == self.STAT_COOKIE:
                session = cookie.value
        if token and session:
            return token + "_" + session
        else:
            return ""


class DataResponse(dict):
    """
    The response from a data API call.

    It works like the "data" portion of the data response, but the remaining
    metadata is available as `response.meta`.
    """
    def __init__(self, response):
        dict.__init__(self)
        self.update(response["data"])
        del response["data"]
        self.meta = response
