import sublime, sublime_plugin
from .SoftwareUtil import *
from .SoftwareRepo import *

DASHBOARD_LABEL_WIDTH = 28
DASHBOARD_VALUE_WIDTH = 36
DASHBOARD_COL_WIDTH = 21
DASHBOARD_LRG_COL_WIDTH = 38
TABLE_WIDTH = 80
MARKER_WIDTH = 4



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