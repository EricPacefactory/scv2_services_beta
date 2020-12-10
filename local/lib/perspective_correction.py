#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 10 11:02:47 2020

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
import numpy as np


# ---------------------------------------------------------------------------------------------------------------------
#%% Perspective correction functions

# .....................................................................................................................

def check_valid_quad(region_quad):
    
    ''' Function which checks if a provided quadrilateral is valid for perspective correction '''
    
    # Initialize outputs
    is_valid = False
    error_msg = "Unknown error with quad data"
    
    try:
        
        # For clarity
        is_iter = lambda x: type(x) in {list, tuple}
        is_number = lambda x: type(x) in {int, float}
        
        # Bail if quad draw is bad
        correct_data_type = is_iter(region_quad)
        if not correct_data_type:
            error_msg = "Did not find valid quad data!"
            return is_valid, error_msg
        
        # Check that all quad entries are iterables
        all_iters = all([is_iter(each_entry) for each_entry in region_quad])
        if not all_iters:
            error_msg = "quad entries are not xy pairs"
            return is_valid, error_msg
        
        # Bail if the quad is not a list of 4 two-tuples (i.e. xy pairs)
        is_list_of_4 = (len(region_quad) == 4)
        all_2_tuples = all([(len(each_entry) == 2) for each_entry in region_quad])
        correct_format = (is_list_of_4 and all_2_tuples)
        if not correct_format:
            error_msg = "quad is not properly formatted (must be 4 xy pairs)"
            return is_valid, error_msg
        
        # Bail on non-numeric x/y values
        xys_are_valid = all([(is_number(each_x) and is_number(each_y)) for each_x, each_y in region_quad])
        if not xys_are_valid:
            error_msg = "xy pairs must be floating point values (or integers)"
            return is_valid, error_msg
        
        # If we get here, the data is valid
        is_valid = (correct_data_type and correct_format and xys_are_valid)
        error_msg = None
        
    except (TypeError, AttributeError) as err:
        # Catch any casting/type errors
        print("", "Error validating quad points", str(err), sep = "\n", flush = True)
    
    return is_valid, error_msg

# .....................................................................................................................

def calculate_perspective_correction_factors(input_region_quad):
    
    # Initialize outputs
    is_valid = False
    in_to_out_warp_matrix = None
    out_to_in_warp_matrix = None
    
    # For clarity
    tl, tr, br, bl = input_region_quad
    input_region_array = np.float32((tl,tr,br,bl))
    
    # Build a matching 'output region' that we want our input co-ords to map to
    output_region_array = np.float32([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
        
    try:
        # Use OpenCV function to get the warping matrix, which maps input -> output, and also generate inverse
        in_to_out_warp_matrix = cv2.getPerspectiveTransform(input_region_array, output_region_array)
        out_to_in_warp_matrix = np.linalg.inv(in_to_out_warp_matrix)
        is_valid = True
        
    except np.linalg.LinAlgError:
        # Algebra errors imply impossible mapping, so don't try to return anything
        in_to_out_warp_matrix = np.float32([])
        out_to_in_warp_matrix = np.float32([])
        is_valid = False
    
    return is_valid, in_to_out_warp_matrix.tolist(), out_to_in_warp_matrix.tolist()

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Demo

if __name__ == "__main__":
    
    pass


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap


