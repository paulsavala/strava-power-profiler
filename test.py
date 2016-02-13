import pandas as pd
import numpy as np
from bokeh.plotting import figure, output_file, show
from bokeh.embed import components

short_df = pd.DataFrame.from_csv('stream.csv')
short_grad_df = short_df.diff().altitude / short_df.diff().distance
short_df['gradient'] = short_grad_df.replace(np.nan, 0)

long_df = pd.DataFrame.from_csv('stream2.csv')
long_grad_df = long_df.diff().altitude / long_df.diff().distance
long_df['gradient'] = long_grad_df.replace(np.nan, 0)

output_file('patch_bokeh.html')
p = figure()
p.patch([-3,0,2,0], [0,2,0,-1], line_width = 2, alpha = 0.5)
p.grid.bounds = (0, 0)
p.axis.minor_tick_line_color = None
p.xaxis.axis_label = ''
p.yaxis.axis_label = ''
show(p)

script, div = components(p)