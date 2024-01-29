import geopandas as gpd
import numpy as np
import pandas as pd
from pandas import testing as tm
from shapely import Point
import unittest
from accessto.matrix import Matrix
from accessto.travel_costs.otp2 import OTP2


class TestOTP2(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:

        # Build the OTP graph and launch server.
        cls.otp_instance = OTP2()
        cls.otp_instance.java_path = r"C:\Program Files\Microsoft\jdk-17.0.9.8-hotspot\bin\java"
        cls.otp_instance.otp_jar_path = r"C:\MyPrograms\otp\2_4\otp-2.4.0-shaded.jar"
        cls.otp_instance.graph_dir = r"C:\Users\bsharma2\AccessOpportunities\Test Data\tests"
        cls.otp_instance.memory_str = "1G"

        cls.otp_instance.build_otp_graph(overwrite=True)
        cls.otp_instance.launch_local_otp2_server()

    def setUp(self):
        from_df = pd.DataFrame(index=[11, 13, 15], columns = ['geometry'], 
                       data = [Point(-79.52809, 43.61918), Point(-79.52238, 43.62586), Point(-79.51702, 43.62160)])
        self.from_gdf = gpd.GeoDataFrame(from_df, crs="EPSG:4326")

        to_df = pd.DataFrame(index=[21, 23], columns = ['geometry'], 
                     data = [Point(-79.50093, 43.62943), Point(-79.49908, 43.62977)])
        self.to_gdf = gpd.GeoDataFrame(to_df, crs="EPSG:4326")

        self.from_pt = self.from_gdf.iloc[0]['geometry']
        self.to_pt = self.to_gdf.iloc[0]['geometry']

    @staticmethod
    def _test_matrix(test_matrix, ref_matrix, check_name=False):
        """ Test matrix helping function that checks two matrices. Raises Assertion error if test fails."""
        tm.assert_frame_equal(
                left=test_matrix.matrix, 
                right=ref_matrix.matrix,
                check_dtype=False,
                check_names=False,
                check_exact=False,
                check_index_type="equiv"
        )
        if check_name:
            if test_matrix.name != ref_matrix.name:
                raise AssertionError(f"Names do not match: {test_matrix.name}, {ref_matrix.name}")

    def test_walk_trip_request_default_walk_speed(self):
        """ Compare walk trip request using default walk speed of 5 km/hr."""
        r = self.otp_instance.request_walk_trip_cost(self.from_pt, self.to_pt)
        self.assertAlmostEqual(r['trip_duration'], 2331 / 60, places=3)
        self.assertAlmostEqual(r['walk_distance'], 2940.45, places=3)


    def test_walk_trip_request_custom_walk_speed(self):
        r = self.otp_instance.request_walk_trip_cost(self.from_pt, self.to_pt, walk_speed=7.2)
        self.assertAlmostEqual(r['trip_duration'], 1674 / 60, places=3)
        self.assertAlmostEqual(r['walk_distance'], 2940.45, places=3)


    def test_walk_matrix_request_default_walk_speed(self):
        ref_matrix = Matrix(origins=[11, 13, 15], destinations=[21,23], 
                            data=[[38.850000, 39.183333], [32.933333, 30.216667], [26.333333, 26.666667]],
                            name="ref_walk_matrix")
        cost_matrix = self.otp_instance.request_walk_cost_matrix(self.from_gdf, self.to_gdf)
        self._test_matrix(cost_matrix, ref_matrix)

    def test_walk_matrix_request_custom_walk_speed(self):
        ref_matrix = Matrix(origins=[11, 13, 15], destinations=[21,23], 
                            data=[[27.900000, 28.116667], [23.183333, 21.316667], [18.850000, 19.066667]],
                            name="ref_walk_matrix")
        cost_matrix = self.otp_instance.request_walk_cost_matrix(self.from_gdf, self.to_gdf, walk_speed=7.2)
        self._test_matrix(cost_matrix, ref_matrix)

    def test_time_within_graph_interval(self):
        self.otp_instance.test_date_within_service_time_range("2024-01-15")

    def test_time_not_within_graph_interval(self):
        with self.assertRaises(RuntimeError):
            self.otp_instance.test_date_within_service_time_range("2023-01-15")

    def test_single_transit_trip_request_default_walk_speed(self):
        r = self.otp_instance.request_transit_trip_cost(
            self.from_pt, self.to_pt, "2024-01-15", "09:16", arrive_by=False)
        self.assertAlmostEqual(r['trip_duration'], 37.3, places=1)
        self.assertAlmostEqual(r['walk_distance'], 751.35, places=1)

    def test_single_transit_trip_request_custom_walk_speed(self):
        r = self.otp_instance.request_transit_trip_cost(
            self.from_pt, self.to_pt, "2024-01-15", "09:16", arrive_by=False, walk_speed=7.2)
        # Walking all the way
        self.assertAlmostEqual(r['trip_duration'], 27.9, places=1)   
        self.assertAlmostEqual(r['walk_distance'], 2940.45, places=1)

    def test_average_transit_trip_request_default_walk_speeed(self):
        r = self.otp_instance.request_avg_transit_trip_cost(
            self.from_pt, self.to_pt, "2024-01-15", "09:00", 15, 3)
        self.assertAlmostEqual(r['trip_duration'], 27.32, places=1)
        self.assertAlmostEqual(r['walk_distance'], 751.35, places=1)

    def test_average_transit_trip_request_custom_walk_speeed(self):
        r = self.otp_instance.request_avg_transit_trip_cost(
            self.from_pt, self.to_pt, "2024-01-15", "09:00", 15, 3, walk_speed=7.2)
        self.assertAlmostEqual(r['trip_duration'], 24.75, places=1)
        self.assertAlmostEqual(r['walk_distance'], 1627, places=1)

    def test_transit_cost_matrix_request_default_walk_speed(self):
        ref_matrix = Matrix(origins=[11, 13, 15], destinations=[21,23], 
                            data=[[27.316667, 26.383333], [27.240000, 25.950000], [24.926667, 24.696667]],
                            name="ref_transit_matrix")
        cost_matrix = self.otp_instance.request_transit_cost_matrix(
            self.from_gdf, self.to_gdf, "2024-01-15", "09:00", 15, 3)
        self._test_matrix(cost_matrix, ref_matrix)

    def test_transit_cost_matrix_request_custom_walk_speed(self):
        ref_matrix = Matrix(origins=[11, 13, 15], destinations=[21,23], 
                            data=[[24.75, 24.423333], [22.37, 20.853333], [18.85, 19.066667]],
                            name="ref_transit_matrix")
        cost_matrix = self.otp_instance.request_transit_cost_matrix(
            self.from_gdf, self.to_gdf, "2024-01-15", "09:00", 15, 3, walk_speed=7.2)
        self._test_matrix(cost_matrix, ref_matrix)