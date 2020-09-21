#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 13:51:32 2020

@author: eo
"""


# ---------------------------------------------------------------------------------------------------------------------
#%% Imports



# ---------------------------------------------------------------------------------------------------------------------
#%% URL Helpers

# .....................................................................................................................

def build_dbserver_url(dbserver_url, *url_components):
    
    ''' Helper function for building urls to the dbserver '''
    
    return "/".join([dbserver_url, *url_components])

# .....................................................................................................................

def build_snap_ems_list_url(dbserver_url, camera_select, start_ems, end_ems):
    
    ''' Helper function for generating the url to request a list of snapshot epoch ms values in a time range '''
    
    return build_dbserver_url(dbserver_url, camera_select,
                              "snapshots", "get-ems-list", "by-time-range",
                              str(start_ems), str(end_ems))

# .....................................................................................................................

def build_snap_image_url(dbserver_url, camera_select, snapshot_epoch_ms):
    
    ''' Helper function for generating urls to download snapshot image data '''
    
    return build_dbserver_url(dbserver_url, camera_select,
                              "snapshots", "get-one-image", "by-ems", str(snapshot_epoch_ms))

# .....................................................................................................................

def build_bg_image_url(dbserver_url, camera_select, target_epoch_ms):
    
    ''' Helper function for generating urls to download background image data '''
    
    ems_str = str(target_epoch_ms)
    return build_dbserver_url(dbserver_url, camera_select,
                              "backgrounds", "get-active-image", "by-time-target", ems_str)

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Demo

if __name__ == "__main__":
    
    pass


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap


