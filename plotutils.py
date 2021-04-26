import cmath
import numpy as np
from iumsutils import *
import matplotlib.pyplot as plt

class Multiplot:
    '''Base class for creating easily referenceable objects to subplot into. Effectively a wrapper for plt.subplots'''
    def __init__(self, nrows=None, ncols=None, span=None, figsize=5):
        if not (nrows or ncols):
            raise ValueError('At least one dimension is needed to specify a multiplot')
        elif bool(nrows) ^ bool(ncols): # if only one dimension is passed
            if not span:
                raise ValueError('Span is required when providing only one dimension')
            elif not nrows:
                nrows = ceildiv(span, ncols) # deduce required number of rows from number of columns
            elif not ncols:
                ncols = ceildiv(span, nrows) # deduce required number of columns from number of rows
        self.nrows, self.ncols = nrows, ncols
                
        self.fig, self.axes = plt.subplots(nrows, ncols, figsize=(figsize*ncols, figsize*nrows)) # dimensions must be backwards to scale properly
        self.axes = np.array(self.axes).reshape(nrows, ncols) # ensure that axes object has two dimensions, even in scalar/vector cases
        
    def draw(self, plot, index=(0,0)): 
        '''Wrapper for drawing plots in a more OOP-friendly? fashion. Relies upon the draw method for objects in this module being defined approriately'''
        if type(index) == int:
            index = divmod(index, self.ncols) # allow for linear indexing based on size        
        plot.draw(self.axes, index) #!!CRITICAL!! - prereq for all objects which follow is that they have a draw method which accepts and Axes object and an index
        
    def draw_series(self, plot_set):
        '''Used to plot an iterable of plot objects; leverages linear indexing capability'''
        for i, plot in enumerate(plot_set):
            self.draw(plot, index=i)
        
    def save(self, file_name, close=True):
        '''Wrapper for saving Multiplots'''
        self.fig.savefig(file_name)
        if close:
            plt.close() # by default, will close plots after saving to prevent clutter of the jupyter window and of memory
        
def single_plot(plot_obj, save_dir=None, figsize=20):
    '''Boilerplate for creating a 1-panel Multiplot, plotting a particular plot object, and saving it to a desired location'''
    mp = Multiplot(nrows=1, ncols=1, figsize=figsize)
    mp.draw(plot_obj)
    if save_dir:
        mp.save(save_dir)

    
# Radar Chart classes
class Mapped_Unit_Circle:
    '''Base background unit circle class used to create Radar Charts'''
    def __init__(self, mapping):
        self.mapping = mapping
        theta = np.linspace(0, cmath.tau, 100)
        self.circle = (np.cos(theta), np.sin(theta))  # generic black unit circle, preset for all SD objects
           
        self.N = len(mapping) 
        self.labels = tuple(mapping.keys())
        self.poles  = [cmath.exp(1j* i*cmath.tau/self.N) for i in range(self.N)] # poles at the Nth roots of unity
        
    def draw(self, ax):
        ax.plot(*self.circle, 'k-')
        for i, (label, pole) in enumerate(zip(self.labels, self.poles)): # pass the poles and axes to the internal unit circle
            x, y = pole.real, pole.imag # unpack components f values
            #ax.plot(x, y, 'ro')        # plot the roots of unity
            ax.plot([0, x], [0, y], 'y--')  # plot radial lines to each root
            ax.annotate(label, (x, y), ha='center') # label each root with the associated family, center horizontally

class Base_RC:
    '''Base Radar Chart class. Builds unit circle based on species mapping, can plot set of point along with unreduced centroid'''     
    unit_circle = None # !!CRITICAL!! - must set mapping for class prior to use
    
    @classmethod
    def set_uc_mapping(cls, mapping): # sets background unit circle mapping for class - !!NOTE!! must be prior to use in order for RCs to work
        cls.unit_circle = Mapped_Unit_Circle(mapping)
        
    def __init__(self, title, points, point_symbol='gx', centroid_symbol='b*'):
        self.title = title
        self.points = points
        
        self.point_symbol = point_symbol
        self.centroid = sum(self.points)/len(points)
        self.centroid_symbol = centroid_symbol
   
    def plot_point(self, coords, ax, symbol='ro', size=6):
        color, marker = symbol # unpack color and marker info from passed symbol - allows for tuple of color and marker to bypass single-character limit
        if type(coords) != tuple:
            coords = (coords.real, coords.imag)
        ax.plot(*coords, color=color, marker=marker, markersize=size) 
        
    def draw(self, axes, index=(0,0)):
        ax = axes[index] # index subplots within the passed plt.Axes object
        ax.set_title(self.title)
        
        if not ax.lines: # only draw a circle if one isn't already there; for overlay purposes. NOTE TO SELF: check if better param than "lines" exists
            self.unit_circle.draw(ax) # plot the unit circle background
        
        for point in self.points:
            self.plot_point(point, ax, symbol=self.point_symbol)
            
        if self.centroid_symbol: # only plot the centroid if it is called for
            self.plot_point(self.centroid, ax, symbol=self.centroid_symbol, size=14)
            
