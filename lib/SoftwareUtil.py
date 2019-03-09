# Copyright (c) 2018 by Software.com
from threading import Thread, Timer, Event
import os
import json
import time
import sublime_plugin, sublime
import sys
import uuid
import platform
import re, uuid
import webbrowser
from urllib.parse import quote_plus
from subprocess import Popen, PIPE
from .SoftwareHttp import *


VERSION = '0.6.7'
PLUGIN_ID = 1
SETTINGS_FILE = 'Software.sublime_settings'
SETTINGS = {}

runningResourceCmd = False
currentUserStatus = None
lastRegisterUserCheck = 0


# log the message
def log(message):

    software_settings = sublime.load_settings("Software.sublime_settings")
    if (software_settings.get("software_logging_on", True)):
        print(message)

def clearUserStatusCache():
    global currentUserStatus
    global lastRegisterUserCheck
    currentUserStatus = None
    lastRegisterUserCheck = 0


# fetch a value from the .software/sesion.json file
def getItem(key):
    jsonObj = getSoftwareSessionAsJson()

    # return a default of None if key isn't found
    val = jsonObj.get(key, None)

    return val

# get an item from the session json file
def setItem(key, value):
    jsonObj = getSoftwareSessionAsJson()
    jsonObj[key] = value

    content = json.dumps(jsonObj)

    sessionFile = getSoftwareSessionFile()
    with open(sessionFile, 'w') as f:
        f.write(content)

# store the payload offline
def storePayload(payload):
    # append payload to software data store file
    dataStoreFile = getSoftwareDataStoreFile()

    with open(dataStoreFile, "a") as dsFile:
        dsFile.write(payload + "\n")

def getSoftwareSessionAsJson():
    try:
        with open(getSoftwareSessionFile()) as sessionFile:
            return json.load(sessionFile)
    except Exception:
        return {}

def getSoftwareSessionFile():
    file = getSoftwareDir()
    return os.path.join(file, 'session.json')

def getSoftwareDataStoreFile():
    file = getSoftwareDir()
    return os.path.join(file, 'data.json')

def getSoftwareDir():
    softwareDataDir = os.path.expanduser('~')
    softwareDataDir = os.path.join(softwareDataDir, '.software')
    os.makedirs(softwareDataDir, exist_ok=True)
    return softwareDataDir

def getDashboardFile():
    file = getSoftwareDir()
    return os.path.join(file, 'CodeTime.txt')

# execute the applescript command
def runComand(cmd, args):
    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(cmd)
    return stdout.decode('utf-8').strip()

def getItunesTrackState():
    script = '''
        tell application "iTunes" to get player state
        '''
    try:
        cmd = script.encode('latin-1')
        result = runComand(cmd, ['osascript', '-'])
        return result
    except Exception as e:
        log("exception getting track state: %s " % e)
        # no music found playing
        return "stopped"

def getSpotifyTrackState():
    script = '''
        tell application "Spotify" to get player state
        '''
    try:
        cmd = script.encode('latin-1')
        result = runComand(cmd, ['osascript', '-'])
        return result
    except Exception as e:
        log("exception getting track state: %s " % e)
        # no music found playing
        return "stopped"


# get the current track playing (spotify or itunes)
def getTrackInfo():
    if sys.platform == "darwin":
        return getMacTrackInfo()
    elif sys.platform == "win32":
        # not supported on other platforms yet
        return getWinTrackInfo()
    else:
        # linux not supported yet
        return {}

# windows
def getWinTrackInfo():
    # not supported on other platforms yet
    return {}

