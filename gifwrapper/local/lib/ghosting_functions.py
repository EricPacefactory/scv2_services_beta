#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 14:12:34 2020

@author: eo
"""


# ---------------------------------------------------------------------------------------------------------------------
#%% Imports

import cv2

# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
#%% Ghosting functions

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
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Demo

if __name__ == "__main__":
    
    pass


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap


