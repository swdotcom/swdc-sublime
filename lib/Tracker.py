import os
import sys
from .SoftwareHttp import *

print(sys.version)

# Add vendor directory to module search path
vendor_dir = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'vendor'))
sys.path.append(vendor_dir)

from snowplow_tracker import Subject, Tracker, Emitter

trackerInstance = None

def swdc_tracker():
	if(trackerInstance):
		return trackerInstance
	else
		response = requestIt('GET', '/plugins/config', None, None)
		config = json.loads(response.read().decode('utf-8'))
		e = Emitter(config['tracker_api'])
		t = Tracker(e, 'CodeTime', 'swdc-sublime')
		trackerInstance = t
		return trackerInstance

def track_codetime_event(**kwargs):
	payload = codetime_payload(**kwargs)
	context = build_context(**kwargs)
	swdc_tracker().track_unstruct_event(codetime_payload, context)

def codetime_payload(**kwargs):
	return {
		'schema': 'iglu:com.software/codetime/jsonschema/1-0-1',
		'data': {
			'keystrokes': kwargs['keystrokes'],
			'chars_added': kwargs['chars_added'],
			'chars_deleted': kwargs['chars_deleted'],
			'chars_pasted': kwargs['chars_pasted'],
			'pastes': kwargs['pastes'],
			'lines_added': kwargs['lines_added'],
			'lines_deleted': kwargs['lines_deleted'],
			'start_time': kwargs['start_time'],
			'end_time': kwargs['end_time']
		}
	}

def editor_action_payload(**kwargs):
	return {
		'schema': 'iglu:com.software/editor_action/jsonschema/1-0-1',
		'data': {
			'entity': kwargs['entity'],
			'type': kwargs['type']
		}
	}

def ui_interaction_payload(**kwargs):
	return {
		'schema': 'iglu:com.software/ui_interaction/jsonschema/1-0-0',
		'data': {
			'interaction_type': kwargs['interaction_type']
		}
	}

def auth_payload(**kwargs):
	return {
		'schema': 'iglu:com.software/auth/jsonschema/1-0-0',
		'data': {
			'jwt': kwargs['jwt']
    	}
    }

def file_payload(**kwargs):
	hashed_name = hash_value(kwargs['file_name'], 'file_name', kwargs['jwt'])
	hashed_path = hash_value(kwargs['file_name'], 'file_path', kwargs['jwt'])

	return {
    	'schema': 'iglu:com.software/file/jsonschema/1-0-1',
    	'data': {
			'file_name': hashed_name,
			'file_path': hashed_path,
			'syntax': kwargs['syntax'],
			'line_count': kwargs['line_count'],
			'character_count': kwargs['character_count']
      }
    }

def plugin_payload(**kwargs):
	return {
		'schema': 'iglu:com.software/plugin/jsonschema/1-0-1',
		'data': {
			'plugin_id': kwargs['plugin_id'],
			'plugin_version': kwargs['plugin_version'],
			'plugin_name': kwargs['plugin_name']
    	}
    }

def project_payload(**kwargs):
	hashed_name = hash_value(kwargs['project_name'], "project_name", kwargs['jwt']);
    hashed_directory = hash_value(kwargs['project_directory'], "project_directory", kwargs['jwt']);

    return {
      schema: 'iglu:com.software/project/jsonschema/1-0-0',
      data: {
        project_name: hashed_name,
        project_directory: hashed_directory
      }
    }

def repo_payload(**kwargs):
	hashed_name = hash_value(kwargs['repo_name'], 'repo_name', kwargs['jwt'])
    hashed_identifier = hash_value(kwargs['repo_identifier'], 'repo_identifier', kwargs['jwt'])
    hashed_owner_id = hash_value(kwargs['owner_id'], 'owner_id', kwargs['jwt'])
    hashed_git_branch = hash_value(kwargs['git_branch'], 'git_branch', kwargs['jwt'])
    hashed_git_tag = hash_value(kwargs['git_tag'], 'git_tag', kwargs['jwt'])

    return {
		'schema': 'iglu:com.software/repo/jsonschema/1-0-0',
		'data': {
			'repo_identifier': hashed_identifier,
			'repo_name': hashed_name,
			'owner_id': hashed_owner_id,
			'git_branch': hashed_git_branch,
			'git_tag': hashed_git_tag 
    	}
    }

def ui_element_payload(**kwargs):
	return {
    	'schema': 'iglu:com.software/ui_element/jsonschema/1-0-2',
    	'data': {
    		'element_name': kwargs['element_name'],
    		'element_location': kwargs['element_location'],
    		'color': kwargs['color'],
    		'icon_name': kwargs['icon_name'],
    		'cta_text': kwargs['cta_text']
 		}
    }

def build_context(**kwargs):
	auth_context = build_auth_payload(**kwargs)


def hash_value(value, data_type, jwt):
	# TODO
	return value
