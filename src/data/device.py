from src.saf import std_out, dict_fmerge, read_csv_file, export_csv_file
from src.saf import BLUEPRINTS, CHANNEL_LUT, MOLECULAR_WEIGHTS, UNIT_CONVERTION_LUT
from os.path import join

import pandas as pd
from traceback import print_exc
from re import search
from src.models.process import LazyCallable

class Device(object):
    def __init__(self, blueprint, descriptor):
        self.blueprint = blueprint

        # Set attributes
        for bpitem in BLUEPRINTS[blueprint]: self.__setattr__(bpitem, BLUEPRINTS[blueprint][bpitem]) 
        for ditem in descriptor.keys():
            if type(self.__getattribute__(ditem)) == dict: self.__setattr__(ditem, dict_fmerge(self.__getattribute__(ditem), descriptor[ditem]))
            else: self.__setattr__(ditem, descriptor[ditem])

        # Add API handler if needed
        if self.source == 'api':
            hmod = __import__('src.data.api', fromlist=['data.api'])
            Hclass = getattr(hmod, self.sources[self.source]['handler'])
            # Create object
            self.api_device = Hclass(did=self.id)

        self.readings = pd.DataFrame()
        self.loaded = False
        self.options = dict()

    def check_overrides(self, options = {}):
        if 'min_date' in options.keys(): self.options['min_date'] = options['min_date'] 
        else: self.options['min_date'] = self.min_date
        if 'max_date' in options.keys(): self.options['max_date'] = options['max_date']
        else: self.options['max_date'] = self.max_date
        if 'clean_na' in options.keys(): self.options['clean_na'] = options['clean_na']
        else: self.options['clean_na'] = self.clean_na
        if 'frequency' in options.keys(): self.options['frequency'] = options['frequency']
        else: self.options['frequency'] = self.frequency        
   
    def load(self, options = None, path = None, convert_units = True):
        # Add test overrides if we have them, otherwise set device defaults
        if options is not None: self.check_overrides(options)
        else: self.check_overrides()

        try:
            if self.source == 'csv':
                self.readings = self.readings.combine_first(read_csv_file(join(path, self.processed_data_file), self.location, self.options['frequency'], 
                                                            self.options['clean_na'], self.sources[self.source]['index']))
                if self.readings is not None:
                    self.convert_names()

            elif 'api' in self.source:
                if path is None:
                    df = self.api_device.get_device_data(self.options['min_date'], self.options['max_date'], self.options['frequency'], self.options['clean_na'])
                    # API Device is not aware of other csv index data, so make it here
                    if 'csv' in self.sources and df is not None: df = df.reindex(df.index.rename(self.sources['csv']['index']))
                    # Combine it with readings if possible
                    if df is not None: self.readings = self.readings.combine_first(df)
                else:
                    # Cached case
                    self.readings = self.readings.combine_first(read_csv_file(join(path, self.id + '.csv'), self.location, self.options['frequency'], 
                                                            self.options['clean_na'], self.sources['csv']['index']))
        
        except FileNotFoundError:
            std_out('File does not exist', 'ERROR')
            self.loaded = False
        except:
            print_exc()
            self.loaded = False
        else:
            if self.readings is not None: 
                self.loaded = True
                if convert_units: self.convert_units()
        finally:
            return self.loaded

    # TODO VERIFY
    def convert_names(self):
        rename = dict()
        for sensor in self.sensors: 
            if 'id' in self.sensors[sensor] and sensor in self.readings.columns: rename[self.sensors[sensor]['id']] = sensor
        self.readings.rename(columns=rename, inplace=True)

    # TODO VERIFY
    def convert_units(self):
        '''
            Convert the units based on the UNIT_LUT and blueprint
            NB: what is read/written from/to the cache is not converted.
            The files are with original units, and then converted in the device only
            for the readings but never chached like so.
        '''
        std_out('Checking if units need to be converted')

        for sensor in self.sensors.keys(): 

            for channel in CHANNEL_LUT.keys():
                if not (search(channel, sensor)): continue
                # Molecular weight in case of pollutants
                for pollutant in MOLECULAR_WEIGHTS.keys(): 
                    if search(channel, pollutant): 
                        molecular_weight = MOLECULAR_WEIGHTS[pollutant]
                        break
                    else: molecular_weight = 1
                
                # Check if channel is in look-up table
                if CHANNEL_LUT[channel] != self.sensors[sensor]['units']: 
                    std_out(f"Converting units for {sensor}. From {self.sensors[sensor]['units']} to {CHANNEL_LUT[channel]}")
                    for unit in UNIT_CONVERTION_LUT:
                        # Get units
                        if unit[0] == self.sensors[sensor]['units']: factor = unit[2]; break
                        elif unit[1] == self.sensors[sensor]['units']: factor = 1/unit[2]; break
                    # Convert channels
                    self.readings.rename(columns={sensor: sensor + '_RAW'}, inplace=True)
                    self.readings.loc[:, sensor] = self.readings.loc[:, sensor + '_RAW']*factor/molecular_weight
                else: std_out(f"No units conversion needed for {sensor}")
    
    def process(self):
        process_ok = True

        if 'metrics' not in vars(self): 
            std_out(f'Device {self.id} has nothing to process. Skipping', 'WARNING')
            return process_ok
            
        std_out('---------------------------')
        std_out(f'Processing device {self.id}')
        for metric in self.metrics:
            std_out(f'Processing {metric}')
            process_ok &= self.add_metric({metric: self.metrics[metric]})
        return process_ok

    def add_metric(self, metric = dict()):
        try:
            metricn = next(iter(metric.keys()))
            funct = LazyCallable(f"src.models.process.{metric[metricn]['process']}")
        except:
            print_exc()
            return False

        args, kwargs = list(), dict()
        
        if 'args' in metric[metricn]: args = metric[metricn]['args']
        if 'kwargs' in metric[metricn]: kwargs = metric[metricn]['kwargs']

        self.readings[metricn] = funct(self.readings, *args, **kwargs)
        
        if metricn in self.readings: return True
        return False

    def del_metric(self, metricn = ''):
        if metricn in self.readings.columns: self.readings.__delitem__(metricn)
        
        if metricn not in self.readings: return True
        return False        

    def export(self, path = '', forced_overwrite = False):
        # Export device
        return export_csv_file(path, self.id, self.readings, forced_overwrite = forced_overwrite)

    # TODO
    def capture(self):
        std_out('Not yet', 'ERROR')