from datetime import datetime
import numpy as np
from pathlib import Path
import requests
from shapely import Point
import subprocess
from time import sleep

from .enumerations import TRAVELTIME_TOOCLOSE
from .enumerations import TRAVELTIME_ERROR

class OTP2():
    """ Class to interface with OpenTripPlanner to calculate run times.

    This class is currently designed to operate with OpenTripPlanner version 2.4. The calls to OTP are conducted
    through their newer GTFS `*`GraphQL API`, as their previous `Restful API` will be discontinued.
    
    Parameters
    ----------
        None

    Methods
    -------
    build_otp_graph(overwrite=False)
        build OPT 2 graph in `graph_dir` directory using OSM file and optional GTFS files specified in this directory.



    Attributes
    ----------
    java_path : pathlib.Path
        Path to the java executable used to run OTP. This must be set before any operations are done.
    otp_jar_path : pathlib.Path
        Path to OPT 2.4 jar file. This must be set before any operations are done.
    graph_dir: pathlib.Path
        Directory contain the network build. This should contain the OSM street network in compressed (.pbf) format
        and optionally transit GTFS files. This must be set before any operations are done. 
    memory_str: str
        Code describing the memory to allocate. e.g. '2G' = 2 GB. Default is "1G"
    max_server_sleep_time: int or float
        Maximum number of seconds to wait after launching server. Default is 30 seconds.
    request_host_url: pathlib.Path
        Root URL used for requests to OTP server. Defaults to "http://localhost:8080", which is 
        a server running on a local machine.
    """

    # Class variables
    JAVA_PATH_ERROR = "Must set Java path before running Open Trip Planner."
    OTP_JAR_PATH_ERROR = "Must defined the path to the OTP 2.4 jar file before running Open Trip Planner."
    GRAPH_DIR_ERROR = "Must defined the path to the network directory berfore building graph or launching the server."

    HEADERS = {
        'Content-Type': 'application/json',
        'OTPTimeout': '180000',
    }

    def __init__(self):
        
        # These attributes will need to be defined before starting an OTP instance
        self._java_path = None
        self._otp_jar_path = None
        self._graph_dir = None
        self._memory_str = "1G"

        # These default URLs assume that the server is hosted locally. These can be changed by a user if desired
        self._request_host_url = "http://localhost:8080"
        self._request_api = self._request_host_url + "/otp/routers/default/index/graphql"
        
        # This allows time for a server to fully load before running requests
        # Setting this too low will cause problems as the server won't be available when subsequent actions are run.
        self._max_server_sleep_time = 30


    def build_otp_graph(self, overwrite:bool=False) -> None:
        """ Runs OTP 2 to build OTP graph in the directory.
        
        The OTP graph is built in the directory specified by the `graph_dir` attribute. This directory should have
        the OSM network (saved in .pbf format) and optional GTFS transit files.
        
        Parameters
        ----------
        overwrite:
            If True, overwrite any existing graph in the graph directory. 
            Will raise if set to False and there is an existing graph.

        Raises
        ------
        FileExistsError
            Raised if the graph exists and overwrite is set to False.
        ValueError
            If the `java_path`, `otp_jar_path` or `graph_dir` attributes have not been set.
        
        subprocess.CalledProcessError
            Errors returned by the OTP 2 subprocess.
        """
        self._test_paths()

        # Test to see if there is an existing graph, delete if overwrite is True, otherwise exit.
        graph_file_path = self._graph_dir / "graph.obj"
        if graph_file_path.is_file():
            if overwrite:
                graph_file_path.unlink()
            else:
                raise FileExistsError("`overwrite` argument is False and graph exists in the directory.")

        full_memory_str = f"-Xmx{self._memory_str}"
        subproc_return = subprocess.run([
            self._java_path.absolute(), full_memory_str, "-jar", self._otp_jar_path.absolute(), 
            "--build", "--save", self._graph_dir.absolute(),
        ], check=True)

        # Ensure that the graph has been created in the run directory
        if not graph_file_path.is_file():
            raise FileExistsError("Graph file was not created")

    def launch_local_otp2_server(self) -> None:
        """ Launches OTP 2 server on the local machine using previously built graph. 

        Notes
        -----
        This method will wait until a connection is made to the server before finishing, up until 
        a number of seconds defined in the attribute `max_server_sleep_time`
        
        Raises
        ------
        FileExistsError
            Raised if the graph file does not exist in `graph_dir`
        ValueError
            If the `java_path`, `otp_jar_path` or `graph_dir` attributes have not been set.
        subprocess.CalledProcessError
            Errors returned by the OTP 2 subprocess.
        RuntimeError:
            Connection could not be made to server within time specified by `max_server_sleep_time`
        """
        self._test_paths()

        # Make sure that the graph exists in this folder
        graph_file_path = self._graph_dir / "graph.obj"
        if not graph_file_path.is_file():
            raise FileNotFoundError(f"`graph_file_path` does not exist. Need to run `build_otp_graph` before launching server.")

        full_memory_str = f"-Xmx{self._memory_str}"
        # Note that this server runs in the background, so we'll use a subprocess.popen constructor instead
        subproc_return = subprocess.Popen([
            self._java_path.absolute(), full_memory_str, "-jar", self._otp_jar_path.absolute(), 
            "--load", self._graph_dir.absolute()
        ])

        # Sleep to ensure that the server is launched before exiting out of the method
        t = 0
        increment = 1
        while True:
            try:
                self.test_otp_server()
                break
            except requests.ConnectionError:
                # Not ready yet, try again
                pass
            except RuntimeError:
                # Not ready yet, try again
                pass
            sleep(increment)
            if t >= self._max_server_sleep_time:
                raise RuntimeError(f"Connection to server could not be found within{self._max_server_sleep_time} seconds")
            t += increment

    def test_otp_server(self) -> None:
        """ Tests if can successfully connect to OTP 2 server. 

        Tests server at the address defined in `request_host_url` attribute. 
        
        Raises
        ------
        requests.ConnectionError
            Raised if cannot connect 
        RuntimeError
            Raised if null values are returned from the request
        """

        host = requests.get(self._request_host_url)
        if host is None:
            raise RuntimeError("Null values returned from OTP request.")


    def request_walk_trip_cost(self, from_pt, to_pt, walk_speed=5.0, test_mode=False):
        """ Requests a walk-only trip from OTP, returing walk time and distance.

            Parameters
            ----------
            from_pt: shapely.Point
                Point containing x,y location of trip start
            to_pt: list of float
                Point containing x,y location of trip end
            walk_speed: float
                Walk speed in kilometres per hour
                
            Returns
            -------
            results: dict
                walk_time: float
                    Walk time in minutes
                walk_distance: float
                    Walk distance in metres
                generalized_cost: float
                    Internal generalized cost

            Raises
            ------
            requests.ConnectionError
                Raised if cannot connect to host

            Other Parameters
            ----------------
            test_mode: bool, optional
                if True, returns request itineraries instead of usual return dictionary. 
                This is intended only to be run from test scripts. 

            Notes
            -----
            For a walk trip in OTP, we do not need to specify a date and time. 

        """
        from_str = self._set_pt_str("from", from_pt)
        to_str = self._set_pt_str("to", to_pt)
        modes_str = self._set_modes_str(["WALK"])
        walk_spd_str = f"walkSpeed: {walk_speed / 3.6}"  # Convert walk speed to metres per second
        itineraries_str = self._set_itineraries_str()
        qry_str = "{plan(%s %s %s %s)%s}" % (from_str, to_str, modes_str, walk_spd_str, itineraries_str)
        qry = {
            'query': qry_str
        }
        request = requests.post(self._request_api, headers=self.HEADERS, json=qry)
        result = request.json()

        try:
            itineraries = result['data']['plan']['itineraries']
        except KeyError:
            raise RuntimeError("Invalid query string:  '%s'" % qry_str)

        if len(itineraries) == 0:
            raise RuntimeError("No itineraries found")
        if len(itineraries) > 1:
            raise RuntimeError("More than one itinerary found for walk trip. This is unexpected to look into this.")

        if not test_mode:
            # Default mode, returns trip duration and walk distance
            return {"trip_duration": (itineraries[0]['endTime'] - itineraries[0]['startTime']) / 60.0, 
                    "walk_distance": itineraries[0]['walkDistance'],
                    "generalized_cost": itineraries[0]['generalizedCost']}
        else:
            # In test mode, return full itinerary for additional testing
            return itineraries
        

    def request_bike_trip_cost(self, from_pt, to_pt, bike_speed=18.0, test_mode=False):
        """ Requests a bike-only trip from OTP, returing walk time and distance. """

        # todo: need to explore more for bike trips, including possible changes to the router-config file
        raise NotImplementedError("Further testing is required for this library to support bike travel. ")

    def request_transit_trip_cost(self, from_pt, to_pt, date_str, time_str, arrive_by, walk_speed=5.0, 
                                    skip_test_trip_date=False, test_mode=False, num_itineraries=5):
        """ Requests a transit/walk trip from OTP, returing total time and walk distance.

            Parameters
            ----------
            from_pt: shapely.Point
                Point containing x,y location of trip start
            to_pt: list of float
                Point containing x,y location of trip end
            walk_speed: float
                Walk speed in kilometres per hour
            date_str: str
                Trip date in format YYYY-MM-DD
            time_str: str
                Trip time in format hh:mm
            arrive_by: bool
                Flag if trip time reflects latest arrival time (if True) or departure time (if False)
                

            Returns
            -------
            results: dict
                walk_time: float
                    Walk time in minutes
                walk_distance: float
                    Walk distance in metres
                generalized_cost: float
                    Internal generalized cost


            Raises
            ------
            requests.ConnectionError
                Raised if cannot connect to host

                
            Other Parameters
            ----------------
            skip_test_trip_date: bool, optional
                if true, then do not test the trip start time. This is meant as an efficiency parameter when requesting
                multiple trip costs, such as when calculating a travel time matrix.

            test_mode: bool, optional
                if True, returns request itineraries instead of usual return dictionary. 
                This is intended only to be run from test scripts. 

            num_itineraries: int, optional
                Sets the maximum number of itineraries returned. Default is 5.


        """
        if not skip_test_trip_date:
            self.test_date_within_service_time_range(date_str)

        from_str = self._set_pt_str("from", from_pt)
        to_str = self._set_pt_str("to", to_pt)
        modes_str = self._set_modes_str(["WALK", "TRANSIT"])
        itineraries_str = self._set_itineraries_str()

        qry_str = '{' + f'plan({from_str} {to_str} {modes_str} date: "{date_str}" time: "{time_str}" ' + \
                  f'arriveBy: {str(arrive_by).lower()} walkSpeed: {walk_speed / 3.6} ){itineraries_str}' + '}' 
        qry = {
            'query': qry_str
        }
        request = requests.post(self._request_api, headers=self.HEADERS, json=qry)
        result = request.json()

        try:
            itineraries = result['data']['plan']['itineraries']
        except KeyError:
            raise RuntimeError("Invalid query string:  '%s'" % qry_str)

        if len(itineraries) == 0:
            raise RuntimeError("No itineraries found")

        if not test_mode:
            # Default mode, returns trip duration and walk distance
            # Find and return the details from the itinerary with the shortest travel time
            # Note that the trip startTime and endTime are in posix milliseconds, hence / 1000
            # to convert to posix seconds, which is what Python's datetime.timestamp uses.

            min_duration = 9.999e15
            gen_cost_min_duration_trip = 9.999e15
            walkdist_min_duration_trip = 9.999e15
            for it in result['data']['plan']['itineraries']:
                if arrive_by:
                    duration = self._create_numerical_datetime(date_str, time_str) - (it['startTime'] // 1000)
                else:
                    duration = (it['endTime'] // 1000) - self._create_numerical_datetime(date_str, time_str)
                if duration < min_duration:
                    min_duration = duration
                    walkdist_min_duration_trip = it['walkDistance']
                    gen_cost_min_duration_trip = it['generalizedCost']

            return {
                "trip_duration": min_duration / 60.0, 
                "walk_distance": walkdist_min_duration_trip, 
                "generalized_cost": gen_cost_min_duration_trip
            }
        else:
            # In test mode, return full itinerary for additional testing
            return itineraries

    def request_avg_transit_trip_cost(
            self, start_time_str, time_dur, time_increment=1, **kwargs):
        """ Requests average transit/walk trip costs from OTP over a time interval, inclusive at intervanl start, exclusive at interval end.

            Parameters
            ----------
            start_time_str: str
                Time interval start in format hh:mm
            duration: int
                Duration of time interval in minues.
            time_increment: int, optional
                Increment between different trip runs in minutes. Defaults to 1 minute.
            **kwargs:
                Transit trip cost parameters to be used by `request_transit_trip_cost` method.
                The time_str argument will be overwritten.

            Returns
            -------
            Average of results return from `request_transit_trip_cost` method over the time interval.
        
        """
        # Make sure that no time_str argument is included in the kwargs, this needs to be overwritten.
        if ['time_str'] in kwargs.keys():
            del kwargs['time_str']

        trip_time_str = start_time_str
        elapsed_time = 0
        n_runs = 0
        sum_dict = {
                "trip_duration": 0.0, 
                "walk_distance": 0.0, 
                "generalized_cost": 0.0
        }
        while True:
            cost_dict = self.request_transit_trip_cost(time_str=trip_time_str, **kwargs)
            sum_dict["trip_duration"] += cost_dict["trip_duration"]
            sum_dict["walk_distance"] += cost_dict["walk_distance"]
            sum_dict["generalized_cost"] += cost_dict["generalized_cost"]
            n_runs += 1
            trip_time_str = self._calc_next_time(trip_time_str, time_increment)
            elapsed_time += time_increment
            if elapsed_time >= time_dur:  # Exclusive at trip end
                break
        for k, v in sum_dict.items():
            sum_dict[k] = v / n_runs
        return sum_dict

    @staticmethod
    def _create_numerical_datetime(date_str, time_str):
        year, month, day = date_str.split('-')
        hour, min = time_str.split(':', maxsplit=1)
        dt = datetime(int(year), int(month), int(day), int(hour), int(min))
        return dt.timestamp()

    @staticmethod
    def _calc_num_intervals(time_intervals: list[dict]) -> int:
        return len(time_intervals)

    def _calc_num_timesteps(self, time_intervals: list[dict]) -> int:
        def _calc_num_timesteps_in_interval(st_hr, st_min, end_hr, end_min, step):
            st_int = 60 * st_hr + st_min
            end_int = 60 * end_hr + end_min - 1    # adding -1 as exclusive of end time
            return 1 + ((end_int - st_int) // step)

        total_timesteps = 0
        for ti in time_intervals:
            st_hr, st_min = [int(x) for x in ti['start'].split(":")]
            end_hr, end_min = [int(x) for x in ti['end'].split(":")]
            total_timesteps += _calc_num_timesteps_in_interval(st_hr, st_min, end_hr, end_min, ti['step_mins'])
        return total_timesteps

    def _calc_timestamps(self, time_intervals: list[dict]) -> list[str]:
        times = []
        for ti in time_intervals:
            current_time = ti['start']
            times.append(ti['start'])
            hrmin_end = self._calc_hrmin_int(ti['end'])
            step_mins = ti['step_mins']
            while True:
                current_time = self._calc_next_time(current_time, step_mins)
                if self._calc_hrmin_int(current_time) >= hrmin_end:   # exclusive of end point
                    break
                times.append(current_time)
        return times
                    
    def test_date_within_service_time_range(self, date_str: str):
        """ Test if provided date is within the graph service time range. 

        Parameters
        ----------
        date_str: Trip date in format YYYY-MM-DD

        Raises
        ------
        RuntimeError: 
            if date is not within service time range
            OTP server is not running

        """
        test_date = np.datetime64(date_str)
        test_posix = test_date.astype('datetime64[s]').astype('int')

        # Test that the OTP server is up and running
        self.test_otp_server()

        # Find the POSIX representation of the graph start/end times 
        json_data = {
            'query': '{serviceTimeRange {start end} }'
        }
        
        request = requests.post('http://localhost:8080/otp/routers/default/index/graphql', headers=self.HEADERS, json=json_data)
        result = request.json()
        
        start_posix = result['data']['serviceTimeRange']['start']
        end_posix = result['data']['serviceTimeRange']['end']

        if not start_posix <= test_posix <= end_posix:
            start_end_dates = np.array([start_posix, end_posix], dtype='datetime64[s]')
            raise RuntimeError(f"Trip date {date_str} is not within graph start/end dates: {start_end_dates}")

    #region property methods
        
    @property
    def java_path(self):
        return self._java_path

    @java_path.setter
    def java_path(self, new_path):
        new_path = Path(new_path)
        if not new_path.is_file:
            raise FileNotFoundError("Invalid java path.")
        self._java_path = new_path

    @property
    def otp_jar_path(self):
        return self._otp_jar_path
    
    @otp_jar_path.setter
    def otp_jar_path(self, new_path):
        new_path = Path(new_path)
        if not new_path.is_file:
            raise FileNotFoundError("Invalid OTP jar path.")
        self._otp_jar_path = new_path

    @property
    def graph_dir(self):
        return self._graph_dir

    @graph_dir.setter
    def graph_dir(self, new_path):
        new_path = Path(new_path)
        if not new_path.is_dir:
            raise FileNotFoundError("Invalid path to graph directory.")
        self._graph_dir = new_path

    @property
    def memory_str(self):
        return self._memory_str
    
    @memory_str.setter
    def memory_str(self, new_memory_str):
        self._memory_str = new_memory_str

    @property
    def request_host_url(self):
        return self._request_host_url

    @request_host_url.setter
    def request_host_url(self, new_url):
        self._request_host_url = new_url
        self._request_api = self._request_host_url + "/otp/routers/default/index/graphql"

    @property
    def max_server_sleep_time(self):
        return self._max_server_sleep_time
    
    @max_server_sleep_time.setter
    def max_server_sleep_time(self, new_sleep_time):
        if not (isinstance(new_sleep_time, float) or isinstance(new_sleep_time, int)):
            raise TypeError("max_server_sleep_time must be a float or int value.")
        if new_sleep_time < 0.0:
            raise ValueError("max_server_sleep_time must be a number >= 0.")
        self._max_server_sleep_time = new_sleep_time

    #endregion
        
    def _test_paths(self):
        if self._java_path is None:
            raise FileNotFoundError(self.JAVA_PATH_ERROR)
        if self._otp_jar_path is None:
            raise FileNotFoundError(self.OTP_JAR_PATH_ERROR)
        if self._graph_dir is None:
            raise FileNotFoundError(self.GRAPH_DIR_ERROR)

    @staticmethod
    def _set_pt_str(from_to: str, pt: Point):
        return "%s: {lat: %f, lon: %f}" % (from_to, pt.y, pt.x)

    @staticmethod
    def _set_modes_str(modes: list):
        modes_str_int = ""
        for mode in modes:
            modes_str_int = modes_str_int + "{mode: %s}, " % mode
        modes_str_int = modes_str_int[:-2]    # Take out the final comma and space
        return "transportModes: [%s]" % modes_str_int

    @staticmethod
    def _set_itineraries_str():
        return "{itineraries {startTime endTime walkDistance generalizedCost legs{mode duration}}}"
    
    # @staticmethod
    # def _calc_hrmin_int(timestr: str):
    #     hour, minute = [int(x) for x in timestr.split(":")]
    #     return 60 * hour + minute

    @staticmethod
    def _calc_next_time(timestr: str, step: int) -> str:
        """ Calculates the next time ("hour:min") given a current time and a step size in minutes. """
        hour, minute = [int(x) for x in timestr.split(":")]
        if minute + step >= 60:
            hr_increment = (minute + step) // 60
            return f"{str(hour + hr_increment).zfill(2)}:{str(minute + step - hr_increment * 60).zfill(2)}"
        return f"{str(hour).zfill(2)}:{str(minute + step).zfill(2)}"