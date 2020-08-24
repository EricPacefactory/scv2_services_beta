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
import signal

import cv2
import numpy as np

from tempfile import TemporaryDirectory

from waitress import serve as wsgi_serve

from moviepy.editor import ImageSequenceClip

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

def get_default_fps():
    return int(os.environ.get("DEFAULT_FPS", 8))

# .....................................................................................................................

def get_default_frame_width():
    return int(os.environ.get("DEFAULT_FRAME_WIDTH_PX", 480))

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

def build_bg_image_url(camera_select, target_epoch_ms):
    
    ''' Helper function for generating urls to download background image data '''
    
    ems_str = str(target_epoch_ms)
    return build_dbserver_url(camera_select, "backgrounds", "get-active-image", "by-time-target", ems_str)

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
    image_bytes = None
    
    # Build the request url & make the request
    image_request_url = build_snap_image_url(camera_select, snapshot_epoch_ms)
    dbserver_response = requests.get(image_request_url)
    
    # Only return the response data if the response was ok
    response_success = (dbserver_response.status_code == 200)
    if response_success:
        image_bytes = dbserver_response.content
    
    return image_bytes

# .....................................................................................................................

def get_background_image_data(camera_select, target_epoch_ms):
    
    # Initialize output
    image_bytes = None
    
    # Build the request url & make the request
    image_request_url = build_bg_image_url(camera_select, target_epoch_ms)
    dbserver_response = requests.get(image_request_url)
    
    # Only return the response data if the response was ok
    response_success = (dbserver_response.status_code == 200)
    if response_success:
        image_bytes = dbserver_response.content
    
    return image_bytes

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

def pixelate(frame, output_wh, pixelation_factor = 1):
    
    ''' Helper function which pixelates images '''
    
    # Don't do anything with zero or less factors
    if pixelation_factor < 1:
        return frame
    
    # Shrink then scale back up (with nearest-neighbor interp) to get pixelated look
    scale_factor = 1 / (1 + pixelation_factor)
    shrunk_frame = cv2.resize(frame, dsize = None,
                              fx = scale_factor, fy = scale_factor,
                              interpolation = cv2.INTER_AREA)
    
    return cv2.resize(shrunk_frame, dsize = output_wh, interpolation = cv2.INTER_NEAREST)

# .....................................................................................................................

def image_bytes_to_pixels(image_bytes):
    
    ''' Helper function which convert raw image byte data to an actual iamge (represented as pixels) '''
    
    image_array = np.frombuffer(image_bytes, dtype = np.uint8)
    image_pixel_data = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    
    return image_pixel_data

# .....................................................................................................................

def image_pixels_to_bytes(image_pixel_data, jpg_quality_0_to_100 = 50):
    
    ''' Helper function which convert image data into byte data for saving '''
    
    jpg_params = (cv2.IMWRITE_JPEG_QUALITY, jpg_quality_0_to_100)
    _, image_bytes = cv2.imencode(".jpg", image_pixel_data, jpg_params)
    
    return image_bytes

# .....................................................................................................................

def apply_ghosting(background_image_bytes, frame_bytes,
                   brightness_scaling = 1.5, blur_size = 2, pixelation_factor = 3):
    
    # Bail on missing data
    if background_image_bytes is None:
        return np.zeros_like(frame_bytes)
    if frame_bytes is None:
        return background_image_bytes
    
    # Convert byte-data to actual pixels we can manipulate
    background_image = image_bytes_to_pixels(background_image_bytes)
    frame = image_bytes_to_pixels(frame_bytes)
    
    # Get frame sizing so we can scale the background image appropriately
    frame_height, frame_width = frame.shape[0:2]
    frame_wh = (frame_width, frame_height)
    scaled_bg = cv2.resize(background_image, dsize = frame_wh, interpolation = cv2.INTER_AREA)
    
    # Get frame difference
    frame_difference_3ch = cv2.absdiff(scaled_bg, frame)
    frame_difference_1ch = cv2.cvtColor(frame_difference_3ch, cv2.COLOR_BGR2GRAY)
    
    # If needed, blur to further 'censor' the ghosted result
    if blur_size > 0:
        blur_size_odd = 1 + (2 * blur_size)
        blur_kernel_size = (blur_size_odd, blur_size_odd)
        frame_difference_1ch = cv2.blur(frame_difference_1ch, blur_kernel_size)
    
    # Pixelate the ghosted component if needed
    if pixelation_factor > 0:
        frame_difference_1ch = pixelate(frame_difference_1ch, frame_wh, pixelation_factor)
    
    # Combine difference with background & convert back to byte data for final output
    frame_difference_3ch = cv2.cvtColor(frame_difference_1ch, cv2.COLOR_GRAY2BGR)
    ghosted_frame = cv2.addWeighted(scaled_bg, 1.0, frame_difference_3ch, brightness_scaling, 0.0)
    ghosted_frame_bytes = image_pixels_to_bytes(ghosted_frame)
    
    return ghosted_frame_bytes

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

