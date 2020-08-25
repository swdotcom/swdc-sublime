import sublime
import webbrowser
import urllib
import re
from .SoftwareUtil import *
from .SoftwareFileDataManager import *
from .SoftwareHttp import *
from .SoftwareDashboard import *
from .SoftwareSettings import *
from .SoftwarePayload import *
from .CommonUtil import *

loggedInCacheState = False
LOGIN_LABEL = "Log in"

def isLoggedOn():
    print("calling isLoggedOn")
    jwt = getItem("jwt")
    if (jwt is not None):

        user = getUser()
        if (user is not None and validateEmail(user.get("email", None))):
            setItem("name", user.get("email"))
            setItem("jwt", user.get("plugin_jwt"))
            return True

        api = "/users/plugin/state"
        response = requestIt("GET", api, None, jwt)

        responseOk = isResponseOk(response)
        if (responseOk is True):
            try:
                responseObj = json.loads(response.read().decode('utf-8'))
                state = responseObj.get("state", None)
                if (state is not None and state == "OK"):
                    email = responseObj.get("email", None)
                    setItem("name", email)
                    pluginJwt = responseObj.get("jwt", None)
                    if (pluginJwt is not None and pluginJwt != jwt):
                        setItem("jwt", pluginJwt)

                    # state is ok, return True
                    return True
                elif (state is not None and state == "NOT_FOUND"):
                    setItem("jwt", None)

            except Exception as ex:
                log("Code Time: Unable to retrieve logged on response: %s" % ex)

    setItem("name", None)
    return False

def getUserStatus():
    print("calling getUserStatus")
    global loggedInCacheState

    currentUserStatus = {}

    # check if they're logged in or not
    loggedOn = isLoggedOn()

    setValue("logged_on", loggedOn)

    currentUserStatus = {}
    currentUserStatus["loggedOn"] = loggedOn

    if (loggedOn is True and loggedInCacheState != loggedOn):
        log("Code Time: Logged on")
        sendHeartbeat("STATE_CHANGE:LOGGED_IN:true")

    loggedInCacheState = loggedOn

    return currentUserStatus

def refetchUserStatusLazily(tryCountUntilFoundUser):
    currentUserStatus = getUserStatus()
    loggedInUser = currentUserStatus.get("loggedOn", None)
    if (loggedInUser is True or tryCountUntilFoundUser <= 0):
        sendOfflineData()
        return

    # start the time
    tryCountUntilFoundUser -= 1
    t = Timer(10, refetchUserStatusLazily, [tryCountUntilFoundUser])
    t.start()

def launchLoginUrl(loginType):
    webbrowser.open(getLoginUrl(loginType))
    refetchUserStatusLazily(40)

def getUrlEndpoint():
    return getValue("software_dashboard_url", "https://app.software.com")

def getLoginUrl(loginType):
    jwt = getItem('jwt')
    encodedJwt = urllib.parse.quote_plus(jwt)
    host = getValue("software_api_endpoint", "api.software.com")
    loginUrl = None

    scheme = "https"
    if bool(re.match("localhost", host)):
        scheme = "http"

    api_host = scheme + "://" + host

    setItem('authType', loginType)
    if (loginType == 'software'):
        loginUrl = '{}/email-signup?token={}&plugin=codetime&auth=software'.format(getUrlEndpoint(), encodedJwt)
    elif (loginType == 'github'):
        loginUrl = '{}/auth/github?token={}&plugin=codetime&redirect={}'.format(api_host, encodedJwt, getUrlEndpoint())
    elif (loginType == 'google'):
        loginUrl = '{}/auth/google?token={}&plugin=codetime&redirect={}'.format(api_host, encodedJwt, getUrlEndpoint())
    else:
        print('Login type error: Type was {}, defaulting...'.format(loginType))
        loginUrl = '{}/email-signup?token={}&plugin=codetime&auth=software'.format(getUrlEndpoint(), encodedJwt)

    return loginUrl

def launchWebDashboardUrl():
    jwt = getItem('jwt')
    webUrl = getUrlEndpoint() + '?token=' + jwt
    webbrowser.open(webUrl)
