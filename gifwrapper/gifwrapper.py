#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 14 11:43:55 2020

@author: eo
"""


# ---------------------------------------------------------------------------------------------------------------------
#%% Imports

import os
import requests
import subprocess

from tempfile import TemporaryDirectory

from waitress import serve as wsgi_serve

from flask import Flask, send_file, jsonify
from flask import request as flask_request
from flask_cors import CORS


# ---------------------------------------------------------------------------------------------------------------------
#%% Script control

# .....................................................................................................................

def using_spyder_ide():
    
    return any("spyder" in os.environ[each_key].lower() for each_key in os.environ.keys())

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Environment

# .....................................................................................................................

def get_gifserver_protocol():
    return os.environ.get("GIFSERVER_PROTOCOL", "http")

# .....................................................................................................................

def get_gifserver_host():
    return os.environ.get("GIFSERVER_HOST", "0.0.0.0")

# .....................................................................................................................

def get_gifserver_port():
    return int(os.environ.get("GIFSERVER_PORT", 7171))

# .....................................................................................................................

def get_dbserver_protocol():
    return os.environ.get("DBSERVER_PROTOCOL", "http")

# .....................................................................................................................

def get_dbserver_host():
    return os.environ.get("DBSERVER_HOST", "localhost")

# .....................................................................................................................

def get_dbserver_port():
    return int(os.environ.get("DBSERVER_PORT", 8050))

# .....................................................................................................................

def get_default_delay_ms():
    return int(os.environ.get("DEFAULT_DELAY_MS", 150))

# .....................................................................................................................

def get_default_max_frame_size_px():
    return int(os.environ.get("DEFAULT_MAX_FRAME_SIZE_PX", 480))

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% URL Helpers

# .....................................................................................................................

def build_dbserver_url(*url_components):
    
    ''' Helper function for building urls to the dbserver '''
    
    return "/".join([DBSERVER_URL, *url_components])

# .....................................................................................................................

def build_snap_ems_list_url(camera_select, start_ems, end_ems):
    
    ''' Helper function for generating the url to request a list of snapshot epoch ms values in a time range '''
    
    return build_dbserver_url(camera_select, "snapshots", "get-ems-list", "by-time-range",
                              str(start_ems), str(end_ems))

# .....................................................................................................................

def build_snap_image_url(camera_select, snapshot_epoch_ms):
    
    ''' Helper function for generating urls to download snapshot image data '''
    
    return build_dbserver_url(camera_select, "snapshots", "get-one-image", "by-ems", str(snapshot_epoch_ms))

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% HTTP Request functions

# .....................................................................................................................

def check_server_connection(dbserver_url):
    
    ''' Helper function which checks that a server is accessible '''
    
    # Build server status check url
    status_check_url = "{}/is-alive".format(dbserver_url)
    connection_str_for_errors = "@ {}".format(status_check_url)
    
    # Request status check from the server
    server_is_alive = False
    try:
        server_response = requests.get(status_check_url, timeout = 10)
        response_code = (server_response.status_code)
        server_is_alive = (response_code == 200)
        if not server_is_alive:
            print("",
                  "Bad status code connecting to server:",
                  connection_str_for_errors,
                  "",
                  "Status code: {}".format(response_code),
                  sep = "\n")
        
    except requests.ConnectionError as err:
        print("",
              "Error connecting to server:",
              connection_str_for_errors,
              "",
              err,
              sep = "\n")
        
    except requests.exceptions.ReadTimeout as err:
        print("",
              "Timeout error connecting to server:",
              connection_str_for_errors,
              "",
              err,
              sep = "\n")
    
    return server_is_alive

# .....................................................................................................................

def get_snapshot_ems_list(camera_select, start_ems, end_ems):
    
    # Initialize output
    snapshot_ems_list = []
    
    # Build the request url & make the request
    snapshot_ems_list_request_url = build_snap_ems_list_url(camera_select, start_ems, end_ems)
    dbserver_response = requests.get(snapshot_ems_list_request_url)
    
    # Only return the response data if the response was ok
    response_success = (dbserver_response.status_code == 200)
    if response_success:
        snapshot_ems_list = dbserver_response.json()
    
    return snapshot_ems_list

# .....................................................................................................................

def get_snapshot_image_data(camera_select, snapshot_epoch_ms):
    
    # Initialize output
    image_data = None
    
    # Build the request url & make the request
    image_request_url = build_snap_image_url(camera_select, snapshot_epoch_ms)
    dbserver_response = requests.get(image_request_url)
    
    # Only return the response data if the response was ok
    response_success = (dbserver_response.status_code == 200)
    if response_success:
        image_data = dbserver_response.content
    
    return image_data

# .....................................................................................................................

def json_response(response_dict, status_code = 200):
    
    ''' Helper function for handling the return of arbitrary json messages '''
    
    return jsonify(response_dict), status_code

# .....................................................................................................................

def error_response(error_message, status_code = 500):
    
    ''' Helper function for handling the return of error messages '''
    
    return json_response({"error": error_message}, status_code)

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% I/O functions

# .....................................................................................................................

def save_one_jpg(save_folder_path, image_ems, image_data):
    
    # Build the file name with the right extension and enough (left-sided) zero padding to avoid ordering errors
    save_file_name = "{}.jpg".format(image_ems).rjust(20, "0")
    
    # Build pathing to save jpg file & save the image data
    save_path = os.path.join(save_folder_path, save_file_name)
    with open(save_path, "wb") as outfile:
        outfile.write(image_data)
    
    return save_path

# .....................................................................................................................

def save_all_jpgs(save_folder_path, camera_select, snapshot_ems_list):
    
    # Save a jpg for each of the provided epoch ms values
    for each_idx, each_snap_ems in enumerate(snapshot_ems_list):
        
        print(each_idx, each_snap_ems)
            
        # Request image data from dbserver
        image_data = get_snapshot_image_data(camera_select, each_snap_ems)
        if image_data is None:
            continue
        
        # Save the jpegs!
        save_one_jpg(save_folder_path, each_idx, image_data)
        
    # Finally, get the number of files saved, for sanity checks
    num_files_saved = len(os.listdir(save_folder_path))
    
    return num_files_saved

# .....................................................................................................................

def create_gif(save_folder_path, gif_delay, frame_size):
    
    # Build output name & pathing
    output_file_name = "temp.gif"
    path_to_output = os.path.join(save_folder_path, output_file_name)
    
    # Create resize command
    resize_cmd = "{:.0f}>".format(frame_size)
    
    # Build pathing to input images & run gif creation
    path_to_input_jpgs = os.path.join(save_folder_path, "*.jpg")
    run_command_list = ["convert",
                        "-delay", str(gif_delay),
                        "-resize", resize_cmd,
                        path_to_input_jpgs,
                        path_to_output]
    subprocess.run(run_command_list)
    
    return path_to_output

# .....................................................................................................................

def get_gif_response(camera_select, snapshot_ems_list, delay_ms, max_frame_size_px):
    
    # Convert delay value to 1/100th of a second, which gif creation program uses...
    gif_delay = int(round(delay_ms / 10))
    
    # Download each of the snapshot images to a temporary folder
    with TemporaryDirectory() as temp_dir:
        
        # Get all jpg data from the dbserver
        num_jpgs = save_all_jpgs(temp_dir, camera_select, snapshot_ems_list)
        
        # Assuming we have jpgs, create the gif and process as a file to send back to the user
        no_jpgs = (num_jpgs == 0)
        if no_jpgs:
            error_msg = "Could not retrieve jpgs from target snapshot epoch times"
            gif_response = error_response(error_msg, status_code = 500)
            
        else:
            path_to_gif = create_gif(temp_dir, gif_delay, max_frame_size_px)
            user_file_name = "output.gif"
            gif_response = send_file(path_to_gif,
                                     attachment_filename = user_file_name,
                                     mimetype = "image/gif",
                                     as_attachment = True)
    
    return gif_response

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
    
    html_strs_list = ["<title>SCV2 GIF Wrapper</title>",
                      "<h1>GIF Wrapper is running: <a href='/help'>Route listing</a></h1>"]
    
    return "\n".join(html_strs_list)

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
        
        html_entry = "<p><b>[{}]</b>&nbsp;&nbsp;&nbsp;{}</p>".format(method_str, cleaned_url)
        html_entry_list.append(html_entry)
    
    # Alphabetically sort url listings (so they group nicely) then add to html
    _, sorted_html_entries = zip(*sorted(zip(url_list, html_entry_list)))
    html_strs += sorted_html_entries
    
    return "\n".join(html_strs)

# .....................................................................................................................

@wsgi_app.route("/<string:camera_select>/simple-replay/<int:start_ems>/<int:end_ems>")
def gif_simple_replay_route(camera_select, start_ems, end_ems):
    
    # Use default timing & sizing for simple replay route
    delay_ms = get_default_delay_ms()
    max_frame_size_px = get_default_max_frame_size_px()
    
    # Request snapshot timing info from dbserver
    snap_ems_list = get_snapshot_ems_list(camera_select, start_ems, end_ems)
    no_snapshots_to_download = (len(snap_ems_list) == 0)
    if no_snapshots_to_download:
        error_msg = "No snapshots in provided time range"
        return error_response(error_msg, status_code = 400)
    
    # Make sure snapshot times are ordered!
    snap_ems_list = sorted(snap_ems_list)
    
    return get_gif_response(camera_select, snap_ems_list, delay_ms, max_frame_size_px)

# .....................................................................................................................

@wsgi_app.route("/<string:camera_select>/specific-replay", methods = ["GET", "POST"])
def gif_specific_replay_route(camera_select):
    
    # If using a GET request, return some info for how to use POST route
    if flask_request.method == "GET":
        post_args_dict = {"delay_ms": "The delay between frames (in milliseconds) of the output animation",
                          "max_frame_size_px": "The maximum frame dimension of the output animation",
                          "snapshot_ems_list": "A list of the snapshot epoch ms values to render into a gif"}
        
        return json_response(post_args_dict, status_code = 200)
    
    # -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    
    # If we get here, we're dealing with a POST request, make sure we got something...
    post_args_dict = flask_request.get_json()
    missing_post_args = (post_args_dict is None)
    if missing_post_args:
        error_msg = "Missing POST arguments. Call this route as a GET request for options"
        return error_response(error_msg, status_code = 400)
    
    # Parse the post args
    snap_ems_list = post_args_dict.get("snapshot_ems_list", [])
    delay_ms = post_args_dict.get("delay_ms", get_default_delay_ms())
    max_frame_size_px = post_args_dict.get("max_frame_size_px", get_default_max_frame_size_px())
    
    # Check for errors providing snapshot times
    bad_snap_ems_list = (type(snap_ems_list) not in {list, tuple})
    if bad_snap_ems_list:
        snap_ems_type = type(snap_ems_list).__name__
        error_msg = "snapshot_ems_list should be a list! Got: {}".format(snap_ems_type)
        return error_response(error_msg, status_code = 400)
    
    # Avoid missing snapshot times
    no_snapshots_to_download = (len(snap_ems_list) == 0)
    if no_snapshots_to_download:
        error_msg = "No snapshot epoch ms values were provided!"
        return error_response(error_msg, status_code = 400)
    
    # Make sure delay is reasonable
    delay_ms = max(5, int(delay_ms))
    
    # Make sure frame size is reasonable
    max_frame_size_px = max(10, int(max_frame_size_px))
    
    return get_gif_response(camera_select, snap_ems_list, delay_ms, max_frame_size_px)

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% *** Launch server ***

if __name__ == "__main__":
    
    # Set server access parameters
    gifserver_protocol = get_gifserver_protocol()
    gifserver_host = get_gifserver_host()
    gifserver_port = get_gifserver_port()
    
    # Check connection to the dbserver
    dbserver_is_connected = check_server_connection(DBSERVER_URL)
    if not dbserver_is_connected:
        print("", 
              "No connection to dbserver!", 
              "@ {}".format(DBSERVER_URL),
              sep = "\n")
        quit()
    
    # Launch server
    if not using_spyder_ide():
        print("")
        wsgi_serve(wsgi_app, host = gifserver_host, port = gifserver_port, url_scheme = gifserver_protocol)


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap



