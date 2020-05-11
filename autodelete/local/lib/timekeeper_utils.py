#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  4 14:18:24 2020

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

import time
import datetime as dt

from random import random as unit_random


# ---------------------------------------------------------------------------------------------------------------------
#%% Time keeper functions

# .....................................................................................................................
    
def get_local_datetime():

    ''' Returns a datetime object based on the local time, with timezone information included '''

    return dt.datetime.now(tz = get_local_tzinfo())

# .....................................................................................................................

def get_local_tzinfo():
    
    ''' Function which returns a local tzinfo object. Accounts for daylight savings '''
    
    # Figure out utc offset for local time, accounting for daylight savings
    is_daylight_savings = time.localtime().tm_isdst
    utc_offset_sec = time.altzone if is_daylight_savings else time.timezone
    utc_offset_delta = dt.timedelta(seconds = -utc_offset_sec)
    
    return dt.timezone(offset = utc_offset_delta)

# .....................................................................................................................

def get_cutoff_timestamp(days_to_keep):
    
    ''' Function used to figure out the epoch_ms timestamp used for deletion '''
    
    # Calculate cutoff as delta for easier calculations
    day_cutoff_timedelta = dt.timedelta(days = abs(days_to_keep))
    
    # Figure out today's date and get timing of 'midnight'
    current_dt = get_local_datetime()
    midnight_dt = dt.datetime(year = current_dt.year, month = current_dt.month, day = current_dt.day)
    
    # Calculate cut-off datetime and convert to epoch_ms value
    deletion_cutoff_dt = midnight_dt - day_cutoff_timedelta
    deletion_timestamp_sec = deletion_cutoff_dt.timestamp()
    deletion_timestamp_ms = int(round(deletion_timestamp_sec * 1000))
    
    # Generate human-readable string representing the cutoff date
    deletion_dt_str = deletion_cutoff_dt.strftime("%Y/%m/%d %H:%M:%S")
    
    return deletion_timestamp_ms, deletion_dt_str

# .....................................................................................................................

def get_human_readable_datetime_now_string():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Delay functions

# .....................................................................................................................

def sleep_until_tomorrow(hour_to_wake = 1, random_sleep_mins = 30):
    
    '''
    Function which pauses execution until the next day from when it was called.
    Regularly wakes up to check if passed the wake timing
    (rather than doing one long sleep, which is prone to timing drift errors)
    '''
    
    # For clarity
    wait_fraction = 0.75
    transistion_timedelta = dt.timedelta(minutes = 30)
    margin_of_error_timedelta = dt.timedelta(minutes = 1)
    
    # Generate the target datetime to wake from
    current_datetime = dt.datetime.now()
    tomorrow_dt = current_datetime + dt.timedelta(days = 1)
    wake_dt = dt.datetime(year = tomorrow_dt.year,
                          month = tomorrow_dt.month,
                          day = tomorrow_dt.day,
                          hour = hour_to_wake)
    
    # Add a random offset to the wake time, to help avoid synchronizing with other timers
    random_wake_offset_mins = (1.0 - unit_random()) * random_sleep_mins
    randomized_wake_dt = wake_dt + dt.timedelta(minutes = random_wake_offset_mins)
    
    # Some feedback
    nice_wake_dt_str = randomized_wake_dt.strftime("%Y/%m/%d %H:%M:%S")
    print("",
          "Sleeping until (roughly): {}".format(nice_wake_dt_str),
          sep = "\n")
    
    # Repeatedly check if we've passed our wake time, otherwise stay sleeping
    while True:
        
        # Exit loop (and function!) once we've passed the wake datetime
        check_dt = dt.datetime.now()
        if check_dt > randomized_wake_dt:
            break
        
        # Determine sleep time until next wake-up-check, based on a fraction of the time remaining
        # (though if we're 'close' to the wake time, just wait the actual remaining time + a bit extra)
        time_remaining_timedelta = randomized_wake_dt - check_dt
        time_to_wait_timedelta = (time_remaining_timedelta * wait_fraction)
        should_wait_for_actual_time_remaining = (time_to_wait_timedelta < transistion_timedelta)
        if should_wait_for_actual_time_remaining:
            time_to_wait_timedelta = time_remaining_timedelta + margin_of_error_timedelta
        
        # Do the actual sleeping!
        time_to_wait_seconds = time_to_wait_timedelta.total_seconds()
        time.sleep(time_to_wait_seconds)
    
    return

# .....................................................................................................................
# .....................................................................................................................

# ---------------------------------------------------------------------------------------------------------------------
#%% Demo

if __name__ == "__main__":
    pass

# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap


