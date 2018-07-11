# Copyright (c) 2018 by Software.com

import os
import json

VERSION = '0.1.6'
USER_AGENT = 'Software.com Sublime Plugin v' + VERSION

# fetch a value from the .software/sesion.json file
def getItem(key):
    jsonObj = getSoftwareSessionAsJson()

    # return a default of None if key isn't found
    val = jsonObj.get(key, None)

    return val

def setItem(key, value):
    jsonObj = getSoftwareSessionAsJson()
    jsonObj[key] = value

    content = json.dumps(jsonObj)

    sessionFile = getSoftwareSessionFile()
    with open(sessionFile, 'w') as f:
        f.write(content)

def storePayload(payload):
    # append payload to software data store file
    dataStoreFile = getSoftwareDataStoreFile()

    with open(dataStoreFile, "a") as dsFile:
        dsFile.write(payload + "\n")

def getSoftwareSessionAsJson():
    data = None

    sessionFile = getSoftwareSessionFile()
    if (os.path.isfile(sessionFile)):
        content = open(sessionFile).read()

        if (content is not None):
            # json parse the content
            data = json.loads(content)

    if (data is not None):
        return data

    return dict()

def getSoftwareSessionFile():
    file = getSoftwareDir()
    if (isWindows()):
        file += "\\session.json"
    else:
        file += "/session.json"
    return file

def getSoftwareDataStoreFile():
    file = getSoftwareDir()
    if (isWindows()):
        file += "\\data.json"
    else:
        file += "/data.json"
    return file

def getSoftwareDir():
    softwareDataDir = getHomeDir()
    if (isWindows()):
        softwareDataDir += "\\.software"
    else:
        softwareDataDir += "/.software"

    if not os.path.exists(softwareDataDir):
        os.makedirs(softwareDataDir)

    return softwareDataDir

def isWindows():
    if (os.name == 'nt'):
        return True

    return False

def isMac():
    if (os.name == 'posix'):
        return True

    return False

def getHomeDir():
    return os.environ['HOME']


