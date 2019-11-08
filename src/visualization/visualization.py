from math import sqrt
import numpy as np
import matplotlib

import pandas as pd

# Matplotlib
import matplotlib.pyplot as plt
from matplotlib import style
from matplotlib import gridspec
plt.ioff()

style.use('seaborn')

import seaborn as sns
import math

from scipy import stats

'''
Available styles
['_classic_test', 'bmh', 'classic', 'dark_background', 'fast', 'fivethirtyeight', 'ggplot', 'grayscale', 'seaborn-bright', 'seaborn-colorblind', 'seaborn-dark-palette', 'seaborn-dark', 'seaborn-darkgrid', 'seaborn-deep', 'seaborn-muted', 'seaborn-notebook', 'seaborn-paper', 'seaborn-pastel', 'seaborn-poster', 'seaborn-talk', 'seaborn-ticks', 'seaborn-white', 'seaborn-whitegrid', 'seaborn', 'Solarize_Light2', 'tableau-colorblind10']
'''

# Plotly
import plotly.tools as tls
from plotly.subplots import make_subplots
import plotly.graph_objs as go
from plotly.offline import iplot
import plotly.io as pio
pio.renderers.default = "jupyterlab"

def targetDiagram(models, plot_train):

	def minRtarget(targetR):
		return sqrt(1+ np.power(targetR,2)-2*np.power(targetR,2))

	targetR20 = 0.5
	targetR0 = sqrt(targetR20)
	MR0 = minRtarget(targetR0)
	targetR21 = 0.7
	targetR1 = sqrt(targetR21)
	MR1 = minRtarget(targetR1)
	targetR22 = 0.9
	targetR2 = sqrt(targetR22)
	MR2 = minRtarget(targetR2)


	fig  = plot.figure(figsize=(13,13))
	for model in models:
		try:
			metrics_model = models[model]
		
			if plot_train == True:
				plt.scatter(metrics_model['train']['sign_sigma']*metrics_model['train']['RMSD_norm_unb'], metrics_model['train']['normalised_bias'], label = 'Train ' + model)
			plt.scatter(metrics_model['test']['sign_sigma']*metrics_model['test']['RMSD_norm_unb'], metrics_model['test']['normalised_bias'], label = 'Test ' + model)
		except:
			print ('Cannot plot model {}'.format(model))

	## Add circles
	ax = plt.gca()
	circle1 =plt.Circle((0, 0), 1, linewidth = 0.8, color='k', fill =False)
	circleMR0 =plt.Circle((0, 0), MR0, linewidth = 0.8, color='r', fill=False)
	circleMR1 =plt.Circle((0, 0), MR1, linewidth = 0.8, color='y', fill=False)
	circleMR2 =plt.Circle((0, 0), MR2, linewidth = 0.8, color='g', fill=False)
	
	circle3 =plt.Circle((0, 0), 0.01, color='k', fill=True)
	
	## Add annotations
	ax.add_artist(circle1)
	ax.annotate('R2 < 0',
				xy=(1, 0), xycoords='data',
				xytext=(-35, 10), textcoords='offset points')
	
	ax.add_artist(circleMR0)
	ax.annotate('R2 < ' + str(targetR20),
				xy=(MR0, 0), xycoords='data',
				xytext=(-35, 10), textcoords='offset points', color = 'r')
	
	ax.add_artist(circleMR1)
	ax.annotate('R2 < ' + str(targetR21),
				xy=(MR1, 0), xycoords='data',
				xytext=(-45, 10), textcoords='offset points', color = 'y')
	
	
	ax.add_artist(circleMR2)
	ax.annotate('R2 < ' + str(targetR22),
				xy=(MR2, 0), xycoords='data',
				xytext=(-45, 10), textcoords='offset points', color = 'g')
	ax.add_artist(circle3)
	
	## Display and others
	plt.axhline(0, color='black', linewidth = 0.5)
	plt.axvline(0, color='black', linewidth = 0.5)
	plt.legend(loc='best')
	plt.xlim([-1.1,1.1])
	plt.ylim([-1.1,1.1])
	plt.title('Target Diagram')
	plt.ylabel('Normalised Bias (-)')
	plt.xlabel("RMSD*'")
	plt.show()

