import sublime 
import webbrowser
from .SoftwareUtil import *
from .SoftwareFileDataManager import *
from .SoftwareHttp import *
from .SoftwareDashboard import *
from .SoftwareSettings import *

loggedInCacheState = False 
LOGIN_LABEL = "Log in"

def isLoggedOn(serverAvailable):
    jwt = getItem("jwt")
    print('using jwt: {}'.format(jwt))
    if (serverAvailable and jwt is not None):

        user = getUser(serverAvailable)
        if (user is not None and validateEmail(user.get("email", None))):
            setItem("name", user.get("email"))
            setItem("jwt", user.get("plugin_jwt"))
            return True
        print('did not validate user')

        api = "/users/plugin/state"
        response = requestIt("GET", api, None, jwt)

        responseOk = isResponseOk(response)
        if (responseOk is True):
            try:
                responseObj = json.loads(response.read().decode('utf-8'))
                print(responseObj)
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
    global loggedInCacheState

    currentUserStatus = {}

    serverAvailable = serverIsAvailable()

    # check if they're logged in or not
    loggedOn = isLoggedOn(serverAvailable)

    setValue("logged_on", loggedOn)
    
    currentUserStatus = {}
    currentUserStatus["loggedOn"] = loggedOn

    if (loggedOn is True and loggedInCacheState != loggedOn):
        log("Code Time: Logged on")
        sendHeartbeat("STATE_CHANGE:LOGGED_IN:true")

    loggedInCacheState = loggedOn

    return currentUserStatus

def refetchUserStatusLazily(tryCountUntilFoundUser):
    print('trying {}'.format(tryCountUntilFoundUser))
    currentUserStatus = getUserStatus()
    loggedInUser = currentUserStatus.get("loggedOn", None)
    if (loggedInUser is True or tryCountUntilFoundUser <= 0):  
        print('success!') 
        updateSessionSummaryFromServer() 
        return

    # start the time
    tryCountUntilFoundUser -= 1
    t = Timer(10, refetchUserStatusLazily, [tryCountUntilFoundUser])
    t.start()

def launchLoginUrl():
    webUrl = getUrlEndpoint()
    jwt = getItem("jwt")
    webUrl += "/onboarding?token=" + jwt
    webbrowser.open(webUrl)
    refetchUserStatusLazily(20)

def getUrlEndpoint():
    return getValue("software_dashboard_url", "https://app.software.com")

def launchWebDashboardUrl():
    webUrl = getUrlEndpoint() + "/login"
    webbrowser.open(webUrl)

def showLoginPrompt():
    serverAvailable = serverIsAvailable()

    if (serverAvailable):
        # set the last update time so we don't try to ask too frequently
        infoMsg = "To see your coding data in Code Time, please log in to your account."
        clickAction = sublime.ok_cancel_dialog(infoMsg, LOGIN_LABEL)
        if (clickAction):
            # launch the login view
            launchLoginUrl()

