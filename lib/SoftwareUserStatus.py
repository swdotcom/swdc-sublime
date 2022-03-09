import sublime
import webbrowser
import urllib
import re, uuid
from .SoftwareUtil import *
from .SoftwareFileDataManager import *
from .SoftwareHttp import *
from .SoftwareSettings import *
from .CommonUtil import *
from .SoftwareSessionApp import *
from .SlackHttp import *
from .Logger import *
try:
    #python2
    from urllib import urlencode
except ImportError:
    #python3
    from urllib.parse import urlencode

LOGIN_LABEL = "Log in"

def getUserRegistrationState(is_integration=False):
    userState = {}
    userState["logged_on"] = False
    userState["user"] = None

    auth_callback_state = getAuthCallbackState(False)
    authType = getItem("authType")
    jwt = getItem("jwt")

    token = auth_callback_state if (auth_callback_state is not None) else jwt

    api = "/users/plugin/state"
    resp = requestIt("GET", api, None, token)
    user = getUserFromResponse(resp)

    if (user is None and is_integration is True and auth_callback_state is not None):
        # try using the jwt
        resp = requestIt("GET", api, None, jwt)
        user = getUserFromResponse(resp)

    if (user is not None):
        registered = user.get("registered", 0)
        user_jwt = user.get("plugin_jwt", None)

        if (registered == 1 and user_jwt is not None):
            logIt("Updated user JWT %s " % user_jwt)
            setItem("jwt", user_jwt)

            setItem("name", user.get("email"))

            setItem("switching_account", False)
            setAuthCallbackState(None)
            userState["logged_on"] = True
            userState["user"] = user
    else:
        userState["logged_on"] = False
        userState["user"] = None

    return userState

def getUserFromResponse(resp):
    if (isResponseOk(resp)):
        try:
            obj = json.loads(resp.read().decode('utf-8'))
            return obj.get("user", None)
        except Exception as ex:
            logIt("Code Time: Unable to retrieve user from plugin state: %s" % ex)
    return None

def refetchUserStatusLazily(tryCountUntilFoundUser):
    userState = getUserRegistrationState(False)

    if (userState["logged_on"] is False):
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

        getUser(True)

        initSessionSummaryThread = Thread(target=updateSessionSummaryFromServer, args=())
        initSessionSummaryThread.start()

def launchLoginUrl(loginType = "software", switching_account = True):
    webbrowser.open(getLoginUrl(loginType, switching_account))
    refetchUserStatusLazily(40)

def getLoginUrl(loginType = "software", switching_account=True):
    loginType = loginType.lower()

    jwt = getItem("jwt")
    name = getItem("name")

    auth_callback_state = str(uuid.uuid4())
    setAuthCallbackState(auth_callback_state)

    loginUrl = ""

    obj = {
        "plugin_id": getPluginId(),
        "auth_callback_state": auth_callback_state,
        "plugin_uuid": getPluginUuid(),
        "plugin_version": getVersion()
    }

    api_endpoint = getApiEndpoint()
    scheme = "https"
    if('localhost' in api_endpoint):
        scheme = "http"
    apiEndpointUrl = scheme + "://" + api_endpoint

    if (loginType == "github"):
        loginUrl = getWebUrl() + "/auth/github"
    elif (loginType == "google"):
        loginUrl = getWebUrl() + "/auth/google"
    else:
        obj["token"] = getItem("jwt")
        obj["auth"] = "software"
        if (switching_account is False):
            loginUrl = getWebUrl() + "/email-signup"
        else:
            loginUrl = getWebUrl() + "/onboarding"

    qryStr = urlencode(obj)

    loginUrl += "?" + qryStr
    if (switching_account is True):
        loginUrl += "&login=true"

    return loginUrl

def launchWebDashboardUrl():
    webbrowser.open(getWebUrl())

def launchCodeTimeDashboard():
    webbrowser.open(getWebUrl() + "/dashboard/code_time?view=summary")

def launchUpdatePreferences():
    webbrowser.open(getWebUrl() + "/preferences")

def switchAccount():
    keys = ['Google', 'GitHub', 'Email']
    sublime.active_window().show_quick_panel(keys, switchAccountHandler)

def switchAccountHandler(idx):
    if (idx is not None and idx >= 0):
        setItem("switching_account", True)
        if (idx == 0):
            launchLoginUrl('google')
        elif (idx == 1):
            launchLoginUrl('github')
        else:
            launchLoginUrl('software')
