#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 14 11:43:55 2020

@author: eo
"""


# ---------------------------------------------------------------------------------------------------------------------
#%% Imports

import signal

from waitress import serve as wsgi_serve

from flask import Flask
from flask import request as flask_request
from flask_cors import CORS

from local.lib.environment import using_spyder_ide, get_default_fps
from local.lib.environment import get_gifserver_protocol, get_gifserver_host, get_gifserver_port
from local.lib.environment import get_dbserver_protocol, get_dbserver_host, get_dbserver_port

from local.lib.timekeeper_utils import datetime_to_isoformat_string

from local.lib.request_helpers import connect_to_dbserver, check_server_connection, get_snapshot_ems_list
from local.lib.response_helpers import json_response, error_response

from local.lib.video_creation import create_video_simple_replay
from local.lib.video_creation import create_video_from_instructions, create_video_response_from_b64_jpgs

from local.lib.perspective_correction import check_valid_quad, calculate_perspective_correction_factors

from local.eolib.utils.use_git import Git_Reader


# ---------------------------------------------------------------------------------------------------------------------
#%% Server control

# .....................................................................................................................

def register_waitress_shutdown_command():
    
    ''' Awkward hack to get waitress server to close on SIGTERM signals '''
    
    def convert_sigterm_to_keyboard_interrupt(signal_number, stack_frame):
        print("", "", "*" * 48, "Kill signal received! ({})".format(signal_number), "*" * 48, "", sep = "\n")
        raise KeyboardInterrupt
    
    # Replaces SIGTERM signals with a Keyboard interrupt, which the server will handle properly
    signal.signal(signal.SIGTERM, convert_sigterm_to_keyboard_interrupt)
    
    return

# .....................................................................................................................

def check_git_version():
    
    ''' Helper function used to generate versioning info to be displayed on main web page '''
    
    # Initialize output in case of errors
    is_valid = False
    version_indicator_str = "unknown"
    commit_date_str = "unknown"
    
    # Try to get versioning info    
    try:
        commit_id, commit_tags_list, commit_dt = GIT_READER.get_current_commit()
        
        # Use tag if possible to represent the version
        version_indicator_str = ""
        if len(commit_tags_list) > 0:
            version_indicator_str = ", ".join(commit_tags_list)
        else:
            version_indicator_str = commit_id
        
        # Add time information
        commit_date_str = commit_dt.strftime("%b %d")
        
        # If we get here, the info is probably good
        is_valid = True
        
    except:
        pass
    
    return is_valid, commit_date_str, version_indicator_str

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Configure

# Get (global!) settings
DBSERVER_PROTOCOL = get_dbserver_protocol()
DBSERVER_HOST = get_dbserver_host()
DBSERVER_PORT = get_dbserver_port()
DBSERVER_URL = "{}://{}:{}".format(DBSERVER_PROTOCOL, DBSERVER_HOST, DBSERVER_PORT)


# ---------------------------------------------------------------------------------------------------------------------
#%% Create server routes

# Create wsgi application so we can start adding routes
wsgi_app = Flask(__name__)
CORS(wsgi_app)

# .....................................................................................................................

@wsgi_app.route("/")
def home_route():
    
    # For convenience
    indent_by_2 = lambda message: "  {}".format(message)
    
    # Generate versioning info
    version_is_valid, version_date_str, version_id_str = check_git_version()
    bad_version_entry = "<p>error getting version info!</p>"
    good_version_entry = "<p>version: {} ({})</p>".format(version_id_str, version_date_str)
    git_version_str = (good_version_entry if version_is_valid else bad_version_entry)
    
    # Build html line-by-line
    html_list = ["<!DOCTYPE html>",
                 "<html>",
                 "<head>",
                 indent_by_2("<title>GIF Wrapper</title>"),
                 indent_by_2("<link rel='icon' href='data:;base64,iVBORw0KGgo='>"),
                 "</head>",
                 "<body>",
                 indent_by_2("<h1>GIF Wrapper is running: <a href='/help'>Route listing</a></h1>"),
                 indent_by_2(git_version_str),
                 "</body>",
                 "</html>"]
    
    return "\n".join(html_list)

# .....................................................................................................................

@wsgi_app.route("/help")
def help_route():

    # Initialize output html listing
    html_strs = ["<title>GIF Wrapper Help</title>", "<h1>Route List:</h1>"]
    
    # Get valid methods to print
    valid_methods = ("GET", "POST")
    check_methods = lambda method: method in valid_methods
    
    url_list = []
    html_entry_list = []
    for each_route in wsgi_app.url_map.iter_rules():
        
        # Ignore the static path
        if "static" in each_route.rule:
            continue
        
        # Get route urls (for sorting)
        each_url = each_route.rule
        url_list.append(each_url)
        
        # Clean up url and get GET/POST listing
        cleaned_url = each_url.replace("<", " (").replace(">", ") ")
        method_str = ", ".join(filter(check_methods, each_route.methods))
        
        # Generate a inactive/active link versions of the url
        method_html = "<b>[{}]</b>&nbsp;&nbsp;&nbsp;".format(method_str)
        dead_html_entry = "<p>{}{}</p>".format(method_html, cleaned_url)
        link_html_entry = "<p>{}<a href={}>{}</a></p>".format(method_html, cleaned_url, cleaned_url)
        
        # Decide which style url to present
        show_as_dead = ("(" in cleaned_url) or (cleaned_url == "/help") or (cleaned_url == "/")
        add_html_entry = dead_html_entry if show_as_dead else link_html_entry
        html_entry_list.append(add_html_entry)
    
    # Alphabetically sort url listings (so they group nicely) then add to html
    _, sorted_html_entries = zip(*sorted(zip(url_list, html_entry_list)))
    html_strs += sorted_html_entries
    
    return "\n".join(html_strs)

# .....................................................................................................................

@wsgi_app.route("/get-version-info")
def get_server_version():
    
    ''' Route used to check the current version of the server (based on git repo details) '''
    
    try:
        commit_id, commit_tags_list, commit_dt = GIT_READER.get_current_commit()
        isoformat_datetime = datetime_to_isoformat_string(commit_dt)
        
    except Exception:
        commit_id = "error"
        commit_tags_list = []
        isoformat_datetime = "error"
    
    # Bundle results for better return
    return_result = {"commit_id": commit_id,
                     "tags_list": commit_tags_list,
                     "commit_datetime_isoformat": isoformat_datetime}
    
    return json_response(return_result, status_code = 200)

# .....................................................................................................................

@wsgi_app.route("/<string:camera_select>/simple-replay/<int:start_ems>/<int:end_ems>")
def simple_replay_route(camera_select, start_ems, end_ems):
    
    # Check dbserver connection, since we'll need it to get snapshot listing
    dbserver_is_connected = check_server_connection(DBSERVER_URL, feedback_on_error = False)
    if not dbserver_is_connected:
        error_msg = "No connection to dbserver!"
        return error_response(error_msg, status_code = 500)
    
    # Interpret ghosting flag
    enable_ghosting_str = flask_request.args.get("ghost", "true")
    enable_ghosting_bool = (enable_ghosting_str.lower() in {"1", "true", "on", "enable"})
    
    # Request snapshot timing info from dbserver
    snap_ems_list = get_snapshot_ems_list(DBSERVER_URL, camera_select, start_ems, end_ems)
    no_snapshots_to_download = (len(snap_ems_list) == 0)
    if no_snapshots_to_download:
        error_msg = "No snapshots in provided time range"
        return error_response(error_msg, status_code = 400)
    
    # Make sure snapshot times are ordered!
    snap_ems_list = sorted(snap_ems_list)
    
    return create_video_simple_replay(DBSERVER_URL, camera_select, snap_ems_list, enable_ghosting_bool)

# .....................................................................................................................

@wsgi_app.route("/create-animation/from-instructions", methods = ["GET", "POST"])
def create_animation_from_instructions_route():
    
    # If using a GET request, return some info for how to use POST route
    if flask_request.method == "GET":
        info_list = ["Use (as a POST request) to create animations",
                     "Data is expected to be provided in JSON, in the following format:",
                     "{",
                     " 'camera_select: (string),",
                     " 'frame_rate': (float),",
                     " 'ghosting': {",
                     "              'enable': (boolean),",
                     "              'brightness_scaling': (float),",
                     "              'blur_size': (int),",
                     "              'pixelation_factor': (int)",
                     "             },",
                     " 'instructions': [...]",
                     "}",
                     "",
                     "The 'instructions' key should be a list drawing instructions for each snapshot",
                     "The first entry in the list will be the first frame of the animation",
                     "Each entry in the instructions list should be another JSON object, in the following format:",
                     "[",
                     " {'snapshot_ems': (int), 'drawing': [...]},",
                     " {... next frame ...},",
                     " {... next frame ...},",
                     " etc.",
                     "]",
                     "",
                     "The 'drawing' key should hold a list of what should be drawn on the corresponding snapshot",
                     "Each entry in the drawing list should be a JSON object (see below for options)",
                     "If nothing is to be drawn, the drawing instructions should be an empty list: []",
                     "The following drawing instructions are available:",
                     "{",
                     " 'type': 'polyline',",
                     " 'xy_points_norm': (list of xy pairs in normalized co-ordinates),",
                     " 'is_closed': (boolean),",
                     " 'color_rgb': (list of 3 values between 0-255),",
                     " 'thickness_px': (int, use -1 to fill),",
                     " 'antialiased': (boolean)",
                     "}",
                     "",
                     "{",
                     " 'type': 'circle',",
                     " 'center_xy_norm': (pair of xy values in normalized co-ordinates),",
                     " 'radius_norm': (float, normalized to frame diagonal length),",
                     " 'color_rgb': (list of 3 values between 0-255),",
                     " 'thickness_px': (int, use -1 to fill),",
                     " 'antialiased': (boolean)",
                     "}",
                     "",
                     "{",
                     " 'type': 'rectangle',",
                     " 'top_left_norm': (pair of xy values in normalized co-ordinates),",
                     " 'bottom_right_norm': (pair of xy values in normalized co-ordinates),",
                     " 'color_rgb': (list of 3 values between 0-255),",
                     " 'thickness_px': (int, use -1 to fill),",
                     " 'antialiased': (boolean)",
                     "}",
                     "",
                     "{",
                     " 'type': 'text',",
                     " 'message': (string),",
                     " 'text_xy_norm': (pair of xy values in normalized co-ordinates),",
                     " 'align_horizontal': ('left', 'center' or 'right')",
                     " 'align_vertical': ('top', 'center' or 'bottom')",
                     " 'text_scale': (float)",
                     " 'color_rgb': (list of 3 values between 0-255),",
                     " 'bg_color_rgb': (list of 3 values between 0-255 or null to disable),",
                     " 'thickness_px': (int, use -1 to fill),",
                     " 'antialiased': (boolean)",
                     "}"]
        return json_response(info_list, status_code = 200)
    
    # -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    
    # If we get here, we're dealing with a POST request, make sure we got something...
    animation_data_dict = flask_request.get_json(force = True)
    missing_animation_data = (animation_data_dict is None)
    if missing_animation_data:
        error_msg = "Missing animation data. Call this route as a GET request for more info"
        return error_response(error_msg, status_code = 400)
    
    # Pull-out global config settings (or defaults)
    camera_select = animation_data_dict.get("camera_select", None)
    frame_rate = animation_data_dict.get("frame_rate", get_default_fps())
    ghost_config_dict = animation_data_dict.get("ghosting", {"enable": False})
    instructions_list = animation_data_dict.get("instructions", [])
    
    # Bail if no camera was selected
    bad_camera = (camera_select is None)
    if bad_camera:
        error_msg = "No camera selected"
        return error_response(error_msg, status_code = 400)
    
    # Bail if we got no frame instructions
    data_is_valid = (len(instructions_list) > 0)
    if not data_is_valid:
        error_msg = "Did not find any drawing instructions"
        return error_response(error_msg, status_code = 400)
    
    # Check dbserver connection, since we'll need it to get snapshot data
    dbserver_is_connected = check_server_connection(DBSERVER_URL, feedback_on_error = False)
    if not dbserver_is_connected:
        error_msg = "No connection to dbserver!"
        return error_response(error_msg, status_code = 500)
    
    # Use instructions to get target snapshots & draw overlay as needed
    return create_video_from_instructions(DBSERVER_URL,
                                          camera_select, instructions_list, frame_rate, ghost_config_dict)

# .....................................................................................................................

@wsgi_app.route("/create-animation/from-b64-jpgs", methods = ["GET", "POST"])
def create_animation_from_b64_jpgs_route():
    
    # If using a GET request, return some info for how to use POST route
    if flask_request.method == "GET":
        info_list = ["Use (as a POST request) to create animations",
                     "Data is expected to be provided in JSON, in the following format:",
                     "{",
                     " 'frame_rate': (float),",
                     " 'b64_jpgs': (list of b64-encoded jpgs)",
                     "}",
                     "The 'b64_jpgs' entry should contain a sequence of base64 encoded jpgs to be rendered",
                     "The first entry in the list will be the first frame of the animation"]
        return json_response(info_list, status_code = 200)
    
    # -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    
    # If we get here, we're dealing with a POST request, make sure we got something...
    animation_data_dict = flask_request.get_json(force = True)
    missing_animation_data = (animation_data_dict is None)
    if missing_animation_data:
        error_msg = "Missing animation data. Call this route as a GET request for more info"
        return error_response(error_msg, status_code = 400)
    
    # Pull out global information
    frame_rate = animation_data_dict.get("frame_rate", get_default_fps())
    b64_jpgs_list = animation_data_dict.get("b64_jpgs", [])
    
    # Bail if we got no image data
    data_is_valid = (len(b64_jpgs_list) > 0)
    if not data_is_valid:
        error_msg = "Did not find any base64 jpgs data to render!"
        return error_response(error_msg, status_code = 400)
    
    return create_video_response_from_b64_jpgs(b64_jpgs_list, frame_rate)

# .....................................................................................................................

@wsgi_app.route("/get-perspective-correction", methods = ["GET", "POST"])
def get_perspective_correction_route():
    
    # If using a GET request, return some info for how to use POST route
    if flask_request.method == "GET":
        info_list = ["Use (as a POST request) to get perspective correction data",
                     "Data is expected to be provided in JSON, in the following format:",
                     "{",
                     " 'input_quad': list of 4 xy-pairs",
                     "}",
                     "- Input quad is assumed to represent a shape that would be rectangular if not for perspective",
                     "- Input quad points are expected to be in normalized units",
                     "- The order of the quad points will affect the orientation of the output mapping",
                     "  - Assumed to be provided as [top-left, top-right, bot-right, bot-left]",
                     "- The warping will map these points to: (0, 0), (1, 0), (1, 1), (0, 1)",
                     "",
                     "This route will return two matrices, for mapping points in either direction",
                     "- 'in_to_out_matrix' maps points from the input co-ords. to (warped) output co-ords.",
                     "- 'out_to_in_matrix' maps (warped) outputs back to input co-ords.",
                     "",
                     "To use in-to-out mapping:",
                     "Assume we have an input xy co-ordinate (xi, yi)",
                     "Assume we have an in-to-out matrix:",
                     "",
                     "         [m11, m12, m13]",
                     "  Mi2o = [m21, m22, m23]",
                     "         [m31, m32, m33]",
                     "",
                     "Form intermediate values Nx, Ny and D, given by:",
                     "",
                     "  Nx = (m11 * xi) + (m12 * yi) + m13",
                     "  Ny = (m21 * xi) + (m22 * yi) + m23",
                     "   D = (m31 * xi) + (m32 * yi) + m33",
                     "",
                     "Note: This result is a matrix-vector multiplication using: Mi2o * [xi, yi, 1]^T",
                     "The warped outputs (xo, yo) are then given by:",
                     "",
                     "  xo = Nx / D",
                     "  yo = Ny / D",
                     "",
                     "The out-to-in matrix can be used in the same way to warp back to input co-ordinates!"]
        return json_response(info_list, status_code = 200)
    
    # -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    
    # If we get here, we're dealing with a POST request, make sure we got something...
    post_data_dict = flask_request.get_json(force = True)
    missing_data = (post_data_dict is None)
    if missing_data:
        error_msg = "Missing post data. Call this route as a GET request for more info"
        return error_response(error_msg, status_code = 400)
    
    # Pull out correction request data information
    input_quad = post_data_dict.get("input_quad", None)
    
    # Bail if the input quad draw is bad
    in_quad_is_valid, error_msg = check_valid_quad(input_quad)
    if not in_quad_is_valid:
        return error_response(error_msg, status_code = 400)
    
    # Get perspective correction data
    correction_is_valid = False
    try:
        correction_is_valid, in_to_out_warp_mat_as_list, out_to_in_warp_mat_as_list = \
        calculate_perspective_correction_factors(input_quad)
        
    except (ValueError, TypeError, AttributeError) as err:
        error_msg = "Unknown error calculating perspective matricies ({})".format(str(err))
        return error_response(error_msg)
    
    # Bail on bad corrections
    if not correction_is_valid:
        error_msg = "Invalid perspective correction! Quad may not be possible to correct..."
        return error_response(error_msg)
    
    # Bundle outputs if we get this far
    return_result = {"in_to_out_matrix": in_to_out_warp_mat_as_list,
                     "out_to_in_matrix": out_to_in_warp_mat_as_list}
    
    return json_response(return_result, status_code = 200)

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Set up globals

# Set up git repo access
GIT_READER = Git_Reader(None)


# ---------------------------------------------------------------------------------------------------------------------
#%% *** Launch server ***

if __name__ == "__main__":
    
    # Set server access parameters
    gifserver_protocol = get_gifserver_protocol()
    gifserver_host = get_gifserver_host()
    gifserver_port = get_gifserver_port()
    
    # Check connection to the dbserver, with some re-tries on failure
    # -> This isn't strictly needed, however, it prevents this server from starting immediately
    #    if there is no connection to the dbserver. Helpful for catching errors on deployment
    connect_to_dbserver(DBSERVER_URL)
    
    # Launch server
    if not using_spyder_ide():
        register_waitress_shutdown_command()
        print("")
        wsgi_serve(wsgi_app, host = gifserver_host, port = gifserver_port, url_scheme = gifserver_protocol)


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap

'''
STOPPED HERE
- SHOULD TEST ARG TYPECASTING SOME MORE AS WELL!
- CONSIDER SETTING UP DEMO ROUTES? TO ACT AS BASIC DOCUMENTATION OF ROUTES FOR FUTURE USE???
'''

