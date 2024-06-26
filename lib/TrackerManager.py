import os
import sys
import json
from datetime import datetime
from .SoftwareHttp import *
from .blake2 import BLAKE2b
from .SoftwareUtil import *
from .CommonUtil import *
# Add vendor directory to module search path
# This needs to be here to load the snowplow_tracker library
vendor_dir = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'vendor'))
sys.path.append(vendor_dir)
from snowplow_tracker import Subject, Tracker, Emitter, SelfDescribingJson

cached_tracker = None
cached_hashed_values = {}
# swdc_tracker will initialize on the first use of it (editor activated event)
# and use a cached instance for every subsequent call
def swdc_tracker(event_json, context):
	global cached_tracker

	if cached_tracker is None:
		response = appRequestIt('GET', '/api/v1/plugins/config', None)
		if response is not None and isResponseOk(response):
			config = json.loads(response.read().decode('utf-8'))
			e = Emitter(config['tracker_api'])
			tracker = Tracker(e, namespace='CodeTime', app_id='swdc-sublime')
			cached_tracker = tracker

	if cached_tracker is not None:
		cached_tracker.track_self_describing_event(event_json, context)

def tracker_enabled():
	return getValue("software_telemetry_on", True)

def track_codetime_event(**kwargs):
	if tracker_enabled():
		event_json = codetime_payload(**kwargs)
		context = build_context(**kwargs)
		swdc_tracker(event_json, context)

def track_editor_action(**kwargs):
	if tracker_enabled():
		event_json = editor_action_payload(**kwargs)
		context = build_context(**kwargs)
		response = swdc_tracker(event_json, context)

def track_ui_interaction(**kwargs):
	if tracker_enabled():
		event_json = ui_interaction_payload(**kwargs)
		context = build_context(**kwargs)
		swdc_tracker(event_json, context)

def build_context(**kwargs):
	ctx = []

	if 'jwt' in kwargs:
		ctx.append(auth_payload(**kwargs))

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
		'iglu:com.software/codetime/jsonschema/1-0-2',
		{
			'keystrokes': kwargs['keystrokes'],
			'lines_added': kwargs['lines_added'],
			'lines_deleted': kwargs['lines_deleted'],
			'characters_added': kwargs['characters_added'],
			'characters_deleted': kwargs['characters_deleted'],
			'single_deletes': kwargs['single_deletes'],
			'multi_deletes': kwargs['multi_deletes'],
			'single_adds': kwargs['single_adds'],
			'multi_adds': kwargs['multi_adds'],
			'auto_indents': kwargs['auto_indents'],
			'replacements': kwargs['replacements'],
			'is_net_change': kwargs['is_net_change'],
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
	hashed_name = hash_value(kwargs['file_name'].replace("\\", "/"), 'file_name', kwargs['jwt'])
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
	plugin_id = kwargs["plugin_id"] or getPluginId()
	plugin_version = kwargs["plugin_version"] or getVersion()
	plugin_name = kwargs["plugin_name"] or getPluginName()

	return SelfDescribingJson(
		'iglu:com.software/plugin/jsonschema/1-0-1',
		{
			'plugin_id': plugin_id,
			'plugin_version': plugin_version,
			'plugin_name': plugin_name
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

latestJwt = None
def hash_value(value, data_type, jwt):
	global latestJwt

	if(jwt != latestJwt):
		latestJwt = jwt
		fetch_user_hashed_values()

	if value:
		hashed_value = BLAKE2b(value.encode(), 64).hexdigest()

		global cached_hashed_values
		if hashed_value not in cached_hashed_values.get(data_type, []):
			if cached_hashed_values.get(data_type, False):
				cached_hashed_values[data_type].append(hashed_value)
			else:
				cached_hashed_values[data_type] = [hashed_value]
			storeHashedValues(cached_hashed_values)

			encrypt_and_save(value, hashed_value, data_type, jwt)

		return hashed_value

def fetch_user_hashed_values():
	try:
		response = appRequestIt('GET', '/api/v1/user/hashed_values', None)
		user_hashed_values = json.loads(response.read().decode('utf-8'))

		global cached_hashed_values
		cached_hashed_values = user_hashed_values
		storeHashedValues(user_hashed_values)
	except Exception as ex:
		logIt("ERROR FETCHING HASHED VALUES")
		logIt(ex)

def encrypt_and_save(value, hashed_value, data_type, jwt):
	params = {
		'value': value,
		'hashed_value': hashed_value,
		'data_type': data_type
	}

	response = appRequestIt('POST', '/api/v1/user/encrypted_data', json.dumps(params))
	if response and isResponseOk(response):
		return True
	else:
		logIt("error POSTing to /api/v1/user/encrypted_data for value: " + hashed_value)
		return False