# OS X
def getMacTrackInfo():
    script = '''
        on buildItunesRecord(appState)
            tell application "iTunes"
                set track_artist to artist of current track
                set track_name to name of current track
                set track_genre to genre of current track
                set track_id to database ID of current track
                set track_duration to duration of current track
                set json to "type='itunes';genre='" & track_genre & "';artist='" & track_artist & "';id='" & track_id & "';name='" & track_name & "';state='playing';duration='" & track_duration & "'"
            end tell
            return json
        end buildItunesRecord

        on buildSpotifyRecord(appState)
            tell application "Spotify"
                set track_artist to artist of current track
                set track_name to name of current track
                set track_duration to duration of current track
                set track_id to id of current track
                set track_duration to duration of current track
                set json to "type='spotify';genre='';artist='" & track_artist & "';id='" & track_id & "';name='" & track_name & "';state='playing';duration='" & track_duration & "'"
            end tell
            return json
        end buildSpotifyRecord

        try
            if application "Spotify" is running and application "iTunes" is not running then
                tell application "Spotify" to set spotifyState to (player state as text)
                -- spotify is running and itunes is not
                if (spotifyState is "paused" or spotifyState is "playing") then
                    set jsonRecord to buildSpotifyRecord(spotifyState)
                else
                    set jsonRecord to {}
                end if
            else if application "Spotify" is running and application "iTunes" is running then
                tell application "Spotify" to set spotifyState to (player state as text)
                tell application "iTunes" to set itunesState to (player state as text)
                -- both are running but use spotify as a higher priority
                if spotifyState is "playing" then
                    set jsonRecord to buildSpotifyRecord(spotifyState)
                else if itunesState is "playing" then
                    set jsonRecord to buildItunesRecord(itunesState)
                else if spotifyState is "paused" then
                    set jsonRecord to buildSpotifyRecord(spotifyState)
                else
                    set jsonRecord to {}
                end if
            else if application "iTunes" is running and application "Spotify" is not running then
                tell application "iTunes" to set itunesState to (player state as text)
                set jsonRecord to buildItunesRecord(itunesState)
            else
                set jsonRecord to {}
            end if
            return jsonRecord
        on error
            return {}
        end try
    '''
    try:
        cmd = script.encode('latin-1')
        result = runComand(cmd, ['osascript', '-'])
        result = result.strip('\r\n')
        result = result.replace('"', '')
        result = result.replace('\'', '')

        if (result):
            trackInfo = dict(item.strip().split("=") for item in result.strip().split(";"))
            return trackInfo
        else:
            return {}
    except Exception as e:
        log("exception getting track: %s " % e)
        # no music found playing
        return {}