def save_all_jpgs(save_folder_path, camera_select, snapshot_ems_list, ghosting_config_dict):
    
    # Get ghosting parameters
    enable_ghosting = ghosting_config_dict.get("enable_ghosting", False)
    brightness_factor = ghosting_config_dict.get("brightness_factor", 1.5)
    blur_size = ghosting_config_dict.get("blur_size", 2)
    pixelation_factor = ghosting_config_dict.get("pixelation_factor", 3)
    
    # Grab a background image if we're ghosting
    bg_bytes = None
    if enable_ghosting:
        latest_snap_ems = snapshot_ems_list[-1]
        bg_bytes = get_background_image_data(camera_select, latest_snap_ems)
    
    # Save a jpg for each of the provided epoch ms values
    for each_idx, each_snap_ems in enumerate(snapshot_ems_list):
        
        # Request image data from dbserver
        snap_bytes = get_snapshot_image_data(camera_select, each_snap_ems)
        if snap_bytes is None:
            continue
        
        # Apply ghosting if needed
        if enable_ghosting:
            snap_bytes = apply_ghosting(bg_bytes, snap_bytes,
                                        brightness_factor, blur_size, pixelation_factor)
        
        # Save the jpegs!
        save_one_jpg(save_folder_path, each_idx, snap_bytes)
        
    # Finally, get the number of files saved, for sanity checks
    num_files_saved = len(os.listdir(save_folder_path))
    
    return num_files_saved

# .....................................................................................................................

def create_gif(save_folder_path, frame_rate, frame_width):
    
    # Make sure the frame rate isn't silly
    frame_rate = min(30, max(0.5, frame_rate))
    
    # Build output name & pathing
    output_file_name = "temp.gif"
    path_to_output = os.path.join(save_folder_path, output_file_name)
    
    # Build gif output
    gif_frames = ImageSequenceClip(save_folder_path, fps = frame_rate)
    gif_frames.resize(width = frame_width).write_gif(path_to_output, tempfiles = True)
    
    return path_to_output

# .....................................................................................................................

def create_gif_response(camera_select, snapshot_ems_list, frame_rate, frame_width, ghosting_config_dict):
    
    # Download each of the snapshot images to a temporary folder
    with TemporaryDirectory() as temp_dir:
        
        # Get all jpg data from the dbserver
        num_jpgs = save_all_jpgs(temp_dir, camera_select, snapshot_ems_list, ghosting_config_dict)
        
        # Assuming we have jpgs, create the gif and process as a file to send back to the user
        no_jpgs = (num_jpgs == 0)
        if no_jpgs:
            error_msg = "Could not retrieve jpgs from target snapshot epoch times"
            gif_response = error_response(error_msg, status_code = 500)
            
        else:
            path_to_gif = create_gif(temp_dir, frame_rate, frame_width)
            user_file_name = "output.gif"
            gif_response = send_file(path_to_gif,
                                     attachment_filename = user_file_name,
                                     mimetype = "image/gif",
                                     as_attachment = True)
    
    return gif_response

# .....................................................................................................................

def create_video(save_folder_path, file_ext, frame_rate, frame_width):
    
    # Make sure the frame rate isn't silly
    frame_rate = min(30, max(0.5, frame_rate))
    
    # Build output name & pathing
    output_file_name = "temp.{}".format(file_ext)
    path_to_output = os.path.join(save_folder_path, output_file_name)
    
    # Build gif output
    video_frames = ImageSequenceClip(save_folder_path, fps = frame_rate)
    video_frames.resize(width = frame_width).write_videofile(path_to_output, audio = False)
    
    return path_to_output

# .....................................................................................................................

def create_video_response(camera_select, snapshot_ems_list, file_ext, frame_rate, frame_width, ghosting_config_dict):
    
    # Download each of the snapshot images to a temporary folder
    with TemporaryDirectory() as temp_dir:
        
        # Get all jpg data from the dbserver
        num_jpgs = save_all_jpgs(temp_dir, camera_select, snapshot_ems_list, ghosting_config_dict)
        
        # Assuming we have jpgs, create the video and process as a file to send back to the user
        no_jpgs = (num_jpgs == 0)
        if no_jpgs:
            error_msg = "Could not retrieve jpgs from target snapshot epoch times"
            video_response = error_response(error_msg, status_code = 500)
            
        else:
            path_to_video = create_video(temp_dir, file_ext, frame_rate, frame_width)
            user_file_name = "output.{}".format(file_ext)
            video_response = send_file(path_to_video,
                                       attachment_filename = user_file_name,
                                       mimetype = "video/{}".format(file_ext),
                                       as_attachment = True)
    
    return video_response

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

