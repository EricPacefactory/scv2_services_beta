#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 13:59:02 2020

@author: eo
"""


# ---------------------------------------------------------------------------------------------------------------------
#%% Add local path

import os
import sys

def find_path_to_local(target_folder = "local"):
    
    # Skip path finding if we successfully import the dummy file
    try:
        from local.dummy import dummy_func; dummy_func(); return
    except ImportError:
        print("", "Couldn't find local directory!", "Searching for path...", sep="\n")
    
    # Figure out where this file is located so we can work backwards to find the target folder
    file_directory = os.path.dirname(os.path.abspath(__file__))
    path_check = []
    
    # Check parent directories to see if we hit the main project directory containing the target folder
    prev_working_path = working_path = file_directory
    while True:
        
        # If we find the target folder in the given directory, add it to the python path (if it's not already there)
        if target_folder in os.listdir(working_path):
            if working_path not in sys.path:
                tilde_swarm = "~"*(4 + len(working_path))
                print("\n{}\nPython path updated:\n  {}\n{}".format(tilde_swarm, working_path, tilde_swarm))
                sys.path.append(working_path)
            break
        
        # Stop if we hit the filesystem root directory (parent directory isn't changing)
        prev_working_path, working_path = working_path, os.path.dirname(working_path)
        path_check.append(prev_working_path)
        if prev_working_path == working_path:
            print("\nTried paths:", *path_check, "", sep="\n  ")
            raise ImportError("Can't find '{}' directory!".format(target_folder))
            
find_path_to_local()

# ---------------------------------------------------------------------------------------------------------------------
#%% Imports

import cv2
import base64
import datetime as dt
import numpy as np

from tempfile import TemporaryDirectory

from moviepy.editor import ImageSequenceClip

from flask import send_file

from local.lib.environment import get_default_fps
from local.lib.request_helpers import get_snapshot_image_bytes, get_background_image_bytes
from local.lib.response_helpers import error_response
from local.lib.image_read_write import image_bytes_to_pixels, image_pixels_to_bytes, save_one_jpg
from local.lib.ghosting_functions import apply_ghosting
from local.lib.drawing_functions import interpret_drawing_call


# ---------------------------------------------------------------------------------------------------------------------
#%% Video creation functions

# .....................................................................................................................

def create_video(save_folder_path, frame_rate, print_message = "Creating video"):
    
    # Make sure the frame rate isn't silly
    frame_rate = min(30, max(0.5, frame_rate))
    
    # Build output name & pathing
    path_to_output = os.path.join(save_folder_path, "temp.mp4")
    
    # Print message to indicate video creation in logs
    dt_now = dt.datetime.now()
    timestamp_str = dt_now.strftime("%Y/%m/%d %H:%M:%S")
    print("", "{}  |  {}".format(timestamp_str, print_message), sep = "\n")
    
    # Build video output, with resizing if needed
    video_frames = ImageSequenceClip(save_folder_path, fps = frame_rate,)
    video_frames.write_videofile(path_to_output,
                                 audio = False,
                                 write_logfile = False,
                                 logger = None)
    
    return path_to_output

# .....................................................................................................................

def create_video_simple_replay(dbserver_url, camera_select, snapshot_ems_list, enable_ghosting):
    
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
            got_background, bg_bytes = get_background_image_bytes(dbserver_url, camera_select, last_snap_ems)
            if not got_background:
                raise FileNotFoundError("Couldn't retrieve background image for ghosting!")
            bg_frame = image_bytes_to_pixels(bg_bytes)
    
        # Download each of the snapshot images to a temporary folder
        with TemporaryDirectory() as temp_dir:
            
            # Save a jpg for each of the provided epoch ms values
            for each_idx, each_snap_ems in enumerate(snapshot_ems_list):
                
                # Request image data from dbserver
                got_snapshot, snap_bytes = get_snapshot_image_bytes(dbserver_url, camera_select, each_snap_ems)
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
            path_to_video = create_video(temp_dir, frame_rate, "Simple replay")
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

def create_video_from_instructions(dbserver_url, camera_select,
                                   instructions_list, frames_per_second, ghost_config_dict):
    
    try:
        
        # Grab a background image if we're ghosting
        bg_frame = None
        enable_ghosting = ghost_config_dict.get("enable", False)
        if enable_ghosting:
            last_snapshot_instruction = instructions_list[-1]
            last_snap_ems = last_snapshot_instruction.get("snapshot_ems", None)
            got_background, bg_bytes = get_background_image_bytes(dbserver_url, camera_select, last_snap_ems)
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
                got_snapshot, snap_bytes = get_snapshot_image_bytes(dbserver_url, camera_select, snapshot_ems)
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
            path_to_video = create_video(temp_dir, frames_per_second, "From instructions")
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
            path_to_video = create_video(temp_dir, frames_per_second, "From b64 jpgs")
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
#%% Demo

if __name__ == "__main__":
    
    pass


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap


