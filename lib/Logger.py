from .SoftwareSettings import *

def logIt(message):
    if (getValue("software_logging_on", True)):
        print(message)