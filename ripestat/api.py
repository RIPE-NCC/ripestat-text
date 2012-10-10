from cookielib import CookieJar, Cookie
import sys
import urllib
import urllib2
try:
    import simplejson as json
except ImportError:
    import json

from ripestat import VERSION


class DataResponse(dict):
    def __init__(self, response):
        dict.__init__(self)
        self.update(response["data"])
        del response["data"]
        self.meta = response


class StatAPI(object):
    RIPE_ACCESS = "https://access.ripe.net"

    class VersionError(Exception):
        message = "Bla bla bla"

    class Error(Exception):

        def __init__(self, http_error):
            serialized = http_error.read()
            self.response = json.loads(serialized)
            self.args = [m[1] for m in self.response["messages"] if m[0] ==
                "error"]

    def __init__(self, base_url="https://stat.ripe.net/data/", token=None,
            caller_id=None):
        self.base_url = base_url

        self.cookiejar = StatCookieJar(token)

        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(
            self.cookiejar))

        self.ua_parts = [
            "ripestat-text/%s" % VERSION,
            "python/" + ".".join(str(v) for v in sys.version_info[:3]),
            "platform/" + sys.platform
        ]
        self.caller_id = caller_id

    def get_session(self):
        if self.cookiejar.token:
            return self.cookiejar.token
        self.get_response()
        return self.cookiejar.token

    def get_data(self, call, query=None, version=None):
        json_response = self.get_response("%s/data.json" % call, query)
        response = json.loads(json_response)
        if version is not None:
            maj_version, min_version = response["version"].split(".", 2)
            if int(maj_version) != version:
                raise self.VersionError(
                    "Expected version %s.x of '%s', but found %s." % (
                        version, call, response["version"]))
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
            raise self.Error(exc)
        return response.decode("UTF-8")

    def open(self, url, *args, **kwargs):
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
