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
from .SlackHttp import *
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

        if (is_integration is False):
            if (user_jwt is not None):
                setItem("jwt", user.get("plugin_jwt"))

            if (registered == 1):
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
            log("Code Time: Unable to retrieve user from plugin state: %s" % ex)
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
        clearTimeDataSummary()

        # clear the integrations
        syncIntegrations([])

        # fetch user's integrations
        updateSlackIntegrationsFromUser(userState["user"])

        updateSessionSummaryFromServer(True)


def launchLoginUrl(loginType = "software", switching_account = True):
    webbrowser.open(getLoginUrl(loginType, switching_account))
    refetchUserStatusLazily(40)

def getLoginUrl(loginType = "software", switching_account=True):
    loginType = loginType.lower()

    auth_callback_state = str(uuid.uuid4())
    setAuthCallbackState(auth_callback_state)

    loginUrl = ""

    obj = {
        "plugin": "codetime",
        "plugin_uuid": getPluginUuid(),
        "pluginVersion": getVersion(),
        "plugin_id": getPluginId(),
        "auth_callback_state": auth_callback_state
    }

    apiEndpointUrl = "https://" + getApiEndpoint()

    if (loginType == "github"):
        obj["redirect"] = getWebUrl()
        loginUrl = apiEndpointUrl + "/auth/github"
    elif (loginType == "google"):
        obj["redirect"] = getWebUrl()
        loginUrl = apiEndpointUrl + "/auth/google"
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
    jwt = getItem('jwt')
    webUrl = getWebUrl() + '?token=' + jwt
    webbrowser.open(webUrl)

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

def updateSlackIntegrationsFromUser(user):
    foundNewIntegration = False

    if (user is not None and user["integrations"] is not None):
        integrations = user["integrations"]

        existingIntegrations = getIntegrations()
        for i in range(len(integrations)):
            integration = integrations[i]

            if (integration["name"].lower() == 'slack'
                and integration["status"].lower() == 'active'
                and integration["access_token"] is not None):

                first = next(filter(lambda x: x["authId"] == integration["authId"], existingIntegrations), None)

                if (first is None):
                    resp = api_call('users.identity', {'token': integration["access_token"]})
                    if (resp['ok'] is True):
                        integration["team_domain"] = resp["team"]["domain"]
                        integration["team_name"] = resp["team"]["name"]
                        integration["integration_id"] = resp["user"]["id"]
                        foundNewIntegration = True
                        existingIntegrations.append(integration)
                        syncIntegrations(existingIntegrations)
                    break
    return foundNewIntegration
