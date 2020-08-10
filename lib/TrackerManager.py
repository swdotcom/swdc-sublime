import os
import sys
import json
from datetime import datetime
from .SoftwareHttp import *
from .blake2 import BLAKE2b
# Add vendor directory to module search path
# This needs to be here to load the snowplow_tracker library
vendor_dir = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'vendor'))
sys.path.append(vendor_dir)
from snowplow_tracker import Subject, Tracker, Emitter, SelfDescribingJson

cached_tracker = None
cached_hashed_values = {}
refresh_hashed_values = False
# swdc_tracker will initialize on the first use of it (editor activated event)
# and use a cached instance for every subsequent call
def swdc_tracker(use_cache = True):
	global cached_tracker

	if(cached_tracker and use_cache):
		return cached_tracker
	else:
		response = requestIt('GET', '/plugins/config', None, None)
		config = json.loads(response.read().decode('utf-8'))
		e = Emitter(config['tracker_api'])
		tracker = Tracker(e, namespace='CodeTime', app_id='swdc-sublime')
		cached_tracker = tracker
		return tracker

def tracker_enabled():
	return getValue("software_telemetry_on", True)

def track_codetime_event(**kwargs):
	if tracker_enabled():
		event_json = codetime_payload(**kwargs)
		context = build_context(**kwargs)
		swdc_tracker().track_self_describing_event(event_json, context)
		if(refresh_hashed_values):
			fetch_user_hashed_values()

def track_editor_action(**kwargs):
	if tracker_enabled():
		event_json = editor_action_payload(**kwargs)
		context = build_context(**kwargs)
		response = swdc_tracker().track_self_describing_event(event_json, context)
		if(refresh_hashed_values):
			fetch_user_hashed_values()

def track_ui_interaction(**kwargs):
	if tracker_enabled():
		event_json = ui_interaction_payload(**kwargs)
		context = build_context(**kwargs)
		swdc_tracker().track_self_describing_event(event_json, context)
		if(refresh_hashed_values):
			fetch_user_hashed_values()

def build_context(**kwargs):
	ctx = []

	if 'jwt' in kwargs:
		ctx.append(auth_payload(**kwargs))

	if 'start_time' in kwargs and 'end_time' in kwargs:
		ctx.append(codetime_payload(**kwargs))

	if 'entity' in kwargs:
		ctx.append(editor_action_payload(**kwargs))

	if 'interaction_type' in kwargs:
		ctx.append(ui_interaction_payload(**kwargs))

	if 'element_name' in kwargs and 'element_location' in kwargs:
		ctx.append(ui_element_payload(**kwargs))

	if 'project_name' in kwargs and 'project_directory' in kwargs:
		ctx.append(project_payload(**kwargs))

	if 'repo_identifier' in kwargs:
		ctx.append(repo_payload(**kwargs))

	if 'file_name' in kwargs and 'file_path' in kwargs:
		ctx.append(file_payload(**kwargs))

	if 'plugin_id' in kwargs and 'plugin_version' in kwargs:
		ctx.append(plugin_payload(**kwargs))

	return ctx

def codetime_payload(**kwargs):
	return SelfDescribingJson(
		'iglu:com.software/codetime/jsonschema/1-0-1',
		{
			'keystrokes': kwargs['keystrokes'],
			'chars_added': kwargs['chars_added'],
			'chars_deleted': kwargs['chars_deleted'],
			'chars_pasted': kwargs['chars_pasted'],
			'pastes': kwargs['pastes'],
			'lines_added': kwargs['lines_added'],
			'lines_deleted': kwargs['lines_deleted'],
			'start_time': datetime.utcfromtimestamp(int(kwargs['start_time'])).isoformat(),
			'end_time': datetime.utcfromtimestamp(int(kwargs['end_time'])).isoformat()
		}
	)

def editor_action_payload(**kwargs):
	return SelfDescribingJson(
		'iglu:com.software/editor_action/jsonschema/1-0-1',
		{
			'entity': kwargs['entity'],
			'type': kwargs['type']
		}
	)