class Instance_RC(Base_RC):
    '''0-order Radar Chart class for plotting the axial components and single centroid of a single instance'''
    def __init__(self, dataset, inst_name, point_symbol='gx', centroid_symbol='b1'):
        aavs = dataset[get_family(inst_name)][isolate_species(inst_name)][inst_name] # perform the appropriate lookup for the species
        axial_points = [aav*pole for (aav, pole) in zip(aavs, Base_RC.unit_circle.poles)] # multiply aavs by axial conponents to obtain set of points
        
        super().__init__(inst_name, axial_points, point_symbol, centroid_symbol)
        self.centroid *= Base_RC.unit_circle.N # scale centroid by number of points in this case to better adhere to unit circle
        
class Species_RC(Base_RC):
    '''1-order Radar Chart class for plotting centroid of all instances of a species'''
    def __init__(self, dataset, species, point_symbol='b1', centroid_symbol='m*'):
        inst_centroids = [Instance_RC(dataset, instance).centroid for instance in dataset[get_family(species)][species]]
        super().__init__(species, inst_centroids, point_symbol, centroid_symbol)
        
class Family_RC(Base_RC):
    '''2-order Radar Chart class for plotting centroid of all instances of a family'''
    def __init__(self, dataset, family, point_symbol='m*', centroid_symbol='cs'):
        spec_centroids = [Species_RC(dataset, species).centroid for species in dataset[family]]
        super().__init__(family, spec_centroids, point_symbol, centroid_symbol)

class Overlaid_Family_RC(Base_RC):
    '''2.5-order Radar Chart class for plotting all families on a single diagram, color-coded '''
    colors = { # full color mapping given all currently supported chemical families
            'Acetates' : 'g', 
            'Alcohols' : 'r',
            'Aldehydes': 'c',
            'Alkanes'  : 'y',
            'Alkenes'  : 'tab:pink',
            'Alkynes'  : 'tab:purple',
            'Amines'   : 'lime',
            'Carboxylic Acids' : 'tab:orange',
            'Ethers'   : 'b',
            'Ketones'  : 'm'
    }
    point_marker = '^' # allows for easy interchange of marker symbols
    centroid_marker = 'x'
    
    def __init__(self, dataset, title='Family Overlay'):
        self.title = title
        self.point_symbols = {family : (self.colors[family], self.point_marker) for family in dataset}
        self.centroid_symbols = {family : (self.colors[family], self.centroid_marker) for family in dataset}
        self.famsds = [Family_RC(dataset, family, point_symbol=self.point_symbols[family], centroid_symbol=self.centroid_symbols[family]) for family in dataset]
    
    def draw(self, axes, index=(0,0)):
        ax = axes[index]
        for fsd in self.famsds:
            fsd.draw(axes, index) # draw over one another
        ax.set_title(self.title)
            
        symbols = [ax.scatter(np.nan, np.nan, color=color, marker=marker) for (color, marker) in self.point_symbols.values()] # plot fake points for legend
        ax.legend(symbols, self.point_symbols.keys(), loc='lower right')
        
class Macro_RC(Base_RC):
    '''3-order Radar Chart from plotting trends across all data'''
    def __init__(self, dataset, point_symbol='cs', centroid_symbol='gp'):
        fam_centroids = [Family_RC(dataset, family).centroid for family in dataset]
        super().__init__('All Families', fam_centroids, point_symbol, centroid_symbol) 
       
    
# Line Plot classes
class Line_Plot:
    '''Basic class for plotting lines, allows for multiple lines, scalable x-axis, and moveable legends, within the confines of the Multiplot framework'''
    def __init__(self, *args, x_range=None, title=None, legend_pos=None, colormap={'line' : 'c'}):
        self.lines = args
        self.x_data = None
        if x_range:
            self.x_data = list(np.linspace(*x_range, num=len(self.lines[0]))) # made into list to avoid annoying numpy multi-element truth value error
        
        self.legend_pos = legend_pos
        self.colormap = colormap
        self.title = title
        
    def draw(self, axes, index=(0,0)):
        ax = axes[index]
        ax.set_title(self.title)
        
        for line, (label, color) in zip(self.lines, self.colormap.items()):
            if self.x_data: 
                ax.plot(self.x_data, line, color, label=label)
            else:
                ax.plot(line, color, label=label)
            
        if self.legend_pos:
            ax.legend(loc=self.legend_pos)
            
class Single_Line_Plot(Line_Plot):
    '''Syntactic sugar for plotting a single line'''
    def __init__(self, line, title=None, legend_pos=None, label='line', color='c'):
        super().__init__(line, title=title, legend_pos=legend_pos, colormap={label : color})
        
