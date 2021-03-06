#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 13:59:17 2020

@author: eo
"""


# ---------------------------------------------------------------------------------------------------------------------
#%% Imports

from flask import jsonify


# ---------------------------------------------------------------------------------------------------------------------
#%% Response functions

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
#%% Demo

if __name__ == "__main__":
    
    pass


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap


