from src.saf import std_out, calculate_distance
from src.saf import CURRENT_NAMES, FREQ_CONV_LUT, BLUEPRINTS
import pandas as pd
import math
from traceback import print_exc
import requests
from tzwhere import tzwhere
from re import search
import io

'''
About the classes in this file:
Each of the object interacts with a separate API.
There should be at minimum the following properties:
- id: identifier against the API
- location: timezone
- sensors: dictionary used to convert the names to saf standard (see saf.py and blueprints.yml) {api_name: saf_name}
- data: pandas dataframe containing the data. Columns = pollutants or sensors; index = localised timestamp
Methods
- get_device_data(start_date, end_date, frequency, clean_na): returns clean pandas dataframe (self.data) with start and end date filtering, and rollup
- get_device_location: returns timezone for timestamp geolocalisation

The units should not be converted here, as they will be later on converted in device.py
If you want to support caching, see get_device_data in ScApiDevice
'''

class ScApiDevice:

    API_BASE_URL='https://api.smartcitizen.me/v0/devices/'

    def __init__ (self, did):
        self.id = did
        self.kit_id = None
        self.mac = None
        self.last_reading_at = None
        self.added_at = None
        self.location = None
        self.lat = None
        self.long = None
        self.data = None
        self.sensors = None
        self.devicejson = None
    
    @staticmethod
    def get_world_map(min_date = None, max_date = None, city = None, within = None, tags = None, tag_method = 'any'):
        """
        Gets devices from Smart Citizen API with certain requirements
        Parameters
        ----------
            min_date: string, datetime-like object, optional
                None
                Minimum date to filter out the devices. Device started posted before min_date
            max_date: string, datetime-like object, optional
                None
                Maximum date to filter out the devices. Device posted after max_date
            city: string, optional
                Empty string
                City
            within: tuple
                Empty tuple
                Gets the devices within a circle center on lat, long with a radius_meters
                within = tuple(lat, long, radius_meters)
            tags: list of strings
                None
                Tags for the device (system or user). Default system wide are: indoor, outdoor, online, and offline
            tag_method: string
                'any'
                'any' or 'all'. Checks if 'all' the tags are to be included in the tags or it could be any
        Returns
        -------
            A list of kit IDs that comply with the requirements. If no requirements are set, returns all of them
        """
        def is_within_circle(x, within):
            if math.isnan(x['latitude']): return False
            if math.isnan(x['longitude']): return False
        
            return calculate_distance(location_A=(within[0], within[1]), location_B=(x['latitude'], x['longitude']))<within[2]
    
        world_map = requests.get('https://api.smartcitizen.me/v0/devices/world_map')
        
        df = pd.DataFrame(world_map.json()).set_index('id')
        
        # Filter out dates
        if min_date is not None: df=df[(min_date > df['added_at'])]
        if max_date is not None: df=df[(max_date < df['last_reading_at'])]
            
        # Location
        if city is not None: df=df[(df['city']==city)]
        if within is not None:

            df['within'] = df.apply(lambda x: is_within_circle(x, within), axis=1)
            df=df[(df['within']==True)]
        
        # Tags
        if tags is not None: 
            if tag_method == 'any':
                df['has_tags'] = df.apply(lambda x: any(tag in x['system_tags']+x['user_tags'] for tag in tags), axis=1)
            elif tag_method == 'all':
                df['has_tags'] = df.apply(lambda x: all(tag in x['system_tags']+x['user_tags'] for tag in tags), axis=1)
            df=df[(df['has_tags']==True)]
        
        return list(df.index)
    
    def get_mac(self):
        if self.mac is None:
            std_out(f'Requesting MAC from API for device {self.id}')
            # Get device
            try:
                deviceR = requests.get(self.API_BASE_URL + '{}/'.format(self.id))

                # If status code OK, retrieve data
                if deviceR.status_code == 200 or deviceR.status_code == 201:
                    if 'hardware_info' in deviceR.json().keys(): self.mac = deviceR.json()['hardware_info']['mac']
                    std_out ('Device {} is has this MAC {}'.format(self.id, self.mac))
                else:
                    std_out('API reported {}'.format(deviceR.status_code), 'ERROR')  
            except:
                std_out('Failed request. Probably no connection', 'ERROR')
                pass

        return self.mac

    def get_device_json(self):
        if self.devicejson is None:
            try:
                deviceR = requests.get(self.API_BASE_URL + '{}/'.format(self.id))
                if deviceR.status_code == 200 or deviceR.status_code == 201:
                    self.devicejson = deviceR.json()
                else: 
                    std_out('API reported {}'.format(deviceR.status_code), 'ERROR')  
            except:
                std_out('Failed request. Probably no connection', 'ERROR')  
                pass                
        return self.devicejson

    def get_kit_ID(self):

        if self.kit_id is None:
            if self.get_device_json() is not None:
                self.kit_id = self.devicejson['kit']['id']                
        
        return self.kit_id

    def get_device_last_reading(self):

        if self.last_reading_at is None:
            if self.get_device_json() is not None:
                self.last_reading_at = self.devicejson['last_reading_at']                
        
        std_out ('Device {} has last reading at {}'.format(self.id, self.last_reading_at))

        return self.last_reading_at

    def get_device_location(self):

        if self.location is None:
            latitude, longitude = self.get_device_lat_long()
            # Localize it
            tz_where = tzwhere.tzwhere()
            self.location = tz_where.tzNameAt(latitude, longitude)

        std_out ('Device {} timezone is {}'.format(self.id, self.location))               
        
        return self.location

    def get_device_lat_long(self):

        if self.lat is None or self.long is None:
            if self.get_device_json() is not None:
                latidude = longitude = None
                if 'location' in self.devicejson.keys(): latitude, longitude = self.devicejson['location']['latitude'], self.devicejson['location']['longitude']
                elif 'data' in self.devicejson.keys(): 
                    if 'location' in self.devicejson['data'].keys(): latitude, longitude = self.devicejson['data']['location']['latitude'], self.devicejson['data']['location']['longitude']
                
                self.lat = latitude
                self.long = longitude
        
        std_out ('Device {} is located at {}, {}'.format(self.id, latitude, longitude))        
        
        return (self.lat, self.long)
    
    def get_device_added_at(self):

        if self.added_at is None:
            if self.get_device_json() is not None:
                self.added_at = self.devicejson['added_at']                
        
        std_out ('Device {} was added at {}'.format(self.id, self.added_at))

        return self.added_at

    def get_device_sensors(self):

        if self.sensors is None:
            if self.get_device_json() is not None:
                # Get available sensors
                sensors = self.devicejson['data']['sensors']
            
                # Put the ids and the names in lists
                self.sensors = dict()
                for sensor in sensors: 
                    for key in BLUEPRINTS:
                        if not search("sc[k|_]",key): continue
                        if 'sensors' in BLUEPRINTS[key]:
                            for sensor_name in BLUEPRINTS[key]['sensors'].keys(): 
                                if BLUEPRINTS[key]['sensors'][sensor_name]['id'] == str(sensor['id']): 
                                    # IDs are unique
                                    self.sensors[sensor['id']] = sensor_name
        
        return self.sensors

    def convert_rollup(self, frequency):
        # Convert frequency from pandas to API's
        for index, letter in enumerate(frequency):
            try:
                aux = int(letter)
            except:
                index_first = index
                letter_first = letter
                rollup_value = frequency[:index_first]
                frequency_unit = frequency[index_first:]
                break

        for item in FREQ_CONV_LUT:
            if item[1] == frequency_unit: 
                rollup_unit = item[0]
                break

        rollup = rollup_value + rollup_unit
        return rollup

    def get_device_data(self, start_date = None, end_date = None, frequency = '1Min', clean_na = None):

        std_out(f'Requesting data from SC API')
        std_out(f'Device ID: {self.id}')

        rollup = self.convert_rollup(frequency)
        std_out(f'Using rollup: {rollup}')

        # Make sure we have the everything we need beforehand
        self.get_device_sensors()
        self.get_device_location()
        self.get_device_last_reading()
        self.get_device_added_at()
        self.get_kit_ID()

        # Check start date
        if start_date is None and self.added_at is not None:
            start_date = pd.to_datetime(self.added_at, format = '%Y-%m-%dT%H:%M:%SZ')
        elif start_date is not None:
            start_date = pd.to_datetime(start_date, format = '%Y-%m-%dT%H:%M:%SZ')
        
        if start_date.tzinfo is None: start_date = start_date.tz_localize('UTC').tz_convert(self.location)
        std_out (f'Min Date: {start_date}')
        
        # Check end date
        if end_date is None and self.last_reading_at is not None:
            end_date = pd.to_datetime(self.last_reading_at, format = '%Y-%m-%dT%H:%M:%SZ')
        elif end_date is not None:
            end_date = pd.to_datetime(end_date, format = '%Y-%m-%dT%H:%M:%SZ')
        
        if end_date.tzinfo is None: end_date = end_date.tz_localize('UTC').tz_convert(self.location)
        std_out (f'Max Date: {end_date}')
        if start_date > end_date: std_out('Ignoring device dates. Probably SD card device', 'WARNING')
        
        # Print stuff
        std_out('Kit ID: {}'.format(self.kit_id))
        if start_date < end_date: std_out(f'Dates: from: {start_date}, to: {end_date}')
        std_out(f'Device timezone: {self.location}')
        if not self.sensors.keys(): 
            std_out(f'Device is empty')
            return None
        else: std_out(f'Sensor IDs:\n{list(self.sensors.keys())}')

        df = pd.DataFrame()
        
        # Get devices in the sensor first
        for sensor_id in self.sensors.keys(): 

            # Request sensor per ID
            request = self.API_BASE_URL + '{}/readings?'.format(self.id)
            
            if start_date is None or start_date < end_date: request += 'from=2001-01-01'
            else : request += f'from={start_date}'
            request += f'&rollup={rollup}'
            request += f'&sensor_id={sensor_id}'
            request += '&function=avg'
            if end_date is not None and end_date > start_date: request += f'&to={end_date}'
            
            # Make request
            # print (request)
            sensor_req = requests.get(request)
            flag_error = False
            try:
                sensorjson = sensor_req.json()
            except:
                print_exc()
                std_out('Problem with json data from API', 'ERROR')
                flag_error = True
                pass
            
            if 'readings' not in sensorjson.keys(): 
                std_out(f'No readings key in request for sensor: {sensor_id}', 'ERROR')
                flag_error = True
            
            elif sensorjson['readings'] == []: 
                std_out(f'No data in request for sensor: {sensor_id}', 'WARNING')
                flag_error = True

            if flag_error: continue

            # Put 
            try:
                dfsensor = pd.DataFrame(sensorjson['readings']).set_index(0)
                dfsensor.columns = [self.sensors[sensor_id]]
                dfsensor.index = pd.to_datetime(dfsensor.index).tz_localize('UTC').tz_convert(self.location)
                dfsensor.sort_index(inplace=True)
                dfsensor = dfsensor[~dfsensor.index.duplicated(keep='first')]
                
                # Drop unnecessary columns
                dfsensor.drop([i for i in dfsensor.columns if 'Unnamed' in i], axis=1, inplace=True)
                # Check for weird things in the data
                dfsensor = dfsensor.apply(pd.to_numeric, errors='coerce')
                # Resample
                dfsensor = dfsensor.resample(frequency, limit = 1).mean()

                df = df.combine_first(dfsensor)
            except:
                print_exc()
                std_out('Problem with sensor data from API', 'ERROR')
                flag_error = True
                pass                

            if flag_error: continue

            try:
                df = df.reindex(df.index.rename('Time'))
                
                if clean_na is not None:
                    if clean_na == 'drop':
                        # std_out('Cleaning na with drop')
                        df.dropna(axis = 0, how='all', inplace=True)
                    elif clean_na == 'fill':
                        df = df.fillna(method='bfill').fillna(method='ffill')
                        # std_out('Cleaning na with fill')
                self.data = df
                
            except:
                std_out('Problem closing up the API dataframe', 'ERROR')
                pass
                return None

        std_out(f'Device {self.id} loaded successfully from API', 'SUCCESS')
        return self.data

class MuvApiDevice:

    API_BASE_URL='https://data.waag.org/api/muv/'

    def __init__ (self, did):
        self.id = did
        self.location = None
        self.data = None
        self.sensors = None

    def get_device_location(self):
        self.location = 'Europe/Madrid'
        return self.location

    def get_device_sensors(self):
        if self.sensors is None:
            self.sensors = dict()
            for key in BLUEPRINTS:
                if 'muv' not in key: continue
                if 'sensors' in BLUEPRINTS[key]:
                    for sensor_name in BLUEPRINTS[key]['sensors'].keys():
                        # IDs are unique
                        self.sensors[BLUEPRINTS[key]['sensors'][sensor_name]['id']] = sensor_name
        return self.sensors

    def get_device_data(self, start_date = None, end_date = None, frequency = '1Min', clean_na = None):

        std_out(f'Requesting data from MUV API')
        std_out(f'Device ID: {self.id}')
        self.get_device_location()
        self.get_device_sensors()        
        
        # Get devices
        try:
            url = self.API_BASE_URL + 'getSensorData?sensor_id={}/'.format(self.id)
            df = pd.read_json(url)
        except:
            # print_exc()
            std_out('Failed sensor request request. Probably no connection', 'ERROR')
            pass
            return None

        try:
            # Rename columns
            df.rename(columns=self.sensors, inplace=True)
            df = df.set_index('Time')
            df.index = pd.to_datetime(df.index).tz_localize('UTC').tz_convert(self.location)
            df = df[~df.index.duplicated(keep='first')]
            # Drop unnecessary columns
            df.drop([i for i in df.columns if 'Unnamed' in i], axis=1, inplace=True)
            # Check for weird things in the data
            df = df.apply(pd.to_numeric, errors='coerce')
            # # Resample
            df = df.resample(frequency, limit = 1).mean()
            df = df.reindex(df.index.rename('Time'))
                
            if clean_na is not None:
                if clean_na == 'drop':
                    df.dropna(axis = 0, how='all', inplace=True)
                elif clean_na == 'fill':
                    df = df.fillna(method='bfill').fillna(method='ffill')
            self.data = df
                
        except:
            std_out('Problem closing up the API dataframe', 'ERROR')
            pass
            return None

        std_out(f'Device {self.id} loaded successfully from API', 'SUCCESS')
        return self.data

class DadesObertesApiDevice:

    API_BASE_URL="https://analisi.transparenciacatalunya.cat/resource/uy6k-2s8r.csv?"

    def __init__ (self, did = None, within = None):
        if did is None and within is None:
            std_out('Specify either station id (=codi_eoi) or within (=(lat, long, radius_meters))')
            return

        if did is not None: self.id = did
        if within is not None: self.id = self.get_id_from_within(within)

        self.location = None
        self.data = None
        self.sensors = None
        self.devicejson = None
        self.lat = None
        self.long = None
        self.location = None
    
    @staticmethod
    def get_world_map(city = None, within = None, station_type = None, area_type = None):
        """
        Gets devices from Dades Obertes API with certain requirements
        Parameters
        ----------
            city: string, optional
                Empty string
                City
            within: tuple
                Empty tuple
                Gets the devices within a circle center on lat, long with a radius_meters
                within = tuple(lat, long, radius_meters)
            station_type: string
                None
                Type of station, to choose from: 'background', nan or 'traffic'
            area_type: string
                None
                Type of area, to choose from:  nan, 'peri-urban', 'rural', 'suburban', 'urban'
        Returns
        -------
            A list of eoi codes that comply with the requirements. If no requirements are set, returns all of them
        """
        def is_within_circle(x, within):
            if math.isnan(x['latitud']): return False
            if math.isnan(x['longitud']): return False

            return calculate_distance(location_A=(within[0], within[1]), location_B=(x['latitude'], x['longitude']))<within[2]
            
        world_map = requests.get("https://analisi.transparenciacatalunya.cat/resource/uy6k-2s8r.csv?")
        df = pd.read_csv(io.StringIO(world_map.content.decode('utf-8'))).set_index('codi_eoi')
        
        # Location
        if city is not None: df=df[(df['municipi']==city)]
        if within is not None:

            df['within'] = df.apply(lambda x: is_within_circle(x, within), axis=1)
            df=df[(df['within']==True)]
            
        # Station type
        if station_type is not None: df=df[(df['tipus_est']==station_type)] 
        # Area type
        if area_type is not None: df=df[(df['rea_urb']==area_type)]
        
        return list(set(list(df.index)))

    def get_id_from_within(self, within):
        '''
            Gets the stations within a radius in meters.
            within = tuple(lat, long, radius_meters)
        '''
        request = self.API_BASE_URL
        request += f'$where=within_circle(geocoded_column,{within[0]},{within[1]},{within[2]})'

        try:
            s = requests.get(request)
        except:
            std_out('Problem with request from API', 'ERROR')
            return None

        if s.status_code == 200 or s.status_code == 201:
            df = pd.read_csv(io.StringIO(s.content.decode('utf-8')))
        else:
            std_out('API reported {}'.format(s.status_code), 'ERROR')
            return None

        if 'codi_eoi' in df.columns: 
            ids = list(set(df.codi_eoi.values))
            if ids == []: std_out('No stations within range', 'ERROR')
            elif len(ids) > 1:
                for ptid in ids: 
                    municipi = next(iter(set(df[df.codi_eoi==ptid].municipi.values)))
                    nom_estaci = next(iter(set(df[df.codi_eoi==ptid].nom_estaci.values)))
                    rea_urb = next(iter(set(df[df.codi_eoi==ptid].rea_urb.values)))
                    tipus_est = next(iter(set(df[df.codi_eoi==ptid].tipus_est.values)))
                    
                    std_out(f'{ids.index(ptid)+1} /- {ptid} --- {municipi} - {nom_estaci} - Type: {rea_urb} - {tipus_est}')
                
                wptid = int(input('Multiple stations found, please select one: ')) - 1

                devid = ids[wptid]
                std_out(f'Selected station in {next(iter(set(df[df.codi_eoi==devid].municipi.values)))} with codi_eoi={devid}')
            else:
                devid = ids[0]
                municipi = next(iter(set(df[df.codi_eoi==devid].municipi.values)))
                nom_estaci = next(iter(set(df[df.codi_eoi==devid].nom_estaci.values)))
                rea_urb = next(iter(set(df[df.codi_eoi==devid].rea_urb.values)))
                tipus_est = next(iter(set(df[df.codi_eoi==devid].tipus_est.values)))        
                std_out(f'Found station in {next(iter(set(df[df.codi_eoi==devid].municipi.values)))} with codi_eoi={devid}')
                std_out(f'Found station in {municipi} - {nom_estaci} - {devid} - Type: {rea_urb} - {tipus_est}')

        else:
            std_out('Data is empty', 'ERROR')
            return None            

        return devid

    def get_device_sensors(self):

        if self.sensors is None:
            if self.get_device_json() is not None:
                # Get available sensors
                sensors = list(set(self.devicejson.contaminant))
            
                # Put the ids and the names in lists
                self.sensors = dict()
                for sensor in sensors: 
                    for key in BLUEPRINTS:
                        if not search("csic_station",key): continue
                        if 'sensors' in BLUEPRINTS[key]:
                            for sensor_name in BLUEPRINTS[key]['sensors'].keys(): 
                                if BLUEPRINTS[key]['sensors'][sensor_name]['id'] == str(sensor): 
                                    # IDs are unique
                                    self.sensors[sensor] = sensor_name
        
        return self.sensors        
    
    def get_device_json(self):

        if self.devicejson is None:
            try:
                s = requests.get(self.API_BASE_URL + f'codi_eoi={self.id}')
                if s.status_code == 200 or s.status_code == 201:
                    self.devicejson = pd.read_csv(io.StringIO(s.content.decode('utf-8')))
                else: 
                    std_out('API reported {}'.format(s.status_code), 'ERROR')  
            except:
                std_out('Failed request. Probably no connection', 'ERROR')  
                pass
        
        return self.devicejson

    def get_device_location(self):

        if self.location is None:
            latitude, longitude = self.get_device_lat_long()
            # Localize it
            tz_where = tzwhere.tzwhere()
            self.location = tz_where.tzNameAt(latitude, longitude)
            
        std_out ('Device {} timezone is {}'.format(self.id, self.location))               
        
        return self.location

    def get_device_lat_long(self):

        if self.lat is None or self.long is None:
            if self.get_device_json() is not None:
                latitude = longitude = None
                if 'latitud' in self.devicejson.columns: 
                    latitude = next(iter(set(self.devicejson.latitud)))
                    longitude = next(iter(set(self.devicejson.longitud)))
                
                self.lat = latitude
                self.long = longitude
        
            std_out ('Device {} is located at {}, {}'.format(self.id, latitude, longitude))        
        
        return (self.lat, self.long)

    def get_device_data(self, start_date = None, end_date = None, frequency = '1H', clean_na = None):
        '''
        Based on code snippet from Marc Roig:
        # I2CAT RESEARCH CENTER - BARCELONA - MARC ROIG (marcroig@i2cat.net)
        '''

        std_out(f'Requesting data from Dades Obertes API')
        std_out(f'Device ID: {self.id}')
        self.get_device_sensors()
        self.get_device_location()

        request = self.API_BASE_URL
        request += f'codi_eoi={self.id}'

        if start_date is not None and end_date is not None:
            request += "&$where=data between " + pd.to_datetime(start_date).strftime("'%Y-%m-%dT%H:%M:%S'") \
                    + " and " + pd.to_datetime(end_date).strftime("'%Y-%m-%dT%H:%M:%S'")
        elif start_date is not None:
            request += "&$where=data >= " + pd.to_datetime(start_date).strftime("'%Y-%m-%dT%H:%M:%S'")
        elif end_date is not None:
            request += "&$where=data < " + pd.to_datetime(end_date).strftime("'%Y-%m-%dT%H:%M:%S'")

        try:
            s = requests.get(request)
        except:
            print_exc()
            std_out('Problem with sensor data from API', 'ERROR')
            pass
            return None

        if s.status_code == 200 or s.status_code == 201:
            df = pd.read_csv(io.StringIO(s.content.decode('utf-8')))
        else:
            std_out('API reported {}'.format(s.status_code), 'ERROR')
            pass
            return None

        # Filter columns
        measures = ['h0' + str(i) for i in range(1,10)]
        measures += ['h' + str(i) for i in range(10,25)]
        # validations = ['v0' + str(i) for i in range(1,10)]
        # validations  += ['v' + str(i) for i in range(10,25)]
        new_measures_names = list(range(1,25))

        columns = ['contaminant', 'data'] + measures# + validations
        try:
            df_subset = df[columns]
            df_subset.columns  = ['contaminant', 'date'] + new_measures_names
        except:
            print_exc()
            std_out('Problem while filtering columns', 'Error')
            return None
        else:
            std_out('Successful filtering', 'SUCCESS')

        # Pivot
        try:
            df = pd.DataFrame([])
            for contaminant in self.sensors.keys():
                if contaminant not in df_subset['contaminant'].values: 
                    std_out(f'{contaminant} not in columns. Skipping', 'WARNING')
                    continue
                df_temp= df_subset.loc[df_subset['contaminant']==contaminant].drop('contaminant', 1).set_index('date').unstack().reset_index()
                df_temp.columns = ['hours', 'date', contaminant]
                df_temp['date'] = pd.to_datetime(df_temp['date'])
                timestamp_lambda = lambda x: x['date'] + pd.DateOffset(hours=int(x['hours']))
                df_temp['date'] = df_temp.apply( timestamp_lambda, axis=1)
                df_temp = df_temp.set_index('date')
                df[contaminant] = df_temp[contaminant]
        except:
            # print_exc()
            std_out('Problem while filtering columns', 'Error')
            pass
            return None
        else:
            std_out('Successful pivoting', 'SUCCESS')

        df.index = pd.to_datetime(df.index).tz_localize('UTC').tz_convert(self.location)
        df.sort_index(inplace=True)

        # Rename
        try:
            df.rename(columns=self.sensors, inplace=True)
        except:
            # print_exc()
            std_out('Problem while renaming columns', 'Error')
            pass
            return None
        else:
            std_out('Successful renaming', 'SUCCESS')
        
        # Clean
        df = df[~df.index.duplicated(keep='first')]
        # Drop unnecessary columns
        df.drop([i for i in df.columns if 'Unnamed' in i], axis=1, inplace=True)
        # Check for weird things in the data
        df = df.apply(pd.to_numeric, errors='coerce')
        # Resample
        df = df.resample(frequency, limit = 1).mean()

        try:
            df = df.reindex(df.index.rename('Time'))
            
            if clean_na is not None:
                if clean_na == 'drop':
                    # std_out('Cleaning na with drop')
                    df.dropna(axis = 0, how='all', inplace=True)
                elif clean_na == 'fill':
                    df = df.fillna(method='bfill').fillna(method='ffill')
                    # std_out('Cleaning na with fill')
            self.data = df
            
        except:
            std_out('Problem closing up the API dataframe', 'ERROR')
            pass
            return None

        std_out(f'Device {self.id} loaded successfully from API', 'SUCCESS')
        return self.data