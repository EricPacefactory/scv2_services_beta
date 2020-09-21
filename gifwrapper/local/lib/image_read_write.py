#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 14:10:58 2020

@author: eo
"""


# ---------------------------------------------------------------------------------------------------------------------
#%% Imports

import os
import cv2
import numpy as np


# ---------------------------------------------------------------------------------------------------------------------
#%% I/O functions

# .....................................................................................................................

def image_bytes_to_pixels(image_bytes):
    
    ''' Helper function which convert raw image byte data to an actual image (represented as pixels) '''
    
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
#%% Demo

if __name__ == "__main__":
    
    pass


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap


