import sublime, sublime_plugin
from .SoftwareUtil import *
from .SoftwareRepo import *

DASHBOARD_LABEL_WIDTH = 28
DASHBOARD_VALUE_WIDTH = 36
DASHBOARD_COL_WIDTH = 21
DASHBOARD_LRG_COL_WIDTH = 38
TABLE_WIDTH = 80
MARKER_WIDTH = 4

def getProjectContributorCodeSummaryFile():
    contributorFile = getSoftwareDir(True)
    return os.path.join(contributorFile, 'ProjectContributorCodeSummary.txt')

def generateContributorSummary(projectDir):
    writeProjectContributorCommitDashboardFromGitLogs(projectDir)

    contributorFile = getProjectContributorCodeSummaryFile()
    sublime.active_window().open_file(contributorFile)

def writeProjectContributorCommitDashboardFromGitLogs(projectDir):
    userTodaysChangeStats = getTodaysCommits(projectDir)
    userYesterdaysChangeStats = getYesterdaysCommits(projectDir)
    userWeeksChangeStats = getThisWeeksCommits(projectDir)

    contributorsTodaysChangeStats = getTodaysCommits(projectDir, False)
    print(contributorsTodaysChangeStats)
    contributorsYesterdaysChangeStats = getYesterdaysCommits(projectDir, False)
    print(contributorsYesterdaysChangeStats)
    contributorsWeeksChangeStats = getThisWeeksCommits(projectDir, False)
    print(contributorsWeeksChangeStats)

    dashboardContent = ''

    now = round(timeModule.time())
    formattedDate = datetime.fromtimestamp(now).strftime('%a, %b %d %I:%M%p').replace(' 0', ' ')
    dashboarContent = getTableHeader('PROJECT SUMMARY', ' (Last updated on {})'.format(formattedDate))

    dashboardContent += '\n\n'
    dashboardContent += 'Project: {}'.format(projectDir)
    dashboardContent += '\n\n'

    # TODAY
    projectDate = datetime.fromtimestamp(now).strftime('%b %d, %Y')
    dashboardContent += getRightAlignedTableHeader('Today ({})'.format(projectDate))
    dashboardContent += getColumnHeaders(['Metric', 'You', 'All Contributors'])

    summary = { 
        "activity": userTodaysChangeStats,
        "contributorActivity": contributorsTodaysChangeStats
    }

    dashboardContent += getRowNumberData(summary, 'Commits', 'commitCount')
    dashboardContent += getRowNumberData(summary, 'Files changed', 'fileCount')
    dashboardContent += getRowNumberData(summary, 'Insertions', 'insertions')
    dashboardContent += getRowNumberData(summary, 'Deletions', 'deletions')
    dashboardContent += '\n'

    # YESTERDAY
    startDate = datetime.fromtimestamp(getYesterday()['start']).strftime('%b %d, %Y')
    dashboardContent += getRightAlignedTableHeader('Yesterday ({})'.format(startDate))
    dashboardContent += getColumnHeaders(['Metric', 'You', 'All Contributors'])
    
    summary = {
        "activity": userYesterdaysChangeStats,
        "contributorActivity": contributorsYesterdaysChangeStats
    }
    dashboardContent += getRowNumberData(summary, 'Commits', 'commitCount')
    dashboardContent += getRowNumberData(summary, 'Files changed', 'fileCount')
    dashboardContent += getRowNumberData(summary, 'Insertions', 'insertions')
    dashboardContent += getRowNumberData(summary, 'Deletions', 'deletions')
    dashboardContent += '\n'

    # THIS WEEK
    startDate = datetime.fromtimestamp(getThisWeek()['start']).strftime('%b %d, %Y')
    dashboardContent += getRightAlignedTableHeader('This week ({} to {})'.format(startDate, projectDate))
    dashboardContent += getColumnHeaders(['Metric', 'You', 'All Contributors'])

    summary = {
        "activity": userWeeksChangeStats,
        "contributorActivity": contributorsWeeksChangeStats
    }
    dashboardContent += getRowNumberData(summary, 'Commits', 'commitCount')
    dashboardContent += getRowNumberData(summary, 'Files changed', 'fileCount')
    dashboardContent += getRowNumberData(summary, 'Insertions', 'insertions')
    dashboardContent += getRowNumberData(summary, 'Deletions', 'deletions')
    dashboardContent += '\n'

    contributorFile = getProjectContributorCodeSummaryFile()
    with open(contributorFile, 'w') as f:
        f.write(dashboardContent)

def getRowNumberData(summary, title, attribute):
    userFilesChanged = '0'
    if summary['activity'][attribute]:
        userFilesChanged = formatNumber(summary['activity'][attribute])
    
    contribFilesChanged = '0'
    if summary['contributorActivity'][attribute]:
        contribFilesChanged = formatNumber(summary['contributorActivity'][attribute])
    
    return getRowLabels([title, userFilesChanged, contribFilesChanged])

def getDashboardBottomBorder():
    content = ''
    dashLen = DASHBOARD_LABEL_WIDTH + DASHBOARD_VALUE_WIDTH
    content += '-' * dashLen
    content += '\n\n'
    return content 

def getSectionHeader(label):
    content = '{}\n'.format(label)
    dashLen = DASHBOARD_LABEL_WIDTH - DASHBOARD_VALUE_WIDTH
    content += '-' * dashLen
    content += '\n'
    return content 

def formatRightAlignedTableLabel(label, colWidth):
    spacesRequired = colWidth - len(label)
    spaces = ' ' * spacesRequired
    
    return '{}{}'.format(spaces, label)

def getTableHeader(leftLabel, rightLabel, isFullTable=True):
    fullLen = TABLE_WIDTH - DASHBOARD_COL_WIDTH if not isFullTable else TABLE_WIDTH
    spacesRequired = fullLen - len(leftLabel) - len(rightLabel)
    spaces = ' ' * spacesRequired
    
    return '{}{}{}'.format(leftLabel, spaces, rightLabel)

def getRightAlignedTableHeader(label):
    content = '{}\n'.format(formatRightAlignedTableLabel(label, TABLE_WIDTH))
    for i in range(TABLE_WIDTH):
        content += '-'
    content += '\n'
    return content 

def getSpaces(spacesRequired):
    return ' ' * spacesRequired

def getRowLabels(labels):
    content = ''
    spacesRequired = 0
    for i in range(len(labels)):
        label = labels[i]
        if i == 0:
            content += label 
            spacesRequired = DASHBOARD_COL_WIDTH - len(content) - 1
            content += ' ' * spacesRequired
            content += ':'
        elif i == 1:
            spacesRequired = DASHBOARD_LRG_COL_WIDTH + DASHBOARD_COL_WIDTH - len(content) - len(label) - 1
            content += ' ' * spacesRequired
            content += label + ' '
        else:
            spacesRequired = DASHBOARD_COL_WIDTH - len(label) - 2
            content += '| '
            content += ' ' * spacesRequired
            content += label 
    
    content += '\n'
    return content 

def getColumnHeaders(labels):
    content = ''
    spacesRequired = 0
    for i in range(len(labels)):
        label = labels[i]
        if i == 0:
            content += label 
        elif i == 1:
            spacesRequired = DASHBOARD_LRG_COL_WIDTH + DASHBOARD_COL_WIDTH - len(content) - len(label) - 1
            content += ' ' * spacesRequired
            content += label + ' '
        else:
            spacesRequired = DASHBOARD_COL_WIDTH - len(label) - 2
            content += '| '
            content += ' ' * spacesRequired
            content += label 
    
    content += '\n'
    content += '-' * TABLE_WIDTH
    content += '\n'
    return content 