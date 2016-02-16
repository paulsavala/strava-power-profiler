# ==================- Helper functions -====================
# Convert a stream to a proper pandas df
def stream_to_df(stream):
	stream_dict = {}
	for type in stream.keys():
		stream_dict[type] = list(stream[type].data)
		
	stream_df = pd.DataFrame(stream_dict)
	
	return stream_df

# Compute the variability score
def get_var_score(grad_series):
	var_score = sum(grad_series.diff().fillna(0))
	return var_score
	
# Grades a hill according to how uphill / downhill it is
# "Large" positive values been long, steep climbs
# "Large" negative values mean long, steep descents
def get_hill_score(grad_series, dist_series):
	# We assume that grad_series is a pandas series holding the gradients
	# at each measurement, and that dist_series is the same for distances 
	# (measured at the same time)
	dist_diff = dist_series.diff().drop(0)
	grad_series = grad_series.drop(0)
	
	hill_score = sum(dist_diff * grad_series)
	
	return hill_score

# Fetch a segment by id and convert to a df	
def get_segment_df(id):
	stream = client.get_segment_streams(id, types=['distance', 'altitude'], resolution='high')
	segment_stream_df = stream_to_df(stream)
	segment_grad_df = segment_stream_df.diff()['altitude'] / segment_stream_df.diff()['distance']
	segment_stream_df['gradient'] = segment_grad_df.fillna(0)
	return segment_stream_df

# Returns all segment grades given an id
def grade_segment(id):
	segment_df = get_segment_df(id)
	hill_score = get_hill_score(segment_df['gradient'], segment_df['distance'])
	var_score = get_var_score(segment_df['gradient'])
	return hill_score, var_score
	
def get_segments_from_activities(activities):
	segments = []
	for activity in activities:
		activity = client.get_activity(activity.id) # For some reason you _have_ to get the activity again, otherwise the efforts are NoneType
		activity_efforts = activity.segment_efforts
		for effort in activity_efforts:
			hill_score, var_score = grade_segment(effort.segment.id)
			effort.hill_score = round(hill_score, 2)
			effort.var_score = round(100*var_score, 2)
			segments.append(effort)
	return segments
	
# This is a temporary, static graph acting as a placeholder
def placeholder_graph():
	p = figure(plot_width = 450, plot_height = 450)
	p.logo = None
	p.toolbar_location = None
	p.patch([-3,0,2,0], [0,2,0,-1], line_width = 2, alpha = 0.5)
	p.axis.minor_tick_line_color = None
	p.xaxis.axis_label = ''
	p.yaxis.axis_label = ''
	
	script, div = components(p)
	return script, div