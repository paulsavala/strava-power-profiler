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

@app_lulu.route('/connect')
def connect():
	return render_template('connect.html', connect_url = url)

@app_lulu.route('/authorization')
def authorization():
	code = request.args.get('code')
	access_token = client.exchange_code_for_token(client_id = 10117, \
		client_secret = 'dceb245a0fe67bcebb54a7c1af1d8a1a58025157', \
		code = code)
	app_lulu.vars['access_token'] = access_token
	return redirect('/graph_profile')

@app_lulu.route('/recent_activities')
def display_user():
	client = Client(access_token = app_lulu.vars['access_token'])
	athlete = client.get_athlete()
	activities = client.get_activities(limit=5)
	names = ' '.join([activity.name for activity in activities])
	return names
	
@app_lulu.route('/alt_stream')
def alt_stream():
	types = ['distance', 'altitude']
	stream = client.get_segment_streams(3944715, types = types, resolution = 'high')

	stream_dict = {}
	for type in types:
		stream_dict[type] = list(stream[type].data)
		
	stream_df = pd.DataFrame(stream_dict)
	stream_df.to_csv('stream2.csv')

	return 'Stream written to file'
	
@app_lulu.route('/graph_profile')
def graph_profile():

	p = figure()
	p.patch([-3,0,2,0], [0,2,0,-1], line_width = 2, alpha = 0.5)
 	#p.axis.minor_tick_line_color = None
  	#p.xaxis.axis_label = ''
 	#p.yaxis.axis_label = ''
	
	script, div = components(p)
	
	return render_template('layout.html', script = script, div = div)
		
# Settings for local Flask deployment (for testing)
if __name__ == "__main__":
	app_lulu.run(debug=True)