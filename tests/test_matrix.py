from importlib.resources import files
import pandas as pd
from pandas import testing as tm
import unittest

import accessto
from accessto.matrix import Matrix, read_csv 


class TestMatrix(unittest.TestCase):
    pass

    def setUp(self):

        # Find the path to to the test-directions
        # The src path is to the src/accessto directory. 
        src_path = files(accessto)
        root_path = src_path.parents[1]
        self.testdata_path = root_path / "tests" / "test_data" / "matrix"

        self.ref_matrix = Matrix(
            origins=[12, 29, 34],
            destinations=[56, 59, 62],
            data=[[11.1, 22.2, 33.3], [44.4, 55.5, 66.6], [77.7, 88.8, 99.9]],
            name="test_matrix"
        )

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

#region read_csv tests   
    def test_read_tall_full(self):
        """ Tests file read of a simple matrix in tall (stacked) format. """
        read_mat = read_csv(self.testdata_path / 'small_matrix_tall.csv', name="read_matrix")
        ref_mat = Matrix(
            origins=[1, 2], destinations=[4, 5, 6], data=[[10., 15., 20.], [5., 8., 12.]], name="ref_matrix"
        )
        self._test_matrix(read_mat, ref_mat)

    def test_read_tall_blanks_1(self):
        """ Tests file read of a simple matrix in tall (stacked) format with blanks, default fill value. """
        fill_value = 999.99
        read_mat = read_csv(self.testdata_path / 'small_matrix_tall_blanks.csv', name="read_matrix")
        ref_mat = Matrix(
            origins=[1, 2], destinations=[4, 5, 6], data=[[10., 15., 20.], [fill_value, fill_value, 12.]], name="ref_matrix"
        )
        self._test_matrix(read_mat, ref_mat)

    def test_read_tall_blanks_2(self):
        """ Tests file read of a simple matrix in tall (stacked) format with blanks, specified fill value. """
        fill_value = 222.22
        read_mat = read_csv(self.testdata_path / 'small_matrix_tall_blanks.csv', name="read_matrix", fill_value=fill_value)
        ref_mat = Matrix(
            origins=[1, 2], destinations=[4, 5, 6], data=[[10., 15., 20.], [fill_value, fill_value, 12.]], name="ref_matrix"
        )
        self._test_matrix(read_mat, ref_mat)

    def test_read_wide(self):
        """ Tests file read of simple matrix in wide format."""
        read_mat = read_csv(self.testdata_path / 'small_matrix_wide.csv', name="read_matrix")
        ref_mat = Matrix(
            origins=[5, 6, 7], destinations=[10, 11], data=[[21.5, 31.7], [41.5, 51.7], [61.5, 71.7]]
        )
        self._test_matrix(read_mat, ref_mat)

    @unittest.SkipTest
    def test_file_write_read_round_trip(self):
        pass
#endregion
    
#region class Matrix tests
        
    def test_creation_from_matrix(self):
        new_matrix = Matrix(self.ref_matrix)
        self._test_matrix(new_matrix, self.ref_matrix, check_name=True)

    def test_creation_from_df(self):
        new_matrix = Matrix(df=self.ref_matrix.matrix, name="test_matrix")
        self._test_matrix(new_matrix, self.ref_matrix, check_name=True)

    def test_creation_from_data(self):
        new_matrix = Matrix(
            origins=self.ref_matrix.matrix.index,
            destinations=self.ref_matrix.matrix.columns,
            data = self.ref_matrix.matrix.values, 
            name=self.ref_matrix.name
        )
        self._test_matrix(new_matrix, self.ref_matrix, check_name=True)

    def test_creation_from_data_negative_entries(self):
        with self.assertRaises(ValueError):
            ref_matrix = Matrix(
                origins=[12, 29, 34],
                destinations=[56, 59, 62],
                data=[[11.1, 22.2, -33.3], [44.4, 55.5, 66.6], [77.7, 88.8, 99.9]],
                name="test_matrix"
            )

    # todo: we can add some tests about matrix writing, later