class PWA_Plot(Line_Plot):
    '''Child class of Line_Plot for generating Point-Wise Aggregate spectral plots'''
    colormap={
        'Maxima' : 'b',
        'Averages' : 'r',
        'Minima' : 'g'
    }
    
    def __init__(self, spectra, species):
        self.spectra  = np.array(spectra)
        self.maxima   = np.amax(self.spectra, axis=0)
        self.averages = np.average(self.spectra, axis=0)
        self.minima   = np.amin(self.spectra, axis=0)
        super().__init__(self.maxima, self.averages, self.minima, title=species, legend_pos='upper right', colormap=self.colormap)
        
class Fermi_Plot(Single_Line_Plot):
    '''Child class of Single_Line_Plot for producing Fermi-Dirac plots from species-wide aavs'''
    def __init__(self, dataset, species, hotbit, precision=4):
        predictions = dataset[get_family(species)][species].values() # pull out a list of aavs      
        targets = [pred[hotbit] for pred in predictions]
        targets.sort(reverse=True) # arrange target aavs in descending order       
        
        n_correct = sum(max(pred) == pred[hotbit] for pred in predictions) # "correct" defined to be when true identity is assigned the highest probability
        n_total = len(predictions) 
        self.score = round(n_correct/n_total, precision)
        
        super().__init__(normalized(targets), title=f'{species}, {n_correct}/{n_total} correct', color='m-')
        
class Loss_Acc_Plot(Line_Plot):
    '''Child class of Single_Line_Plot for plotting training loss and accuracy'''
    colormap = {'Loss' : 'r', 'Accuracy' : 'g'}
    
    def __init__(self, losses, accuracies, evals):
        self.title = f'Loss, Acc={[round(i, 3) for i in evals]}'
        super().__init__(losses, accuracies, title=self.title, legend_pos='center right', colormap=self.colormap)
        
        
# Bar Chart classes
class Multibar: # this will serve as the base bar class, as ordinary bar graphs can be viewed as a special case of Multibars
    '''Class for plotting one or more bar graphs along the same main group labels. Takes the names of the group labels,
    the names of the sub-bar plots within each group, and the datasets (arbitrarily many), along with other parameters'''
    colors = ['b', 'r', 'g', 'y', 'm', 'c', 'k']
    bar_group_width = 0.8 # this should be less than 1 to prevent barset overlap
    
    def __init__(self, group_labels, sub_labels, *datasets, title=None, ylim=None, legend_pos=None):
        if len(datasets) != len(sub_labels):
            raise ValueError('Number of datasets must match number of sub labels')
         
        self.datasets     = datasets # unpacked, to allow for arbitrarily many (or few) inputs
        self.group_labels = group_labels
        self.sub_labels   = sub_labels
        self.n_bar_groups = len(group_labels)
        self.n_per_group  = len(sub_labels)
        
        self.bar_width = self.bar_group_width/self.n_per_group # width of an individual bar within a group
        self.x = np.arange(self.n_bar_groups)
        
        self.title = title
        self.ylim  = ylim
        self.legend_pos = legend_pos

    def draw(self, axes, index=(0,0)):
        ax = axes[index]

        ax.set_title(self.title)
        ax.set_xticks(self.x)
        ax.set_xticklabels(self.group_labels)

        for i, dataset in enumerate(self.datasets):
            offset = self.bar_width*(i - (self.n_per_group-1)/2) # amount to offset each set of bars from unit ticks
            ax.bar(self.x + offset, dataset, width=self.bar_width, color=self.colors[i], align='center')

        if self.ylim:
            ax.set_ylim(self.ylim)
        if self.legend_pos:
            ax.legend(self.sub_labels, loc=self.legend_pos)
            
class AAV_Bars(Multibar):
    '''class used for plotting bar charts of the AAVS of a particular species'''
    def __init__(self, inst_name, aavs, families): # NOTE TO SELF: the "inst_name" sub_label is really just a placeholder, consider inplementing more cleanly going forward
        super().__init__(families, [inst_name], aavs, title=inst_name, ylim=(0,1))
        
# miscellaneous/combined classes
def plot_and_get_score(species, spectra, dataset, metric_data, metric_final, savedir='.', metric_name='Error'):
    '''Rolls several classes into one convenient method for producing species summary plots and generating scores'''
    frame = Multiplot(nrows=2, ncols=2)

    radar_chart = Species_RC(dataset, species) # radar chart not created in-place to extract the hot bit
    hotbit = radar_chart.unit_circle.mapping[get_family(species)].index(1) # deduce hotbit from mapping and current species
    
    fermi_plot = Fermi_Plot(dataset, species, hotbit) # fermi plot not created in-place in order to extract the score
    score = fermi_plot.score
    
    metric_plot = Single_Line_Plot(metric_data, title=f'Final {metric_name}: {metric_final}', color='r')
    
    frame.draw(PWA_Plot(spectra, species), 0)
    frame.draw(metric_plot, 1)
    frame.draw(fermi_plot, 2)  
    frame.draw(radar_chart, 3)
    frame.save(f'{savedir}/{species}') # draw all four panels, then save the figure to the appropriate folder under the species' name
    plt.close() # prevent figure from displaying
    
    return score