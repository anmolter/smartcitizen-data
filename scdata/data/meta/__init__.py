from os.path import join
import yaml

from scdata.utils.dictmerge import dict_fmerge
from scdata.utils.out import std_out
from pandas import read_json
from scdata.utils.out import std_out
from os import pardir, environ
from os.path import join, abspath, dirname

def load_env(env_file):
    with open(env_file) as f:
        for line in f:
            if line.startswith('#') or not line.strip(): continue
            # Load to local environ
            key, value = line.strip().split('=', 1)
            environ[key] = value  

def get_paths():
    
    _paths = dict()
    _paths['rootDirectory'] = abspath(abspath(join(dirname(__file__), pardir, pardir, pardir)))
    _paths['dataDirectory'] = join(_paths['rootDirectory'], 'data')
    _paths['interimDirectory'] = join(_paths['dataDirectory'], 'interim')
    _paths['modelDirectory'] = join(_paths['rootDirectory'], 'models')
    
    load_env(join(_paths['rootDirectory'], '.env'))

    if 'inventory_path' in environ.keys():
        _paths['inventoryDirectory'] = environ['inventory_path']
    
    if 'tools_path' in environ.keys(): 
        _paths['toolsDirectory'] = environ['tools_path']

    return _paths

def load_blueprints():
    try:
        blueprints_path = join(paths['interimDirectory'], 'blueprints.yaml')
        with open(blueprints_path, 'r') as blueprints_yaml:
            blueprints = yaml.load(blueprints_yaml, Loader=yaml.SafeLoader)
    except:
        raise SystemError('Problem loading blueprints file')

    for blueprint in blueprints.keys():
        if 'expands' in blueprints[blueprint]: 
            blueprints[blueprint] = dict_fmerge(blueprints[blueprint], blueprints[blueprints[blueprint]['expands']])
            blueprints[blueprint].pop('expands')
            
    return blueprints

def load_calibrations():
    '''
        The calibrations are meant for alphasense's 4 electrode sensors.
        This file follows the next structure:
        {
            "Target 1": "Pollutant 1", 
            "Target 2": "Pollutant 2", 
            "Serial No": "XXXX", 
            "Sensitivity 1": "Pollutant 1 sensitivity in nA/ppm", 
            "Sensitivity 2": "Pollutant 2 sensitivity in nA/ppm", 
            "Zero Current": "in nA", 
            "Aux Zero Current": "in nA"}
        }
    '''
    caldata_path = join(paths['interimDirectory'], 'calibrations.json')
    caldf = read_json(caldata_path, orient='columns', lines = True)
    caldf.index = caldf['serial_no']

    return caldf

paths = get_paths()
calibrations = load_calibrations()
blueprints = load_blueprints()