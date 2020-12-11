import sublime
import webbrowser
import urllib
import re, uuid
from .SoftwareUtil import *
from .SoftwareFileDataManager import *
from .SoftwareHttp import *
from .SoftwareDashboard import *
from .SoftwareSettings import *
from .CommonUtil import *
from .SoftwareSessionApp import *
try:
    #python2
    from urllib import urlencode
except ImportError:
    #python3
    from urllib.parse import urlencode

LOGIN_LABEL = "Log in"

def isLoggedOn():

    name = getItem("name")
    switching_account = getItem("switching_account")

    if (name is not None and (switching_account is None or switching_account is False)):
        return True

    auth_callback_state = getAuthCallbackState()
    authType = getItem("authType")
    jwt = getItem("jwt")


    token = auth_callback_state if (auth_callback_state is not None) else jwt

    api = "/users/plugin/state"
    resp = requestIt("GET", api, None, token)

    user = getUserFromResponse(resp)

    if (user is None and (authType == "software" or authType == "email")):
        # check again using the jwt
        resp = requestIt("GET", api, None, jwt)
        user = getUserFromResponse(resp)

    if (user is not None):
        registered = user.get("registered", 0)
        setItem("jwt", user.get("plugin_jwt"))
        if (registered == 1):
            setItem("name", user.get("email"))
        else:
            setItem("name", None)

        if (authType is None):
            setItem("authType", "software")

        setItem("switching_account", False)
        setAuthCallbackState(None)
        return True

    return False

def getUserFromResponse(resp):
    if (isResponseOk(resp)):
        try:
            obj = json.loads(resp.read().decode('utf-8'))
            return obj.get("user", None)
        except Exception as ex:
            log("Code Time: Unable to retrieve user from plugin state: %s" % ex)
    return None

def refetchUserStatusLazily(tryCountUntilFoundUser):
    logged_on = isLoggedOn()

    if (logged_on is False):
        if (tryCountUntilFoundUser > 0):
            tryCountUntilFoundUser -= 1
            t = Timer(10, refetchUserStatusLazily, [tryCountUntilFoundUser])
            t.start()
        else:
            # tried enough times
            setItem("switching_account", False)
            setAuthCallbackState(None)
    else:
        setItem("switching_account", False)
        setAuthCallbackState(None)
        # successful logon
        infoMsg = "Successfully logged on to Code Time"
        sublime.message_dialog(infoMsg)

        # clear the session summary data and time summary data
        clearSessionSummaryData()
        clearTimeDataSummary()

        updateSessionSummaryFromServer(True)


def launchLoginUrl(loginType):
    webbrowser.open(getLoginUrl(loginType))
    refetchUserStatusLazily(40)

def getUrlEndpoint():
    return getValue("software_dashboard_url", "https://app.software.com")

def getLoginUrl(loginType):
    loginType = loginType.lower()

    auth_callback_state = str(uuid.uuid4())
    setAuthCallbackState(auth_callback_state)

    api_endpoint = getValue("software_api_endpoint", "api.software.com")
    app_url = getValue("software_dashboard_url", "app.software.com")

    scheme = "https"
    if bool(re.match("localhost", api_endpoint)):
        scheme = "http"

    loginUrl = scheme + "://"

    obj = {
        "plugin": "codetime",
        "plugin_uuid": getPluginUuid(),
        "pluginVersion": getVersion(),
        "plugin_id": getPluginId(),
        "auth_callback_state": auth_callback_state
    }

    if (loginType == "github"):
        obj["redirect"] = app_url
        loginUrl += api_endpoint + "/auth/github"
    elif (loginType == "google"):
        obj["redirect"] = app_url
        loginUrl += api_endpoint + "/auth/google"
    else:
        obj["token"] = getItem("jwt")
        obj["auth"] = "software"
        loginUrl += app_url + "/email-signup"

    qryStr = urlencode(obj)

    loginUrl += "?" + qryStr
    
    return loginUrl

def launchWebDashboardUrl():
    jwt = getItem('jwt')
    webUrl = getUrlEndpoint() + '?token=' + jwt
    webbrowser.open(webUrl)
