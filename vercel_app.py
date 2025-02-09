import streamlit as st
from app import *  # This imports all the app functionality

# This is the entry point for Vercel
def app():
    return st._get_scriptrunner().get_script_run_ctx().get_app()