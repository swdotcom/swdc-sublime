def TimeData():
    template = {
        "timestamp": 0,
        "timestamp_local": 0,
        "editor_seconds": 0,
        "session_seconds": 0,
        "file_seconds": 0,
        "day": '',
        "project": Project()
    }
    return template 

def SessionSummary():
    template = {
        "currentDayMinutes": 0,
        "averageDailyMinutes": 0,
    }
    return template

def KeystrokeAggregate():
    template = {
        "add": 0,
        "close": 0,
        "delete": 0,
        "linesAdded": 0,
        "linesRemoved": 0,
        "open": 0,
        "paste": 0,
        "keystrokes": 0,
        "directory": ''
    }
    return template 

def CommitChangeStats():
    template = {
        "insertions": 0,
        "deletions": 0,
        "fileCount": 0,
        "commitCount": 0
    }
    return template 

def Project():
    template = {
        "directory": '',
        "name": '',
        "identifier": '',
        "resource": Resource()
    }
    return template 

def Resource():
    template = {
        "identifier": '',
        "branch": '',
        "tag": '',
        "email": ''
    }
    return template 

def ContributorMember():
    template = {
        "name": '',
        "email": '',
        "identifier": ''
    }
    return template 

def CodeTimeSummary():
    template = {
        "activeCodeTimeMinutes": 0,
        "codeTimeMinutes": 0,
        "fileTimeMinutes": 0
    }
    return template 