def runResourceCmd(cmdArgs, rootDir):
    if sys.platform == "darwin": # OS X
        runningResourceCmd = True
        p = Popen(cmdArgs, cwd = rootDir, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        stdout = stdout.decode('utf-8').strip()
        if (stdout):
            stdout = stdout.strip('\r\n')
            return stdout
        else:
            return ""
    else:
        return ""


def getResourceInfo(rootDir):
    try:
        resourceInfo = {}
        tag = runResourceCmd(['git', 'describe', '--all'], rootDir)

        if (tag):
            resourceInfo['tag'] = tag
        identifier = runResourceCmd(['git', 'config', '--get', 'remote.origin.url'], rootDir)

        if (identifier):
            resourceInfo['identifier'] = identifier
        branch = runResourceCmd(['git', 'symbolic-ref', '--short', 'HEAD'], rootDir)

        if (branch):
            resourceInfo['branch'] = branch
        email = runResourceCmd(['git', 'config', 'user.email'], rootDir)

        if (email):
            resourceInfo['email'] = email
            
        if (resourceInfo.get("identifier") is not None):
            return resourceInfo
        else:
            return {}
    except Exception as e:
        return {}

def checkOnline():
    # non-authenticated ping, no need to set the Authorization header
    response = requestIt("GET", "/ping", None, getItem("jwt"))
    if (isResponsOk(response)):
        return True
    else:
        return False

def getIdentity():
    homedir = os.path.expanduser('~')

    # strip out the username from the homedir
    username = os.path.basename(homedir)

    identityId = (':'.join(re.findall('..', '%012x' % uuid.getnode())))

    parts = []
    if (username):
        parts.append(username)
    if (identityId):
        parts.append(identityId)

    identityId = '_'.join(parts)

    return identityId

def refetchUserStatusLazily(tryCountUntilFoundUser):
    currentUserStatus = getUserStatus()
    loggedInUser = currentUserStatus.get("loggedInUser", None)
    if (loggedInUser is not None or tryCountUntilFoundUser <= 0):
        return

    # start the time
    tryCountUntilFoundUser -= 1
    t = Timer(10, refetchUserStatusLazily, [tryCountUntilFoundUser])
    t.start()

def launchLoginUrl():
    software_settings = sublime.load_settings("Software.sublime_settings")
    webUrl = software_settings.get("software_dashboard_url", "https://app.software.com")
    identityId = getIdentity()
    webUrl += "/login?addr=" + identityId
    webbrowser.open(webUrl)
    refetchUserStatusLazily(6)

def launchSignupUrl():
    software_settings = sublime.load_settings("Software.sublime_settings")
    webUrl = software_settings.get("software_dashboard_url", "https://app.software.com")
    identityId = getIdentity()
    webUrl += "/onboarding?addr=" + identityId
    webbrowser.open(webUrl)
    refetchUserStatusLazily(12)

def launchWebDashboardUrl():
    software_settings = sublime.load_settings("Software.sublime_settings")
    webUrl = software_settings.get("software_dashboard_url", "https://app.software.com")
    webbrowser.open(webUrl)


def fetchCodeTimeMetrics():
    api = '/dashboard'
    response = requestIt("GET", api, None, getItem("jwt"))
    content = response.read().decode('utf-8')
    file = getDashboardFile()
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

def launchCodeTimeMetrics():
    fetchCodeTimeMetrics()
    file = getDashboardFile()
    sublime.active_window().open_file(file)

def pluginLogout():
    api = "/users/plugin/logout"
    response = requestIt("POST", api, None, getItem("jwt"))

    clearUserStatusCache()
    getUserStatus()

def getAppJwt():
    setItem("app_jwt", None)
    serverAvailable = checkOnline()
    if (serverAvailable):
        identityId = getIdentity()
        if (identityId):
            encodedIdentityId = quote_plus(identityId) 
            api = "/data/token?addr=" + identityId
            response = requestIt("GET", api, None, None)
            if (response is not None):
                responseObjStr = response.read().decode('utf-8')
                try:
                    responseObj = json.loads(responseObjStr)
                    appJwt = responseObj.get("jwt", None)
                    if (appJwt is not None):
                        return appJwt
                except Exception as ex:
                    log("Code Time: Unable to retrieve app token: %s" % ex)
    return None

# crate a uuid token to establish a connection
def createToken():
    # return os.urandom(16).encode('hex')
    uid = uuid.uuid4()
    return uid.hex

def createAnonymousUser(identityId):
    appJwt = getAppJwt()
    serverAvailable = checkOnline()

    if (serverAvailable and appJwt):
        plugin_token = getItem("token")
        if (plugin_token is None):
            plugin_token = createToken()
            setItem("token", plugin_token)

        email = identityId

        timezone = ""
        try:
            timezone = time.strftime('%Z')
        except Exception:
            timezone = time.tzname[0]

        payload = {}
        payload["email"] = email
        payload["plugin_token"] = plugin_token
        payload["timezone"] = timezone
        encodedIdentityId = quote_plus(identityId)

        api = "/data/onboard?addr=" + identityId
        try:
            response = requestIt("POST", api, json.dumps(payload), appJwt)

            if (response is not None and isResponsOk(response)):
                try:
                    responseObj = json.loads(response.read().decode('utf-8'))
                    jwt = responseObj.get("jwt", None)
                    setItem("jwt", jwt)
                    user = responseObj.get("user", None)
                    setItem("user", user)
                    setItem("sublime_lastUpdateTime", round(time.time()))
                    return None
                except Exception as ex:
                    log("Code Time: Unable to retrieve plugin accounts response: %s" % ex)
        except Exception as ex:
            log("Code Time: Unable to complete anonymous user creation: %s" % ex)


def getAuthenticatedPluginAccounts(identityId):
    jwt = getItem("jwt")
    encodedIdentityId = quote_plus(identityId) 
    serverAvailable = checkOnline()
    tokenStr = "token=" + identityId
    if (jwt and serverAvailable and identityId):
        api = "/users/plugin/accounts?" + tokenStr
        response = requestIt("GET", api, None, getItem("jwt"))
        if (response is not None and isResponsOk(response)):
            try:
                responseObj = json.loads(response.read().decode('utf-8'))
                return responseObj.get("users", None)
            except Exception as ex:
                log("Code Time: Unable to retrieve plugin accounts response: %s" % ex)

    return None

def getLoggedInUser(identityId, authAccounts):
    if (authAccounts):
        for account in authAccounts:
            userEmail = account.get("email", "")
            userMacAddr = account.get("mac_addr", "")
            userMacAddrShare = account.get("mac_addr_share", "")
            if (userEmail != userMacAddr and userEmail != identityId and userEmail != userMacAddrShare
                and userMacAddr == identityId):
                return account

    return None


def isMacEmail(email):
    if (email is None):
        return False
    macMatch = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', email, re.I)
    macPairMatch = re.search(r'([a-fA-F0-9]{2}[:\\.-]?){5}[a-fA-F0-9]{2}', email, re.I)
    macTripleMatch = re.search(r'([a-fA-F0-9]{3}[:\\.-]?){3}[a-fA-F0-9]{3}', email, re.I)
    if (macMatch is not None
        or macPairMatch is not None
        or macTripleMatch is not None):
        return True
    return False

def hasAnyUserAccounts(identityId, authAccounts):
    if (authAccounts):
        for account in authAccounts:
            userEmail = account.get("email", None)
            if (isMacEmail(userEmail) is False):
                return True

    return False

def getAnonymousUser(identityId, authAccounts):
    if (authAccounts):
        for account in authAccounts:
            userEmail = account.get("email", None)
            if (isMacEmail(userEmail) is True):
                return True

    return False

def updateSessionUserInfo(user):
    userObj = {}
    userObj["id"] = user.get("id")
    setItem("jwt", user.get("plugin_jwt"))
    setItem("user", userObj)
    setItem("sublime_lastUpdateTime", round(time.time()))

def getUserStatus():
    global SETTINGS
    global currentUserStatus
    global lastRegisterUserCheck

    SETTINGS = sublime.load_settings(SETTINGS_FILE)
    
    nowTime = round(time.time())

    if (currentUserStatus is not None and lastRegisterUserCheck is not None):
        if (nowTime - lastRegisterUserCheck <= 5):
            return currentUserStatus

    identityId = getIdentity()
    
    authAccounts = getAuthenticatedPluginAccounts(identityId)

    loggedInUser = getLoggedInUser(identityId, authAccounts)
    anonUser = getAnonymousUser(identityId, authAccounts)
    if (anonUser is None):
        # create the anonymous user
        createAnonymousUser(identityId)
        authAccounts = getAuthenticatedPluginAccounts(identityId)
        anonUser = getAnonymousUser(identityId, authAccounts)

    email = None

    if (loggedInUser is not None):
        updateSessionUserInfo(loggedInUser)
        email = loggedInUser.get("email")
        SETTINGS.set("logged_on", True)
    elif (anonUser is not None):
        updateSessionUserInfo(anonUser)
        SETTINGS.set("logged_on", False)

    hasUserAccounts = hasAnyUserAccounts(identityId, authAccounts)

    currentUserStatus = {}

    currentUserStatus["loggedInUser"] = loggedInUser
    currentUserStatus["hasUserAccounts"] = hasUserAccounts
    currentUserStatus["email"] = email

    lastRegisterUserCheck = round(time.time())
    return currentUserStatus



