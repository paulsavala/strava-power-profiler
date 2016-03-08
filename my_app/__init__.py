# Import flask and template operators
from flask import Flask, render_template
from stravalib import Client

app = Flask(__name__)

# Connect to the views.py file to allow url routing
import my_app.views

app.vars = {}

# Strava API values
strava_secret_key = 'dceb245a0fe67bcebb54a7c1af1d8a1a58025157'
strava_client_id = 10117

app.vars['client_secret'] = strava_secret_key
app.vars['client_id'] = strava_client_id

DATABASE = 'database.db'