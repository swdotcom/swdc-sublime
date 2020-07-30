import os
import sys
from .SoftwareHttp import *

print(sys.version)

# Add vendor directory to module search path
vendor_dir = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'vendor'))
sys.path.append(vendor_dir)

from snowplow_tracker import Subject, Tracker, Emitter

def initialize_tracker():
	response = requestIt("GET", '/plugins/config', None, None)
	config = json.loads(response.read().decode('utf-8'))
	e = Emitter(config['tracker_api'])
	t = Tracker(e)


