def TimeData():
    template = {
        "timestamp": 0,
        "timestamp_local": 0,
        "editor_seconds": 0,
        "session_seconds": 0,
        "file_seconds": 0,
        "day": ''
    }
    return template 

def SessionSummary():
    template = {
        "currentDayMinutes": 0,
        "currentDayKeystrokes": 0,
        "currentDayKpm": 0,
        "currentDayLinesAdded": 0,
        "currentDayLinesRemoved": 0,
        "averageDailyMinutes": 0,
        "averageDailyKeystrokes": 0,
        "averageDailyKpm": 0,
        "averageLinesAdded": 0,
        "averageLinesRemoved": 0,
        "timePercent": 0,
        "volumePercent": 0,
        "velocityPercent": 0,
        "liveshareMinutes": 0,
        "latestPayloadTimestampEndUtc": 0,
        "latestPayloadTimestamp": 0,
        "lastUpdatedToday": False,
        "currentSessionGoalPercent": 0,
        "inFlow": False,
        "dailyMinutesGoal": 0,
        "globalAverageSeconds": 0,
        "globalAverageDailyMinutes": 0,
        "globalAverageDailyKeystrokes": 0,
        "globalAverageLinesAdded": 0,
        "globalAverageLinesRemoved": 0,
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