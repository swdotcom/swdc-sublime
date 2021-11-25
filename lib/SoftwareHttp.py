import http
import json
import sublime_plugin, sublime
from .SoftwareSettings import *
from .CommonUtil import *
from .Logger import *

USER_AGENT = 'Code Time Sublime Plugin'
lastMsg = None
windowView = None
version = None

def toggleStatus():
    global lastMsg
    showStatusVal = getValue("show_code_time_status", True)
    setValue("show_code_time_status", not showStatusVal)

    # Change the setting before displaying the new one
    if (not showStatusVal is True):
        showStatus(lastMsg)
    else:
        # show clock icon unicode
        showStatus("🕒")
    sublime.active_window().run_command('open_tree_view')

# update the status bar message
def showStatus(msg):
    global lastMsg
    try:
        lastMsg = msg

        if (sublime.active_window() is None or sublime.active_window().active_view() is None):
            return

        showStatusVal = getValue("show_code_time_status", True)

        if (showStatusVal is False):
            msg = "🕒"
        elif (msg is None):
            msg = "Code Time"

        sublime.active_window().active_view().set_status('software.com', msg)
    except RuntimeError:
        print(msg)

def isResponseOk(response):
    if (response is not None and int(response.status) < 300):
        return True
    return False

def isUnauthenticated(response):
    if (response is not None and int(response.status) == 401):
        return True
    return False

# send the request.
def requestIt(method, api, payload, jwt):

    api_endpoint = getApiEndpoint()
    telemetry = getValue("software_telemetry_on", True)

    if (telemetry is False):
        # logIt("Code Time: telemetry is currently paused. To see your coding data in Software.com, enable software telemetry.")
        return None

    # try to update kpm data.
    try:
        headers = {'Content-Type': 'application/json', 'User-Agent': USER_AGENT}
        connection = None
        # create the connection
        if ('localhost' in api_endpoint):
            connection = http.client.HTTPConnection(api_endpoint)
        else:
            # logIt("Creating HTTPS Connection")
            connection = http.client.HTTPSConnection(api_endpoint)

        if (jwt is not None):
            headers['Authorization'] = jwt

        # make the request
        if (payload is None):
            payload = json.dumps({})

        headers['X-SWDC-Plugin-Id'] = getPluginId()
        headers['X-SWDC-Plugin-Name'] = getPluginName()
        headers['X-SWDC-Plugin-Version'] = getVersion()
        headers['X-SWDC-Plugin-OS'] = getOs()
        headers['X-SWDC-Plugin-TZ'] = getTimezone()
        headers['X-SWDC-Plugin-Offset'] = int(float(getUtcOffset() / 60))

        # send the request
        connection.request(method, api, payload.encode('utf-8'), headers)

        response = connection.getresponse()
        return response
    except Exception as ex:
        print("Code Time: Response Error for " + api + ": %s" % ex)
        return None

def fetchReleaseTag():
    # fetch the latest release tag
    try:
        connection = http.client.HTTPSConnection("api.github.com")

        headers = {'Content-Type': 'application/json', 'User-Agent': USER_AGENT}
        connection.request("GET", "/repos/swdotcom/swdc-sublime/releases/latest", {}, headers)

        response = connection.getresponse()
        return response
    except Exception as ex:
        print("Code Time: Response Error fetching release tag: %s" % ex)
        return getValue("plugin_version", "2.4.2")

def getVersion():
    global version
    if (version is not None and version != "current"):
        return version

    # fetch from github (None will be returned if there's an exception)
    releaseInfo = fetchReleaseTag()

    version = "current"
    if (releaseInfo is not None):
        releaseInfoStr = releaseInfo.read().decode('utf-8')
        try:
            releaseInfoObj = json.loads(releaseInfoStr)
            version = releaseInfoObj.get("tag_name", "current")
        except Exception as ex:
            print("Code Time: Unable to fetch the plugin version: %s" % ex)

    print("Plugin version: %s" % version)

    return version

def createAnonymousUser():
    jwt = getItem("jwt")
    if (jwt is None):
        plugin_uuid = getPluginUuid()
        username = getOsUsername()
        timezone = getTimezone()
        hostname = getHostname()
        auth_callback_state = getAuthCallbackState()

        payload = {}
        payload["username"] = username
        payload["timezone"] = timezone
        payload["hostname"] = hostname
        payload["plugin_uuid"] = plugin_uuid
        payload["auth_callback_state"] = auth_callback_state

        api = "/plugins/onboard"
        try:
            response = requestIt('POST', api, json.dumps(payload), None)
            if (response is not None and isResponseOk(response)):
                try:
                    responseObj = json.loads(response.read().decode('utf-8'))
                    jwt = responseObj.get("jwt", None)
                    if jwt is not None:
                        logIt("created anonymous user with jwt %s " % jwt)
                        setItem("jwt", jwt)
                        setItem("name", None)
                        setItem("switching_account", False)
                        setAuthCallbackState(None)
                        return jwt
                    else:
                        logIt("Code Time: Unable to complete account onboard")
                except Exception as ex:
                    logIt("Code Time: Unable to retrieve plugin accounts response: %s" % ex)
        except Exception as ex:
            logIt("Code Time: Unable to complete anonymous user creation: %s" % ex)
    return None

def getUser():
    jwt = getItem("jwt")
    if (jwt):
        api = "/users/me"
        response = requestIt("GET", api, None, jwt)
        if (isResponseOk(response)):
            try:
                responseObj = json.loads(response.read().decode('utf-8'))
                user = responseObj.get("data", None)
                return user
            except Exception as ex:
                logIt("Code Time: Unable to retrieve user: %s" % ex)
    return None

