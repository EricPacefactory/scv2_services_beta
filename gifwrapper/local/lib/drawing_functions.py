#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 14:17:38 2020

@author: eo
"""


# ---------------------------------------------------------------------------------------------------------------------
#%% Imports

import cv2
import numpy as np


# ---------------------------------------------------------------------------------------------------------------------
#%% Drawing functions

# .....................................................................................................................


def typecast_arguments(arg_value_type_tuple_list):
    
    '''
    Function which typecasts arguments given in a list of tuples,
    where the first entry of each tuple is the provided argument value,
    and the second entry is the target type
    '''
    
    # Loop over each of the provided argument to check types & typecast if needed
    typecasted_values_list = []
    for each_value, each_type in arg_value_type_tuple_list:
        incorrect_type = (type(each_value) is not each_type)
        typecasted_value = each_type(each_value) if incorrect_type else each_value
        typecasted_values_list.append(typecasted_value)
    
    return typecasted_values_list

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
    
    # Force arguments to be correct types
    try:
        xy_points_norm, is_closed, color_rgb, thickness_px, antialiased = \
        typecast_arguments([(xy_points_norm, list),
                            (is_closed, bool),
                            (color_rgb, list),
                            (thickness_px, int),
                            (antialiased, bool)])
        
    except ValueError as err:
        error_message = "(polyline) Error: {}".format(str(err))
        return draw_error_message(display_image, error_message)
    
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
                radius_norm = 0.05, color_rgb = (255, 255, 0), thickness_px = 1, antialiased = True, **kwargs):
    
    # Force arguments to be correct types
    try:
        center_xy_norm, radius_norm, color_rgb, thickness_px, antialiased = \
        typecast_arguments([(center_xy_norm, list),
                            (radius_norm, float),
                            (color_rgb, list),
                            (thickness_px, int),
                            (antialiased, bool)])
        
    except ValueError as err:
        error_message = "(circle) Error: {}".format(str(err))
        return draw_error_message(display_image, error_message)
    
    # Convert color to bgr for opencv
    color_bgr = color_rgb[::-1]
    
    # Decide on line type
    line_type = cv2.LINE_AA if antialiased else cv2.LINE_4
    
    # Get frame sizing to convert normalized co-ords to pixels
    frame_height, frame_width = display_image.shape[0:2]
    frame_scaling = np.float32((frame_width - 1, frame_height - 1))
    
    # Calculate diagonal length and use it to determine radius in pixels
    frame_diagonal_px = np.sqrt(np.sum(np.square(frame_scaling)))
    radius_px = int(round(radius_norm * frame_diagonal_px))
    
    # Scale xy-points to pixels
    center_xy_px = np.int32(np.round(np.float32(center_xy_norm) * frame_scaling))
    
    return cv2.circle(display_image, tuple(center_xy_px), radius_px, color_bgr, thickness_px, line_type)

# .....................................................................................................................

def draw_rectangle(display_image, top_left_norm, bottom_right_norm,
                   color_rgb = (255, 255, 0), thickness_px = 1, antialiased = False, **kwargs):
    
    # Force arguments to be correct types
    try:
        top_left_norm, bottom_right_norm, color_rgb, thickness_px, antialiased = \
        typecast_arguments([(top_left_norm, list),
                            (bottom_right_norm, list),
                            (color_rgb, list),
                            (thickness_px, int),
                            (antialiased, bool)])
        
    except ValueError as err:
        error_message = "(rectangle) Error: {}".format(str(err))
        return draw_error_message(display_image, error_message)
    
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
              text_scale = 0.5, color_rgb = (255, 255, 255), bg_color_rgb = None, thickness_px = 1, antialiased = True,
              **kwargs):
    
    # Force arguments to be correct types
    try:
        message, text_xy_norm, align_horizontal, align_vertical, text_scale, color_rgb, thickness_px, antialiased = \
        typecast_arguments([(message, str),
                            (text_xy_norm, list),
                            (align_horizontal, str),
                            (align_vertical, str),
                            (text_scale, float),
                            (color_rgb, list),
                            (thickness_px, int),
                            (antialiased, bool)])
        
        # Handle background color typecase separately, since it can take multiple types
        if bg_color_rgb is not None:
            bg_color_rgb = tuple(bg_color_rgb)
        
    except ValueError as err:
        error_message = "(text) Error: {}".format(str(err))
        return draw_error_message(display_image, error_message)
    
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
    
    # Drawn background text, if needed
    if bg_color_rgb is not None:
        bg_thickness = (2 * thickness_px)
        cv2.putText(display_image, message, text_pos, text_font, text_scale, bg_color_rgb, bg_thickness, line_type)
    
    return cv2.putText(display_image, message, text_pos, text_font, text_scale, color_bgr, thickness_px, line_type)

# .....................................................................................................................

def draw_error_message(display_image, error_message):
    
    ''' Helper function used to return (blank) frames with error messages '''
    
    blank_frame = np.zeros_like(display_image)
    return draw_text(blank_frame, error_message, (0.5, 0.5), text_scale = 0.4, color_rgb = (255, 70, 20))

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Demo

if __name__ == "__main__":
    
    pass


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap


