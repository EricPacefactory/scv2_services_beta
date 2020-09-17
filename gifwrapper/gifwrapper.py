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
import base64

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

def get_snapshot_image_bytes(camera_select, snapshot_epoch_ms):
    
    # Initialize output
    image_bytes = None
    
    # Build the request url & make the request
    image_request_url = build_snap_image_url(camera_select, snapshot_epoch_ms)
    dbserver_response = requests.get(image_request_url)
    
    # Only return the response data if the response was ok
    response_success = (dbserver_response.status_code == 200)
    if response_success:
        image_bytes = dbserver_response.content
    
    return response_success, image_bytes

# .....................................................................................................................

def get_background_image_bytes(camera_select, target_epoch_ms):
    
    # Initialize output
    image_bytes = None
    
    # Build the request url & make the request
    image_request_url = build_bg_image_url(camera_select, target_epoch_ms)
    dbserver_response = requests.get(image_request_url)
    
    # Only return the response data if the response was ok
    response_success = (dbserver_response.status_code == 200)
    if response_success:
        image_bytes = dbserver_response.content
    
    return response_success, image_bytes

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
#%% Drawing functions

# .....................................................................................................................

def interpret_drawing_call(display_frame, drawing_instructions_dict):
    
    ''' Function which handles 'drawing calls' for videos rendered by instructions '''
    
    # Make sure we got a dictionary
    drawing_is_dict = (type(drawing_instructions_dict) is dict)
    if not drawing_is_dict:
        error_msg = "Drawing instructions malformed! Got: {}".format(drawing_instructions_dict)
        return draw_error_message(display_frame, error_msg)
    
    # Get the drawing type
    draw_type = drawing_instructions_dict.get("type", None)
    if draw_type is None:
        return draw_error_message(display_frame, "Missing drawing type!")
    
    # Handle lines/polygons
    if draw_type == "polyline":
        return draw_polyline(display_frame, **drawing_instructions_dict)
    
    # Handle circles
    if draw_type == "circle":
        return draw_circle(display_frame, **drawing_instructions_dict)
    
    # Handle squares/rectangles
    if draw_type == "rectangle":
        return draw_rectangle(display_frame, **drawing_instructions_dict)
    
    # Handle text display
    if draw_type == "text":
        return draw_text(display_frame, **drawing_instructions_dict)
    
    # Send a blank frame if we didn't get an expected type, just to make it clear something went wrong
    return draw_error_message(display_frame, "Unrecognized drawing type! ({})".format(draw_type))

# .....................................................................................................................

def draw_polyline(display_image, xy_points_norm,
                  is_closed = False, color_rgb = (255, 255, 0), thickness_px = 1, antialiased = True, **kwargs):
    
    # Convert color to bgr for opencv
    color_bgr = color_rgb[::-1]
    
    # Use filled polygon if thickness is negative
    fill_polygon = (thickness_px < 1)
    
    # Decide on line type
    line_type = cv2.LINE_AA if antialiased else cv2.LINE_4
    
    # Get frame sizing to convert normalized co-ords to pixels
    frame_height, frame_width = display_image.shape[0:2]
    frame_scaling = np.float32((frame_width - 1, frame_height - 1))
    
    # Scale xy-points to pixels
    xy_array_px = np.int32(np.round(np.float32(xy_points_norm) * frame_scaling))
    
    # Draw a polyline/filled polygon, depending on settings
    if fill_polygon:
        return cv2.fillPoly(display_image, [xy_array_px], color_bgr, line_type)
    return cv2.polylines(display_image, [xy_array_px], is_closed, color_bgr, thickness_px, line_type)

# .....................................................................................................................

def draw_circle(display_image, center_xy_norm,
                radius_px = 5, color_rgb = (255, 255, 0), thickness_px = 1, antialiased = True, **kwargs):
    
    # Convert color to bgr for opencv
    color_bgr = color_rgb[::-1]
    
    # Decide on line type
    line_type = cv2.LINE_AA if antialiased else cv2.LINE_4
    
    # Get frame sizing to convert normalized co-ords to pixels
    frame_height, frame_width = display_image.shape[0:2]
    frame_scaling = np.float32((frame_width - 1, frame_height - 1))
    
    # Scale xy-points to pixels
    center_xy_px = np.int32(np.round(np.float32(center_xy_norm) * frame_scaling))
    
    return cv2.circle(display_image, tuple(center_xy_px), radius_px, color_bgr, thickness_px, line_type)

# .....................................................................................................................

def draw_rectangle(display_image, top_left_norm, bottom_right_norm,
                   color_rgb = (255, 255, 0), thickness_px = 1, antialiased = False, **kwargs):
    
    # Convert color to bgr for opencv
    color_bgr = color_rgb[::-1]
    
    # Decide on line type
    line_type = cv2.LINE_AA if antialiased else cv2.LINE_4
    
    # Get frame sizing to convert normalized co-ords to pixels
    frame_height, frame_width = display_image.shape[0:2]
    frame_scaling = np.float32((frame_width - 1, frame_height - 1))
    
    # Scale xy-points to pixels
    tl_px = np.int32(np.round(np.float32(top_left_norm) * frame_scaling))
    br_px = np.int32(np.round(np.float32(bottom_right_norm) * frame_scaling))
    
    return cv2.rectangle(display_image, tuple(tl_px), tuple(br_px), color_bgr, thickness_px, line_type)

# .....................................................................................................................

def draw_text(display_image, message, text_xy_norm,
              align_horizontal = "center", align_vertical = "center",
              text_scale = 0.5, color_rgb = (255, 255, 255), thickness_px = 1, antialiased = True, **kwargs):
    
    # Hard-code font type
    text_font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Convert color to bgr for opencv
    color_bgr = color_rgb[::-1]
    
    # Decide on line type
    line_type = cv2.LINE_AA if antialiased else cv2.LINE_4
    
    # Get frame sizing to convert normalized co-ords to pixels
    frame_height, frame_width = display_image.shape[0:2]
    frame_scaling = np.float32((frame_width - 1, frame_height - 1))
    
    # Scale text-xy co-ordinates to pixels
    text_x_px, text_y_px = np.int32(np.round(np.float32(text_xy_norm) * frame_scaling))
    
    # Figure out text sizing for handling alignment
    (text_w, text_h), text_baseline = cv2.getTextSize(message, text_font, text_scale, thickness_px)
    
    # Figure out text x-location
    h_align_lut = {"left": 0, "center":  -int(text_w / 2), "right": -text_w}
    lowered_h_align = str(align_horizontal).lower()
    x_offset = h_align_lut.get(lowered_h_align, h_align_lut["left"])
    
    # Figure out text y-location
    v_align_lut = {"top": text_h, "center": text_baseline, "bottom": -text_baseline}
    lowered_v_align = str(align_vertical).lower()
    y_offset = v_align_lut.get(lowered_v_align, v_align_lut["top"])
    
    # Calculate final text postion
    text_pos = (1 + text_x_px + x_offset, 1 + text_y_px + y_offset)
    
    return cv2.putText(display_image, message, text_pos, text_font, text_scale, color_bgr, thickness_px, line_type)

# .....................................................................................................................

def draw_error_message(display_image, error_message):
    
    ''' Helper function used to return (blank) frames with error messages '''
    
    blank_frame = np.zeros_like(display_image)
    return draw_text(blank_frame, error_message, (0.5, 0.5), text_scale = 0.4, color_rgb = (255, 70, 20))

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

def apply_ghosting(background_image, frame_to_ghost,
                   brightness_scaling = 1.5, blur_size = 2, pixelation_factor = 3,
                   enable_ghosting = True,
                   **kwargs):
    
    # Bail if we're not actually ghosting
    if not enable_ghosting:
        return frame_to_ghost
    
    # Get frame sizing so we can scale the background image appropriately
    frame_height, frame_width = frame_to_ghost.shape[0:2]
    frame_wh = (frame_width, frame_height)
    scaled_bg = cv2.resize(background_image, dsize = frame_wh, interpolation = cv2.INTER_AREA)
    
    # Get frame difference
    frame_difference_3ch = cv2.absdiff(scaled_bg, frame_to_ghost)
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
    
    return ghosted_frame

# .....................................................................................................................

def save_one_jpg(save_folder_path, save_name, image_data):
    
    # Build the file name with the right extension and enough (left-sided) zero padding to avoid ordering errors
    save_file_name = "{}.jpg".format(save_name).rjust(20, "0")
    
    # Build pathing to save jpg file & save the image data
    save_path = os.path.join(save_folder_path, save_file_name)
    with open(save_path, "wb") as outfile:
        outfile.write(image_data)
    
    return save_path

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Video creation functions

# .....................................................................................................................