def scatterDiagram(fig, gs, n, dataframeTrain, dataframeTest):
	ax = fig.add_subplot(gs[n])

	plt.plot(dataframeTrain['reference'], dataframeTrain['prediction'], 'go', label = 'Train ' + model_name, alpha = 0.3)
	plt.plot(dataframeTest['reference'], dataframeTest['prediction'], 'bo', label = 'Test ' + model_name, alpha = 0.3)
	plt.plot(dataframeTrain['reference'], dataframeTrain['reference'], 'k', label = '1:1 Line', linewidth = 0.4, alpha = 0.3)

	plt.legend(loc = 'best')
	plt.ylabel('Prediction (-)')
	plt.xlabel('Reference (-)')

class plot_wrapper():
	'''
		'plot_type': 
			- violin
			- timeseries
			- scatter_matrix
			- correlation_plot
			- heatmap
			- barplot
			- coherence_plot
		'plotting_library':
			- matplotlib
			- plotly
			- ?   
	'''
	
	def __init__(self, plot_description, verbose):
		self.library = plot_description['plotting_library']
		if self.library not in ['matplotlib', 'plotly']: raise SystemError ('Not supported library')
		self.type = plot_description['plot_type']
		if 'data' in plot_description.keys(): self.data = plot_description['data']
		self.options = plot_description['options']
		self.formatting = plot_description['formatting']
		self.df = pd.DataFrame()
		self.verbose = verbose
		self.subplots_list = None
		self.figure = None
		if 'style' in self.formatting.keys(): style.use(self.formatting['style'])
		
	def std_out(self, msg):
		if self.verbose: print(msg)
	
	def prepare_data(self, records):
		self.std_out('Preparing data for plot')
		# Check if there are different subplots
		n_subplots = 1
		for trace in self.data['traces']:
			if 'subplot' in self.data['traces'][trace].keys(): 
				n_subplots = max(n_subplots, self.data['traces'][trace]['subplot'])
				
			else: raise SystemError ('Trace not assigned to subplot')
		
		self.std_out('Making {} subplots'.format(n_subplots))
		
		# Generate list of subplots
		self.subplots_list = [[] for x in range(n_subplots)]

		# Get min_date and max_date
		if 'min_date' in self.options.keys(): min_date = self.options['min_date']
		else: min_date = None
		if 'max_date' in self.options.keys(): max_date = self.options['max_date']
		else: max_date = None
		
		# Put data in the df
		test = self.data['test']
		for trace in self.data['traces']:

			device = self.data['traces'][trace]['device']
			channel = self.data['traces'][trace]['channel']
			
			if device != 'all':
				# Put channel in subplots_list
				self.subplots_list[self.data['traces'][trace]['subplot']-1].append(channel + '_' + device)
				# Dataframe
				df = pd.DataFrame(records.readings[test]['devices'][device]['data'][channel].values, 
								  columns = [channel + '_' + device],
								  index = records.readings[test]['devices'][device]['data'].index)
				
				# Combine it in the df
				self.df = self.df.combine_first(df)
			
			else:
				for device_records in records.readings[test]['devices'].keys():
					if channel in records.readings[test]['devices'][device_records]['data'].columns:
						# Put channel in subplots_list
						self.subplots_list[self.data['traces'][trace]['subplot']-1].append(channel + '_' + device_records)
						# Dataframe
						df = pd.DataFrame(records.readings[test]['devices'][device_records]['data'][channel].values, 
										  columns = [channel + '_' + device_records],
										  index = records.readings[test]['devices'][device_records]['data'].index)

					# Combine it in the df
					self.df = self.df.combine_first(df)
		
		# Trim data
		if min_date != None: self.df = self.df[self.df.index > min_date]
		if max_date != None: self.df = self.df[self.df.index < max_date]
			
		# Resample it
		if self.options['target_raster'] != None: self.df.resample(self.options['target_raster']).mean()

	def clean_plot(self):
		# Clean matplotlib cache
		plt.clf()

	def export_plot(self):
		savePath = self.options['export_path']
		fileName = self.options['file_name']
		try:
			self.std_out('Exporting {} to {}'.format(fileName, savePath))
		
			if self.library == 'matplotlib': self.figure.savefig(savePath+ '/' + fileName + '.png', dpi = 300, transparent=True, bbox_inches='tight', pad_inches=0)
			elif self.library == 'plotly': pio.write_json(self.figure, savePath+ '/' + fileName + '.plotly')
		except:
			self.std_out('No export requested')

	def plot(self, records):

		# Correlation function for plot anotation
		def corrfunc(x, y, **kws):
			r, _ = stats.pearsonr(x, y)
			ax = plt.gca()
			ax.annotate("r = {:.2f}".format(r),
						xy=(.1, .9), xycoords=ax.transAxes)

		# Clean matplotlib cache
		plt.clf()

		# Parse options if the come from json. Workaround
		if "ylabel" in self.formatting.keys() and self.type != "correlation_plot":
			axises = self.formatting["ylabel"].keys()
			for axis in axises:
				self.formatting["ylabel"][int(axis)] = self.formatting["ylabel"].pop(axis)

		if "yrange" in self.formatting.keys() and self.type != "correlation_plot":
			axises = self.formatting["yrange"].keys()
			for axis in axises:
				self.formatting["yrange"][int(axis)] = self.formatting["yrange"].pop(axis)
		
		# Prepare data for plot
		if records is not None: self.prepare_data(records)
		n_subplots = len(self.subplots_list)

		# Generate plot depending on type and library
		self.std_out('Plotting')
		
		if self.type == 'timeseries':
			if self.library == 'matplotlib': 
				if self.formatting['width'] > 30: 
					self.std_out('Reducing width to 12')
					self.formatting['width'] = 12
				if self.formatting['height'] > 30: 
					self.std_out('Reducing height to 10')
					self.formatting['height'] = 10
				figure, axes = plt.subplots(n_subplots, 1, sharex = self.formatting['sharex'],
												  figsize=(self.formatting['width'], self.formatting['height']))
	
				if n_subplots == 1:
					for trace in self.subplots_list[0]:
						axes.plot(self.df.index, self.df[trace], label = trace)
						axes.legend(loc='center left', bbox_to_anchor=(1, 0.5))
						axes.set_ylabel(self.formatting['ylabel'][1])
						if 'yrange' in self.formatting.keys():
							axes.set_ylim(self.formatting['yrange'][1])
				else:
					for index_subplot in range(n_subplots):
						for trace in self.subplots_list[index_subplot]:
							axes[index_subplot].plot(self.df.index, self.df[trace], label = trace)
							axes[index_subplot].legend(loc='center left', bbox_to_anchor=(1, 0.5))
							axes[index_subplot].set_ylabel(self.formatting['ylabel'][index_subplot+1])
							if 'yrange' in self.formatting.keys():
								axes[index_subplot].set_ylim(self.formatting['yrange'][index_subplot+1])

				
				figure.suptitle(self.formatting['title'], fontsize=14)
				plt.xlabel(self.formatting['xlabel'])
				plt.grid(self.formatting['grid'])
				
				# Save it in global and show
				self.figure = figure
				if 'show_plot' in self.options:
					if self.options['show_plot']: plt.show()
			
			elif self.library == 'plotly':
				if self.formatting['width'] < 100: 
					self.std_out('Setting width to 800')
					self.formatting['width'] = 800
				if self.formatting['height'] <100: 
					self.std_out('Reducing height to 600')
					self.formatting['height'] = 600				
				figure = make_subplots(rows=n_subplots, cols=1, 
									   shared_xaxes = self.formatting['sharex'])
				# Add traces
				for index_subplot in range(n_subplots):
					for trace in self.subplots_list[index_subplot]:
						figure.append_trace({'x': self.df.index, 
											 'y': self.df[trace], 
											 'type': 'scatter', 
											 'name': trace}, 
											index_subplot + 1, 1)
					# Name the axis
					figure['layout']['yaxis' + str(index_subplot+1)]['title']['text'] = self.formatting['ylabel'][index_subplot+1]
					if 'yrange' in self.formatting.keys():
						figure['layout']['yaxis' + str(index_subplot+1)]['range'] = self.formatting['yrange'][index_subplot+1]

				# Add axis labels
				figure['layout']['xaxis' + str(n_subplots)]['title']['text'] = self.formatting['xlabel']
				
				# Add layout
				figure['layout'].update(height=self.formatting['height'],
										legend=dict(x=0.2, y=0, 
													traceorder='normal',
													font = dict(family='sans-serif',
																size=10,
																color='#000'),
													xanchor='center',
													orientation= 'h',
													itemsizing= 'trace',
													yanchor= 'bottom',
													bgcolor='rgba(0,0,0,0)',
													bordercolor='rgba(0,0,0,0)',
													borderwidth = 0),
										title=dict(text=self.formatting['title'])
									   )
				
				self.figure = figure
				if 'show_plot' in self.options:
					if self.options['show_plot']: figure.show()

		elif self.type == 'correlation_plot':
			g = sns.jointplot(self.df[self.subplots_list[0][0]], self.df[self.subplots_list[0][1]], 
						  data=self.df, kind=self.formatting['jpkind'], color="b", height=self.formatting['height'])


			# Set title
			g.fig.suptitle(self.formatting['title'])
			# Xlims
			# g.ax_joint.set_xlim(self.formatting['xrange'])
			g.ax_marg_x.set_xlim(self.formatting['xrange'])
			# Ylims
			# g.ax_joint.set_ylim(self.formatting['yrange'])
			g.ax_marg_y.set_ylim(self.formatting['yrange'])

			if self.library == 'plotly':
				plotly_fig = tls.mpl_to_plotly(g.fig)
				if 'show_plot' in self.options:
					if self.options['show_plot']: plotly_fig.show()
			elif self.library == 'matplotlib':
				# Save it in global and show
				self.figure = g.fig
				if 'show_plot' in self.options:
					if self.options['show_plot']: plt.show()

			if len(self.subplots_list) > 1: self.std_out('WARNING: Ignoring additional subplots')

		elif self.type == 'coherence_plot':
			figure = plt.figure(figsize=(self.formatting['width'], self.formatting['height']))

			cxy, f = plt.cohere(self.df[self.subplots_list[0][0]], self.df[self.subplots_list[0][1]], 512, 2, detrend = 'linear')
			plt.ylabel('Coherence [-]')
			# Set title
			figure.suptitle(self.formatting['title'])

			self.figure = figure
			if 'show_plot' in self.options:
					if self.options['show_plot']: plt.show()

			if len(self.subplots_list) > 1: self.std_out('WARNING: Ignoring additional subplots')

		elif self.type == 'scatter_matrix':

			if self.library == 'matplotlib':
				g = sns.pairplot(self.df.dropna(axis=0, how='all'), vars=self.df.columns[:], height=self.formatting['height'], plot_kws={'alpha': self.formatting['alpha']});
				g.map_upper(corrfunc)
				# g.map_lower(sns.residplot) 
				g.fig.suptitle(self.formatting['title'])
				if 'show_plot' in self.options:
					if self.options['show_plot']: plt.show();

				self.figure = g.fig;

			elif self.library == 'plotly':

				data = list()
				for column in self.df.columns:
					data.append(dict(label=column, values=self.df[column]))

				traces = go.Splom(dimensions=data,
									marker=dict(color='rgb(0,30,230, 0.35)',
									size=5,
									#colorscale=pl_colorscaled,
									line=dict(width=0.5,
											  color='rgb(230,230,230, 0.30)')),
									diagonal=dict(visible=False))
	
				layout = go.Layout(title=self.formatting['title'],
							dragmode='zoom',
							width=self.formatting['width'],
							height=self.formatting['height'],
							autosize=False,
							hovermode='closest',
							plot_bgcolor='rgba(240,240,240, 0.95)')

				self.figure = dict(data=[traces], layout=layout)
				if 'show_plot' in self.options:
					if self.options['show_plot']: iplot(self.figure)

		elif self.type == 'heatmap':

			if 'frequency_hours' in self.formatting.keys(): freq_time = self.formatting['frequency_hours']
			else: freq_time = 6

			# Include categorical variable
			if freq_time == 6:
				labels = ['Morning','Afternoon','Evening', 'Night']
			elif freq_time == 12:
				labels = ['Morning', 'Evening']
			else:
				labels = [str(i) for i in np.arange(0, 24, freq_time)]

			channel = self.df.columns[0]
			self.df = self.df.assign(session = pd.cut(self.df.index.hour, np.arange(0, 25, freq_time), labels = labels))
			
			# Group them by session
			df_session = self.df.groupby(['session']).mean()
			df_session = df_session[channel]

			## Full dataframe
			list_all = ['session', channel]

			# Check relative measurements

			if self.options['relative']:
				# Calculate average
				df_session_avg = df_session.mean(axis = 0)
				channel = channel + '_REL'

				list_all = list(self.df.columns)
				for column in self.df.columns:
					if column != 'session':
						self.df[column + '_REL'] = self.df[column]/df_session_avg
						list_all.append(column + '_REL')
				
			## Full dataframe
			self.df = self.df[list_all]
			self.df.dropna(axis = 0, how='all', inplace = True)
			
			if self.library == 'matplotlib':
				
				_, ax = plt.subplots(figsize=(self.formatting['width'],self.formatting['height']))         # Sample figsize in inches
				# Pivot with 'session'
				g = sns.heatmap(self.df.pivot(columns='session').resample('1D').mean().T, ax=ax)
				g.set_xticklabels([i.strftime("%Y-%m-%d") for i in self.df.resample('1D').mean().index])
				g.set_yticklabels(labels)
				g.set_ylabel('')
				# Set title
				g.figure.suptitle(self.formatting['title'])
				# Save it in global and show
				self.figure = g.figure
				if 'show_plot' in self.options:
					if self.options['show_plot']: plt.show()

			elif self.library =='plotly':
				colorscale = [[0, '#edf8fb'], [.3, '#b3cde3'],  [.6, '#8856a7'],  [1, '#810f7c']]

				# Data
				data = [
					go.Heatmap(
						z=self.df[channel],
						x=self.df.index.date,
						y=self.df['session'],
						colorscale=colorscale
					)
				]

				layout = go.Layout(
					title=self.formatting['title'],
					xaxis = dict(ticks=''),
					yaxis = dict(ticks='' , categoryarray=labels, autorange = 'reversed')
				)

				self.figure = go.Figure(data=data, layout=layout)
				if 'show_plot' in self.options:
					if self.options['show_plot']: iplot(self.figure)

		elif self.type == 'violin':

			if self.library == 'matplotlib':

				number_of_subplots = len(self.df.columns) 
				if number_of_subplots % 2 == 0: cols = 2
				else: cols = 3
				rows = int(math.ceil(number_of_subplots / cols))
				gs = gridspec.GridSpec(rows, cols)
				fig = plt.figure(figsize=(self.formatting['width'], self.formatting['height']*rows/2))

				fig.tight_layout()
				n = 0

				for column in self.df.columns:
					ax = fig.add_subplot(gs[n])
					n += 1
					g = sns.violinplot(y = self.df[column].values, ax = ax, inner="quartile")
					g.set_xticklabels([column])

				g.figure.suptitle(self.formatting['title'])

				# Save it in global and show
				self.figure = g.figure
				if 'show_plot' in self.options:
					if self.options['show_plot']: plt.show()
				
			elif self.library == 'plotly':
				print ('Nothing to see here')
