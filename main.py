from flask import Flask, request, redirect, render_template
from stravalib import Client, unithelper
import pandas as pd
from bokeh.plotting import figure, output_file, show
from bokeh.embed import components

app_lulu = Flask(__name__)

app_lulu.vars = {}

client = Client()
url = client.authorization_url(client_id = 10117, \
	redirect_uri = 'http://127.0.0.1:5000/authorization')

# ==================- Helper functions -====================

# Convert a stream to a proper pandas df
def stream_to_df(stream):
	stream_dict = {}
	for type in stream.keys():
		stream_dict[type] = list(stream[type].data)
		
	stream_df = pd.DataFrame(stream_dict)
	
	return stream_df

# ==================- Flask functions -=====================

# Have user connect with Strava
@app_lulu.route('/connect')
def connect():
	return render_template('connect.html', connect_url = url)

# Authentication and token exchange
@app_lulu.route('/authorization')
def authorization():
	my_client_id = 10117
	my_client_secret = 'dceb245a0fe67bcebb54a7c1af1d8a1a58025157'
	
	code = request.args.get('code')
	
	access_token = client.exchange_code_for_token(client_id = my_strava_client_id, \
		client_secret = my_client_secret, code = code)
	app_lulu.vars['access_token'] = access_token
	
	return redirect('/segment_stream')

# Get the users recent activities
@app_lulu.route('/recent_activities')
def recent_activities():
	num_activities = 5
	client = Client(access_token = app_lulu.vars['access_token'])
	athlete = client.get_athlete()
	
	activities = client.get_activities(limit = num_activities)
	
	return 'Got the 5 most recent activities'

# Get the stream for a SEGMENT
@app_lulu.route('/segment_stream')
def segment_stream():
	segment_id = 3944715
	types = ['distance', 'altitude']
	stream = client.get_segment_streams(segment_id, types = types, resolution = 'high')

	stream_df = stream_to_df(stream)

	return ('Got the stream for segment with id %d' % segment_id)
	
# Render the power profile chart page. Right now the chart is static.
@app_lulu.route('/graph_profile')
def graph_profile():

	p = figure(plot_width = 450, plot_height = 450)
	p.logo = None
	p.toolbar_location = None
	p.patch([-3,0,2,0], [0,2,0,-1], line_width = 2, alpha = 0.5)
 	#p.axis.minor_tick_line_color = None
  	#p.xaxis.axis_label = ''
 	#p.yaxis.axis_label = ''
	
	script, div = components(p)
	
	return render_template('layout.html', script = script, div = div)

# ======================- Housekeeping functions -=========================

# Settings for local Flask deployment (for testing)
if __name__ == "__main__":
	app_lulu.run(debug=True)