def create_video(save_folder_path, frame_rate):
    
    # Make sure the frame rate isn't silly
    frame_rate = min(30, max(0.5, frame_rate))
    
    # Build output name & pathing
    path_to_output = os.path.join(save_folder_path, "temp.mp4")
    
    # Build video output, with resizing if needed
    video_frames = ImageSequenceClip(save_folder_path, fps = frame_rate)
    video_frames.write_videofile(path_to_output, audio = False)
    
    return path_to_output

# .....................................................................................................................

def create_video_simple_replay(camera_select, snapshot_ems_list, enable_ghosting):
    
    # Hard-code 'simple' video parameters
    frame_rate = get_default_fps()
    ghost_config_dict = {"enable": enable_ghosting,
                         "brightness_scaling": 1.5,
                         "blur_size": 2,
                         "pixelation_factor": 3}
    
    try:
        
        # Grab a background image if we're ghosting
        bg_frame = None
        enable_ghosting = ghost_config_dict.get("enable", False)
        if enable_ghosting:
            last_snap_ems = snapshot_ems_list[-1]
            got_background, bg_bytes = get_background_image_bytes(camera_select, last_snap_ems)
            if not got_background:
                raise FileNotFoundError("Couldn't retrieve background image for ghosting!")
            bg_frame = image_bytes_to_pixels(bg_bytes)
    
        # Download each of the snapshot images to a temporary folder
        with TemporaryDirectory() as temp_dir:
            
            # Save a jpg for each of the provided epoch ms values
            for each_idx, each_snap_ems in enumerate(snapshot_ems_list):
                
                # Request image data from dbserver
                got_snapshot, snap_bytes = get_snapshot_image_bytes(camera_select, each_snap_ems)
                if not got_snapshot:
                    continue
                
                # Apply ghosting if needed
                if enable_ghosting:
                    snap_frame = image_bytes_to_pixels(snap_bytes)
                    ghost_frame = apply_ghosting(bg_frame, snap_frame, **ghost_config_dict)
                    snap_bytes = image_pixels_to_bytes(ghost_frame)
                
                # Save the jpgs!
                save_one_jpg(temp_dir, each_idx, snap_bytes)
            
            # Create the video file and return for download
            path_to_video = create_video(temp_dir, frame_rate)
            user_file_name = "simple_replay.mp4"
            video_response = send_file(path_to_video,
                                       attachment_filename = user_file_name,
                                       mimetype = "video/mp4",
                                       as_attachment = True)
        
    except Exception as err:
        # If anything goes wrong, return an error response instead
        error_type = err.__class__.__name__
        print("",  "{} (create_simple_video_response):".format(error_type), str(err), sep = "\n")
        error_msg = ["({}) Error creating simple replay video:".format(error_type), str(err)]
        video_response = error_response(error_msg, status_code = 500)
    
    return video_response

# .....................................................................................................................

def create_video_from_instructions(camera_select, instructions_list, frames_per_second, ghost_config_dict):
    
    try:
        
        # Grab a background image if we're ghosting
        bg_frame = None
        enable_ghosting = ghost_config_dict.get("enable", False)
        if enable_ghosting:
            last_snapshot_instruction = instructions_list[-1]
            last_snap_ems = last_snapshot_instruction.get("snapshot_ems", None)
            got_background, bg_bytes = get_background_image_bytes(camera_select, last_snap_ems)
            if not got_background:
                raise FileNotFoundError("Couldn't retrieve background image for ghosting!")
            bg_frame = image_bytes_to_pixels(bg_bytes)
        
        # Convert each base64 string into image data
        with TemporaryDirectory() as temp_dir:
            for each_idx, each_instruction_dict in enumerate(instructions_list):
                
                # Pull out instruction data (skip if snapshot epoch ms value is missing)
                drawing_list = each_instruction_dict.get("drawing", [])
                snapshot_ems = each_instruction_dict.get("snapshot_ems", None)
                if snapshot_ems is None:
                    continue
                
                # First retrieve snapshot
                got_snapshot, snap_bytes = get_snapshot_image_bytes(camera_select, snapshot_ems)
                if not got_snapshot:
                    continue
                
                # Convert to pixel data so we can work with the image and apply ghosting if needed
                display_frame = image_bytes_to_pixels(snap_bytes)
                if enable_ghosting:
                    display_frame = apply_ghosting(bg_frame, display_frame, **ghost_config_dict)
                
                # Interpret all drawing instructions
                for each_draw_call in drawing_list:
                    display_frame = interpret_drawing_call(display_frame, each_draw_call)
                
                # Save image data to file system
                save_name = "{}.jpg".format(each_idx).rjust(20, "0")
                save_path = os.path.join(temp_dir, save_name)
                cv2.imwrite(save_path, display_frame)
            
            # Create the video file and return for download
            path_to_video = create_video(temp_dir, frames_per_second)
            video_response = send_file(path_to_video,
                                       mimetype = "video/mp4",
                                       as_attachment = False)
        
    except Exception as err:
        # If anything goes wrong, return an error response instead
        error_type = err.__class__.__name__
        print("",  "{} (create_video_from_instructions):".format(error_type), str(err), sep = "\n")
        error_msg = ["({}) Error creating video from instructions:".format(error_type), str(err)]
        video_response = error_response(error_msg, status_code = 500)
    
    return video_response

# .....................................................................................................................

def create_video_response_from_b64_jpgs(base64_jpgs_list, frames_per_second):
    
    try:
        # Convert each base64 string into image data
        with TemporaryDirectory() as temp_dir:
            for each_idx, each_b64_jpg_string in enumerate(base64_jpgs_list):
                
                # Remove encoding prefix data
                data_prefix, base64_string = each_b64_jpg_string.split(",")
                image_bytes = base64.b64decode(base64_string)
                image_array = np.frombuffer(image_bytes, np.uint8)
                
                # Save image data to file system
                save_name = "{}.jpg".format(each_idx).rjust(20, "0")
                save_path = os.path.join(temp_dir, save_name)
                with open(save_path, "wb") as out_file:
                    out_file.write(image_array)
            
            # Create the video file and return for download
            path_to_video = create_video(temp_dir, frames_per_second)
            video_response = send_file(path_to_video,
                                       mimetype = "video/mp4",
                                       as_attachment = False)
        
    except Exception as err:
        # If anything goes wrong, return an error response instead
        error_type = err.__class__.__name__
        print("",  "{} (create_video_response_from_b64_jpgs):".format(error_type), str(err), sep = "\n")
        error_msg = ["({}) Error creating video from b64 jpgs:".format(error_type), str(err)]
        video_response = error_response(error_msg, status_code = 500)
    
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

@wsgi_app.route("/<string:camera_select>/simple-replay/<int:start_ems>/<int:end_ems>")
def simple_replay_route(camera_select, start_ems, end_ems):
    
    # Interpret ghosting flag
    enable_ghosting_str = flask_request.args.get("ghost", "true")
    enable_ghosting_bool = (enable_ghosting_str.lower() in {"1", "true", "on", "enable"})
    
    # Request snapshot timing info from dbserver
    snap_ems_list = get_snapshot_ems_list(camera_select, start_ems, end_ems)
    no_snapshots_to_download = (len(snap_ems_list) == 0)
    if no_snapshots_to_download:
        error_msg = "No snapshots in provided time range"
        return error_response(error_msg, status_code = 400)
    
    # Make sure snapshot times are ordered!
    snap_ems_list = sorted(snap_ems_list)
    
    return create_video_simple_replay(camera_select, snap_ems_list, enable_ghosting_bool)

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
                     " 'xy_points_norm': (list of xy pairs in normalized co-ordinates)",
                     " 'is_closed': (boolean),",
                     " 'color_rgb': (list of 3 values between 0-255),",
                     " 'thickness_px': (int, use -1 to fill),",
                     " 'antialiased': (boolean)",
                     "}",
                     "",
                     "{",
                     " 'type': 'circle',",
                     " 'center_xy_norm': (pair of xy values in normalized co-ordinates),",
                     " 'radius_px': (int),",
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
        error_msg = "Error! No camera selected"
        return error_response(error_msg, status_code = 400)
    
    # Bail if we got no frame instructions
    data_is_valid = (len(instructions_list) > 0)
    if not data_is_valid:
        error_msg = "Error! Did not find any drawing instructions"
        return error_response(error_msg, status_code = 400)
    
    # Use instructions to get target snapshots & draw overlay as needed
    return create_video_from_instructions(camera_select, instructions_list, frame_rate, ghost_config_dict)

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
        error_msg = "Error! Did not find any base64 jpgs data to render!"
        return error_response(error_msg, status_code = 400)
    
    return create_video_response_from_b64_jpgs(b64_jpgs_list, frame_rate)

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