def ui_interaction_payload(**kwargs):
	return SelfDescribingJson(
		'iglu:com.software/ui_interaction/jsonschema/1-0-0',
		{
			'interaction_type': kwargs['interaction_type']
		}
	)

def auth_payload(**kwargs):
	return SelfDescribingJson(
		'iglu:com.software/auth/jsonschema/1-0-0',
		{
			'jwt': kwargs['jwt']
    	}
    )

def file_payload(**kwargs):
	hashed_name = hash_value(kwargs['file_name'], 'file_name', kwargs['jwt'])
	hashed_path = hash_value(kwargs['file_path'], 'file_path', kwargs['jwt'])

	return SelfDescribingJson(
    	'iglu:com.software/file/jsonschema/1-0-1',
    	{
			'file_name': hashed_name,
			'file_path': hashed_path,
			'syntax': kwargs['syntax'],
			'line_count': kwargs['line_count'],
			'character_count': kwargs['character_count']
      }
    )

def plugin_payload(**kwargs):
	return SelfDescribingJson(
		'iglu:com.software/plugin/jsonschema/1-0-1',
		{
			'plugin_id': kwargs['plugin_id'],
			'plugin_version': kwargs['plugin_version'],
			'plugin_name': kwargs['plugin_name']
		}
	)

def project_payload(**kwargs):
	hashed_name = hash_value(kwargs['project_name'], "project_name", kwargs['jwt'])
	hashed_directory = hash_value(kwargs['project_directory'], "project_directory", kwargs['jwt'])

	return SelfDescribingJson(
		'iglu:com.software/project/jsonschema/1-0-0',
		{
			'project_name': hashed_name,
			'project_directory': hashed_directory
		}
	)

def repo_payload(**kwargs):
	hashed_name = hash_value(kwargs['repo_name'], 'repo_name', kwargs['jwt'])
	hashed_identifier = hash_value(kwargs['repo_identifier'], 'repo_identifier', kwargs['jwt'])
	hashed_owner_id = hash_value(kwargs['owner_id'], 'owner_id', kwargs['jwt'])
	hashed_git_branch = hash_value(kwargs['git_branch'], 'git_branch', kwargs['jwt'])
	hashed_git_tag = hash_value(kwargs['git_tag'], 'git_tag', kwargs['jwt'])

	return SelfDescribingJson(
		'iglu:com.software/repo/jsonschema/1-0-0',
		{
			'repo_identifier': hashed_identifier,
			'repo_name': hashed_name,
			'owner_id': hashed_owner_id,
			'git_branch': hashed_git_branch,
			'git_tag': hashed_git_tag 
    	}
    )

def ui_element_payload(**kwargs):
	return SelfDescribingJson(
		'iglu:com.software/ui_element/jsonschema/1-0-3',
		{
			'element_name': kwargs['element_name'],
			'element_location': kwargs['element_location'],
			'color': kwargs['color'],
			'icon_name': kwargs['icon_name'],
			'cta_text': kwargs['cta_text']
		}
	)

def hash_value(value, data_type, jwt):
	if value:
		hashed_value = BLAKE2b(value.encode(), 64).hexdigest()
		
		global cached_hashed_values
		if hashed_value not in cached_hashed_values.get(data_type, []):
			encrypt_and_save(value, hashed_value, data_type, jwt)
			global refresh_hashed_values
			refresh_hashed_values = True

		return hashed_value
	else:
		return ''

def fetch_user_hashed_values():
	response = requestIt('GET', '/hashed_values', None, getJwt())
	r = json.loads(response.read().decode('utf-8'))
	global cached_hashed_values
	cached_hashed_values = r['data']

def encrypt_and_save(value, hashed_value, data_type, jwt):
	params = {
		value: value,
		hashed_value: hashed_value,
		data_type: data_type
	}

	response = requestIt('POST', '/user_encrypted_data', json.dumps(params), jwt)
	if response and isResponseOk(response):
		return
	else:
		print("error POSTing to /user_encrypted_data")
		print(response)
