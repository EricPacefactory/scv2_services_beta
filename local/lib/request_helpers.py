#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 13:49:36 2020

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

import requests

from time import sleep

from local.lib.url_helpers import build_snap_ems_list_url, build_snap_image_url, build_bg_image_url


# ---------------------------------------------------------------------------------------------------------------------
#%% Request functions

# .....................................................................................................................

def check_server_connection(dbserver_url, feedback_on_error = True):
    
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
        
    except requests.ConnectionError:
        if feedback_on_error:
            print("",
                  "Error connecting to server:",
                  connection_str_for_errors,
                  sep = "\n")
        
    except requests.exceptions.ReadTimeout:
        if feedback_on_error:
            print("",
                  "Timeout error connecting to server:",
                  connection_str_for_errors,
                  sep = "\n")
    
    return server_is_alive

# .....................................................................................................................

def connect_to_dbserver(dbserver_url, max_connection_attempts = 10, connection_retry_delay_sec = 12):
    
    # Initialize output
    connection_success = False
    
    # Check connection to the dbserver
    for k in range(max_connection_attempts):
        connection_success = check_server_connection(dbserver_url, feedback_on_error = False)
        if connection_success:
            break
        
        # Provide feedback about connection attempt failure
        print("", "No connection to dbserver!", "@ {}".format(dbserver_url), sep ="\n")
        
        # If we're going to retry the connection, provide additional feedback
        connection_attempt = (1 + k)
        will_retry = (connection_attempt < max_connection_attempts)
        if will_retry:
            print("--> Retrying (attempt {})...".format(connection_attempt))
            sleep(connection_retry_delay_sec)
    
    # Print a warning if we don't manage to conenct to the dbserver
    if not connection_success:
        print("", 
              "*" * 52,
              "Warning:",
              "  Starting server without connection to dbserver!!!",
              "*" * 52, sep = "\n")
    
    return connection_success

# .....................................................................................................................

def get_snapshot_ems_list(dbserver_url, camera_select, start_ems, end_ems):
    
    # Initialize output
    snapshot_ems_list = []
    
    # Build the request url & make the request
    snapshot_ems_list_request_url = build_snap_ems_list_url(dbserver_url, camera_select, start_ems, end_ems)
    dbserver_response = requests.get(snapshot_ems_list_request_url)
    
    # Only return the response data if the response was ok
    response_success = (dbserver_response.status_code == 200)
    if response_success:
        snapshot_ems_list = dbserver_response.json()
    
    return snapshot_ems_list

# .....................................................................................................................

def get_snapshot_image_bytes(dbserver_url, camera_select, snapshot_epoch_ms):
    
    # Initialize output
    image_bytes = None
    
    # Build the request url & make the request
    image_request_url = build_snap_image_url(dbserver_url, camera_select, snapshot_epoch_ms)
    dbserver_response = requests.get(image_request_url)
    
    # Only return the response data if the response was ok
    response_success = (dbserver_response.status_code == 200)
    if response_success:
        image_bytes = dbserver_response.content
    
    return response_success, image_bytes

# .....................................................................................................................

def get_background_image_bytes(dbserver_url, camera_select, target_epoch_ms):
    
    # Initialize output
    image_bytes = None
    
    # Build the request url & make the request
    image_request_url = build_bg_image_url(dbserver_url, camera_select, target_epoch_ms)
    dbserver_response = requests.get(image_request_url)
    
    # Only return the response data if the response was ok
    response_success = (dbserver_response.status_code == 200)
    if response_success:
        image_bytes = dbserver_response.content
    
    return response_success, image_bytes

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Demo

if __name__ == "__main__":
    
    pass
    


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap

