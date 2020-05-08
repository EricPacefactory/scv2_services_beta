#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  4 14:17:05 2020

@author: eo
"""


# ---------------------------------------------------------------------------------------------------------------------
#%% Imports

import requests
import signal
import argparse
import datetime as dt

from time import sleep
from random import random as unit_random

from local.lib.environment import get_dbserver_protocol, get_dbserver_host, get_dbserver_port
from local.lib.environment import get_days_to_keep, get_delete_on_startup, get_delete_once

# ---------------------------------------------------------------------------------------------------------------------
#%% Script control

# .....................................................................................................................

def parse_autodelete_args():
    
    # Hard-coded defaults
    default_days_to_keep = get_days_to_keep()
    default_delete_on_startup = get_delete_on_startup()
    default_delete_once = get_delete_once()
    
    # Get (environment-based) default values
    default_dbserver_protocol = get_dbserver_protocol()
    default_dbserver_host = get_dbserver_host()
    default_dbserver_port = get_dbserver_port()
    
    # Provide some extra information when accessing help text
    script_description = "A self-scheduling script which auto-deletes data from all cameras on a daily basis"
    
    # Construct the argument parser and parse the arguments
    ap_obj = argparse.ArgumentParser(description = script_description,
                                        formatter_class = argparse.RawTextHelpFormatter)
    
    ap_obj.add_argument("-proto", "--protocol",
                        default = default_dbserver_protocol,
                        type = str,
                        help = "\n".join(["Database server protocol", 
                                          "(Default: {})".format(default_dbserver_protocol)]))
    
    ap_obj.add_argument("-host", "--host",
                        default = default_dbserver_host,
                        type = str,
                        help = "\n".join(["Database server host/ip address", 
                                          "(Default: {})".format(default_dbserver_host)]))
    
    ap_obj.add_argument("-port", "--port",
                        default = default_dbserver_port,
                        type = int,
                        help = "\n".join(["Database server port", 
                                          "(Default: {})".format(default_dbserver_port)]))
    
    ap_obj.add_argument("-days", "--days_to_keep",
                        default = default_days_to_keep,
                        type = int,
                        help = "\n".join(["Number of days to keep, when requesting deletion", 
                                          "(Default: {})".format(default_days_to_keep)]))
    
    ap_obj.add_argument("-on_start", "--delete_on_startup",
                        default = default_delete_on_startup,
                        action = "store_true",
                        help = "\n".join(["If set, deletion will occur immediately on startup instead of waiting.",
                                          "May be set through environment variables.",
                                          "(Active: {})".format(default_delete_on_startup)]))
    
    ap_obj.add_argument("-once", "--delete_once",
                        default = default_delete_once,
                        action = "store_true",
                        help = "\n".join(["If set, deletion will occur immediately on startup, then close.",
                                          "Intended for manually running deletions.",
                                          "May be set through environment variables.",
                                          "(Active: {})".format(default_delete_once)]))
    
    # Convert argument results to a dictionary before returning
    ap_result = vars(ap_obj.parse_args())
    
    return ap_result

# .....................................................................................................................

def sigterm_quit(signal_number, stack_frame):
    
    '''
    Helper function, intended to be used if the script receives a SIGTERM command from the operating system.
    The function itself only raises a SystemExit error, which allows for SIGTERM events to be
    handled explicitly using a try/except statement!
      -> This is only expected to occur when running the 'scheduled_delete(...)'
    '''
    
    raise SystemExit

# .....................................................................................................................

def sleep_until_tomorrow(hour_to_wake = 2, random_sleep_mins = 30):
    
    '''
    Function which pauses execution until the next day from when it was called.
    Regularly wakes up to check if passed the wake timing
    (rather than doing one long sleep, which is prone to timing drift errors)
    '''
    
    # For clarity
    one_hour_of_seconds = (60 * 60)
    ten_mins_of_seconds = (10 * 60)
    
    # Generate the target datetime to wake from
    current_datetime = dt.datetime.now()
    tomorrow_dt = current_datetime + dt.timedelta(days = 1)
    wake_dt = dt.datetime(year = tomorrow_dt.year,
                          month = tomorrow_dt.month,
                          day = tomorrow_dt.day,
                          hour = hour_to_wake)
    
    # Add a random offset to the wake time, to help avoid synchronizing with other timers
    wake_offset_mins = (1.0 - unit_random()) * random_sleep_mins
    wake_dt = wake_dt + dt.timedelta(minutes = wake_offset_mins)
    
    # Repeatedly check if we've passed our wake time, otherwise stay sleeping
    while True:
        check_dt = dt.datetime.now()
        if check_dt > wake_dt:
            break
        random_seconds_of_sleep = (1.0 - unit_random()) * ten_mins_of_seconds
        sleep(one_hour_of_seconds + random_seconds_of_sleep)
    
    return

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Url builders

# .....................................................................................................................

def build_url(dbserver_url, *route_addons):
    
    # Force all add-ons to be strings
    addon_strs = [str(each_addon) for each_addon in route_addons]
    
    # Remove any leading/trails slashes from add-ons
    clean_addons = [each_addon.strip("/") for each_addon in addon_strs]
    
    # Combine add-ons to server url
    request_url = "/".join([dbserver_url, *clean_addons])
    
    return request_url

# .....................................................................................................................

def build_delete_url(dbserver_url, camera_select, collection_name, days_to_keep):
    
    days_to_keep_int = int(days_to_keep)
    delete_url = build_url(dbserver_url, camera_select, collection_name, "delete", "by-cutoff", days_to_keep_int)
    
    return delete_url

# .....................................................................................................................
# .....................................................................................................................
    

# ---------------------------------------------------------------------------------------------------------------------
#%% Helper functions

# .....................................................................................................................

def get_collections_to_delete():
    
    ''' Helper function which hard-codes the collections that need to be called/deleted '''
    
    return ["camerainfo", "backgrounds", "snapshots", "objects"]

# .....................................................................................................................

def get_camera_names(dbserver_url):
    
    # Initialize output
    camera_names_list = []
    
    # Build path to camera names route
    get_camera_names_url = build_url(dbserver_url, "get-all-camera-names")
    
    try:
        # Make request for camera names
        get_response = requests.get(get_camera_names_url)
        
        # Handle response
        response_code = get_response.status_code
        response_success = (response_code == 200)
        if response_success:
            # Convert json response data to python data type
            camera_names_list = get_response.json()
            
        else:
            # Feedback about bad responsess
            print("",
                  get_human_readable_datetime_string(),
                  "Bad response getting camera names! ({})".format(response_code),
                  "@ {}".format(get_camera_names_url),
                  "",
                  get_response.text,
                  sep = "\n")
        
    except Exception as err:
        # Try to fail gracefully in the case of unknown errors...
        print("",
              get_human_readable_datetime_string(),
              "Unknown error getting camera names!",
              "@ {}".format(get_camera_names_url),
              "",
              err,
              sep = "\n")
    
    return camera_names_list

# .....................................................................................................................

def get_response_feedback(response_dict, collection_name):
    
    '''
    Helper function for creating deletion feedback 
    Assumes responses formatted as follows (as an example):
        {
           "deletion_datetime":"2020-04-27 16:57:53",
           "deletion_epoch_ms":1588021073069,
           "time_taken_ms":1,
           "mongo_response": {
                                "acknowledged":true,
                                "deleted_count":0,
                                "raw_result": {
                                                 "n":0,
                                                 "ok":1.0
                                              }
                             }
        }
    '''
    
    # Pull out the raw data we want to print
    time_taken_ms = response_dict.get("time_taken_ms", -1)
    num_deleted = response_dict.get("mongo_response", {}).get("deleted_count", -1)
    
    return "{}: {} ms  /  {} entries deleted".format(collection_name, time_taken_ms, num_deleted)

# .....................................................................................................................
    
def get_human_readable_datetime_string():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Server connection helpers

# .....................................................................................................................

def check_server_connection(dbserver_url):
    
    ''' Helper function which checks that a server is accessible (for posting!) '''
    
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

def wait_for_server_connection(dbserver_url, mins_to_sleep_on_failure = 5):
    
    # Pre-calculate sleep time
    failure_sleep_time_sec = (mins_to_sleep_on_failure * 60)
    
    # Keep checking if the server is alive
    while True:
        server_is_alive = check_server_connection(dbserver_url)
        if server_is_alive:
            break
        
        # Some feedback, then wait an try again
        print("",
              get_human_readable_datetime_string(),
              "Couldn't connect to server, though this worked in the past...",
              "@ {}".format(dbserver_url),
              "",
              "Will try again in {} seconds".format(failure_sleep_time_sec),
              "", sep = "\n")
        sleep(failure_sleep_time_sec)
    
    return

# .....................................................................................................................
# .....................................................................................................................

# ---------------------------------------------------------------------------------------------------------------------
#%% Deletion functions

def make_delete_request(delete_url, camera_select, collection_name, timeout_sec = 500):
    
    # Initialize output
    response_feedback_str = "..."
    
    try:
        # Make request to delete each collection
        get_response = requests.get(delete_url, timeout = timeout_sec)
        
        # Handle response
        response_code = get_response.status_code
        response_success = (response_code == 200)
        if response_success:
            # Get feedback about response
            response_dict = get_response.json()
            response_feedback_str = get_response_feedback(response_dict, collection_name)
            
        else:
            # If we get a bad response code, just log it
            response_feedback_str = "Error: {} ({})".format(response_code, collection_name)
        
    except Exception as err:
        # Try to fail gracefully in the case of unknown errors...
        response_feedback_str = "Unknown error: {}".format(collection_name)
        print("",
              get_human_readable_datetime_string(),
              "Unknown error deleting {} for camera: {}".format(collection_name, camera_select),
              "@ {}".format(delete_url),
              "",
              err,
              sep = "\n")
    
    return response_feedback_str

# .....................................................................................................................

def delete_for_one_camera(dbserver_url, camera_select, days_to_keep,
                          timeout_mins = 30):
    
    # Calculate timeout value
    timeout_sec = (60 * timeout_mins)
    
    # Build all the deletion urls needed to clear this camera
    response_feedback_list = []
    collections_list = get_collections_to_delete()
    for each_collection in collections_list:
        
        # Build the url needed to trigger deletion for each collection
        delete_url = build_delete_url(dbserver_url, camera_select, each_collection, days_to_keep)
        response_str = make_delete_request(delete_url, camera_select, each_collection, timeout_sec)
        response_feedback_list.append(response_str)
    
    # Print some feedback
    print("",
          get_human_readable_datetime_string(),
          "Deletion results: {}".format(camera_select),
          "\n".join(response_feedback_list),
          sep = "\n")
    
    return

# .....................................................................................................................

def delete_for_all_cameras(dbserver_url, days_to_keep):
    
    # Check that we have a connection to the server before attempting to delete
    # Note: If we got here, we already passed the connection test on start-up
    #       --> So it makes sense to wait for a reconnect on failure
    wait_for_server_connection(dbserver_url)
    
    # Some feedback
    print("",
          get_human_readable_datetime_string(),
          "Deleting camera data...", 
          sep = "\n")
    
    # Delete data for every camera
    camera_names_list = get_camera_names(dbserver_url)
    for each_camera_name in camera_names_list:
        delete_for_one_camera(dbserver_url, each_camera_name, days_to_keep)
    
    return

# .....................................................................................................................

def scheduled_delete(dbserver_url, days_to_keep, delete_on_startup = False, run_once = False):
    
    # Register signal handler to catch termination events & exit gracefully
    signal.signal(signal.SIGTERM, sigterm_quit)
    
    # Run startup deletion if needed
    delete_now = (delete_on_startup or run_once)
    if delete_now:
        delete_for_all_cameras(dbserver_url, days_to_keep)
        
    # Close early if needed
    if run_once:
        print("", "Deletion finished!", "  Closing...", sep = "\n")
        return
    
    try:
        # Sleep & delete & sleep & delete & sleep & ...
        while True:
            sleep_until_tomorrow()
            delete_for_all_cameras(dbserver_url, days_to_keep)
            
    except KeyboardInterrupt:
        print("", "Keyboard cancelled!", "  Closing...",
              sep = "\n")
        
    except SystemExit:
        # Catch SIGTERM signals
        print("",
              get_human_readable_datetime_string(),
              "  Kill signal received!", "  Closing...",
              sep = "\n")
    
    return

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Get configuration
    
ap_result = parse_autodelete_args()

# Build dbserver url from script args
dbserver_protocol = ap_result["protocol"]
dbserver_host = ap_result["host"]
dbserver_port = ap_result["port"]
dbserver_url = "{}://{}:{}".format(dbserver_protocol, dbserver_host, dbserver_port)

# Get deletion settings
days_to_keep = ap_result["days_to_keep"]
delete_on_startup = ap_result["delete_on_startup"]
delete_once = ap_result["delete_once"]

# Print some feedback about configuration
print("",
      get_human_readable_datetime_string(),
      "Running autodeletion",
      "         server url: {}".format(dbserver_url),
      "       days to keep: {}".format(days_to_keep),
      "  delete on startup: {}".format(delete_on_startup),
      "        delete_once: {}".format(delete_once),
      sep = "\n")


# ---------------------------------------------------------------------------------------------------------------------
#%% *** Main call ***

# Make sure the server is active
server_is_alive = check_server_connection(dbserver_url)
if not server_is_alive:
    print("",
          get_human_readable_datetime_string(),
          "Failed to connect to server on startup!",
          "@ {}".format(dbserver_url),
          "",
          "Auto-delete cancelled!",
          "", "", "",
          sep = "\n")
    raise ConnectionError("Can't connect to server on startup!")

# Run deletion on repeating schedule, forever
scheduled_delete(dbserver_url, days_to_keep, delete_on_startup, delete_once)


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap
'''
STOPPED HERE
- NEED TO CHECK ON AUTODELETE IN CONTAINER, WHY DOES CONNECTION FAIL?
- THEN TRY AT MAPLE & IF NO IMMEDIATE ISSUES, MODATEK?
- THEN WORK ON ADDING BETTER DELETION ROUTES TO DBSERVER
- ALSO ADD TO GIT/GITHUB
'''
# TODO
# - add better deletion routing to dbserver...
#   - should ideally be a single route that handles all deletions
#   - maybe two routes? One by cut-off, another by timestamp???
# - should organize deletion routes into separate route file on dbserver as well...
# - dbserver could also record deletion event + metadata back into the db!
# - should add /<camera_select>/server-logs/<log_type>/... route to be able to retreve logs! Could also log posting...