@wsgi_app.route("/<string:camera_select>/simple-replay/<string:file_ext>/<enable_ghosting>/<int:start_ems>/<int:end_ems>")
def simple_replay_route(camera_select, file_ext, enable_ghosting, start_ems, end_ems):
    
    # Interpret ghosting flag
    enable_ghosting_str = str(enable_ghosting)
    enable_ghosting_bool = (enable_ghosting_str.lower() in {"1", "true", "on", "enable"})
    ghost_config_dict = {"enable_ghosting": enable_ghosting_bool,
                         "brightness_factor": 1.5,
                         "blur_size": 2,
                         "pixelation_factor": 3}
    
    # Use default timing & sizing for simple replay route
    frame_rate = get_default_fps()
    frame_width_px = get_default_frame_width()
    
    # Request snapshot timing info from dbserver
    snap_ems_list = get_snapshot_ems_list(camera_select, start_ems, end_ems)
    no_snapshots_to_download = (len(snap_ems_list) == 0)
    if no_snapshots_to_download:
        error_msg = "No snapshots in provided time range"
        return error_response(error_msg, status_code = 400)
    
    # Make sure snapshot times are ordered!
    snap_ems_list = sorted(snap_ems_list)
    
    # Decide on output format
    safe_ext = str(file_ext).replace(".", "").lower()
    is_gif = (safe_ext == "gif")
    if is_gif:
        return create_gif_response(camera_select, snap_ems_list, frame_rate, frame_width_px, ghost_config_dict)
    
    return create_video_response(camera_select, snap_ems_list, safe_ext, frame_rate, frame_width_px, ghost_config_dict)

# .....................................................................................................................

@wsgi_app.route("/<string:camera_select>/specific-replay", methods = ["GET", "POST"])
def specific_replay_route(camera_select):
    
    # If using a GET request, return some info for how to use POST route
    if flask_request.method == "GET":
        post_args_dict = {"frame_rate": "Number of frames displayed per second of animation",
                          "frame_width_px": "The width of the output animation (height scales proportionally)",
                          "snapshot_ems_list": "A list of the snapshot epoch ms values to render into a animation",
                          "file_ext": "Output file extension. Can be gif or mp4 for example",
                          "enable_ghosting": "If true, all frames will be ghosted prior to rendering the animation",
                          "ghost_brightness_factor": "A brightness scaling factor for ghosting (should be > 1.0)",
                          "ghost_blur_size": "Controls how much blurring occurs on ghosted images",
                          "ghost_pixelation_factor": "Controls pixelation applied to ghosted images"}
        
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
    frame_rate = post_args_dict.get("frame_rate", get_default_fps())
    frame_width_px = post_args_dict.get("frame_width_px", get_default_frame_width())
    file_ext = post_args_dict.get("file_ext", "gif")
    enable_ghosting = post_args_dict.get("enable_ghosting", False)
    ghost_brightness_factor = post_args_dict.get("ghost_brightness_factor", 1.5)
    ghost_blur_size = post_args_dict.get("ghost_blur_size", 2)
    ghost_pixelation_factor = post_args_dict.get("ghost_pixelation_factor", 3)
    ghost_config_dict = {"enable_ghosting": enable_ghosting,
                         "brightness_factor": ghost_brightness_factor,
                         "blur_size": ghost_blur_size,
                         "pixelation_factor": ghost_pixelation_factor}
    
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
    
    # Make sure frame size is reasonable
    frame_width_px = max(10, int(frame_width_px))
    
    # Decide on output format
    safe_ext = str(file_ext).replace(".", "").lower()
    is_gif = (safe_ext == "gif")
    if is_gif:
        return create_gif_response(camera_select, snap_ems_list, frame_rate, frame_width_px, ghost_config_dict)
    
    return create_video_response(camera_select, snap_ems_list, safe_ext, frame_rate, frame_width_px, ghost_config_dict)

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
        register_waitress_shutdown_command()
        print("")
        wsgi_serve(wsgi_app, host = gifserver_host, port = gifserver_port, url_scheme = gifserver_protocol)


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap



