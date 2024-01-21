import unittest

import pandas as pd
from pandas import testing as tm

from accessto.matrix import Matrix
from accessto.access_opportunities import within_threshold, negative_exp, gaussian
from accessto.access_opportunities import calc_impedance_matrix, calc_access_to_opportunities
from accessto.access_opportunities import has_opportunity,closest_opportunity, nth_closest_opportunity


class TestAccessOpportunities(unittest.TestCase):

    def setUp(self):
        self.cost_matrix = Matrix(
            data = [[5.0, 10.0, 15.0], [18.0, 13.0, 8.0]],
            origins = [1, 2],
            destinations = [20, 21, 22], name="cost_matrix"
        )

    @staticmethod
    def _test_matrix(test_matrix, ref_matrix, name=None):
        """ Test matrix helping function that checks two matrices. Raises Assertion error if test fails."""
        tm.assert_frame_equal(
                left=test_matrix.matrix, 
                right=ref_matrix.matrix,
                check_dtype=False,
                check_names=False,
                check_exact=False
        )
        if name and test_matrix.name != name:
            raise AssertionError("Names do not match.")

    def test_impedance_within_threshold_3(self):
        """ Tests for within threshold impedance function with threshold of 3. This should be 0 everywhere. """
        ref_matrix = Matrix(
            data = [[0, 0, 0], [0, 0, 0]],
            origins = [1, 2],
            destinations = [20, 21, 22], name="ref_threshold_impedance_3"
        )
        result = within_threshold(self.cost_matrix, 3)
        self._test_matrix(result, ref_matrix)

    def test_impedance_within_threshold_25(self):
        """ Tests for within threshold impedance function with threshold of 25. This should be 1 everywhere. """
        ref_matrix = Matrix(
            data = [[1, 1, 1], [1, 1, 1]],
            origins = [1, 2],
            destinations = [20, 21, 22], name="ref_threshold_impedance_25"
        )
        result = within_threshold(self.cost_matrix, 25)
        self._test_matrix(result, ref_matrix)

    def test_impedance_within_threshold_10(self):
        """ Tests for within threshold impedance function with threshold of 10."""
        ref_matrix = Matrix(
            data = [[1, 1, 0], [0, 0, 1]],
            origins = [1, 2],
            destinations = [20, 21, 22], name="ref_threshold_impedance_10"
        )
        result = within_threshold(self.cost_matrix, 10)
        self._test_matrix(result, ref_matrix)

    def test_impedance_negative_exp(self):
        """ Test for negative exponential impedance function."""
        # ref matrix was calculated in Excel to avoid using the same code in the test as the implementation
        ref_matrix = Matrix(
            data = [[0.60653066, 0.36787944, 0.22313016], [0.16529889, 0.27253179, 0.44932896]],
            origins = [1, 2],
            destinations = [20, 21, 22], name="ref_nexp_impedance_0_1"
        )
        result = negative_exp(self.cost_matrix, beta=-0.1)
        self._test_matrix(result, ref_matrix)


    def test_impedance_gaussian(self):
        """ Test for Gaussian impedance function."""
        # ref matrix was calculated in Excel to avoid using the same code in the test as the implementation
        ref_matrix = Matrix(
            data = [[0.88249690, 0.60653066, 0.32465247], [0.19789870, 0.42955736, 0.72614904]],
            origins = [1, 2],
            destinations = [20, 21, 22], name="ref_gauss_impedance_10"
        )
        result = gaussian(self.cost_matrix, sigma=10)
        self._test_matrix(result, ref_matrix)


    def test_dual_opportunity_within_threshold_7(self):
        """ Test dual access: opportunity within the cost threshold. """
        ref_series = pd.Series(index=[1, 2], data=[1, 0])
        result = has_opportunity(self.cost_matrix, 7)
        tm.assert_series_equal(result, ref_series, check_names=False, check_dtype=False)

    def test_dual_closest_opportunity(self):
        """ Test dual access: closest opportunity"""
        ref_series = pd.Series(index=[1, 2], data=[5.0, 8.0])
        result = closest_opportunity(self.cost_matrix)
        tm.assert_series_equal(result, ref_series, check_names=False, check_dtype=False)

    def test_dual_2nd_closest_opportunity(self):
        """Test dual access: second closest opportunity"""
        ref_series = pd.Series(index=[1, 2], data=[10.0, 13.0])
        result = nth_closest_opportunity(self.cost_matrix, 2)
        tm.assert_series_equal(result, ref_series, check_names=False, check_dtype=False)

    def test_primal_gaussian_no_weights(self):
        """ Test the access to opportunities with no weights. """
        result = calc_access_to_opportunities(
             self.cost_matrix, gaussian, destination_weights=None, origin_weights=None, 
             normalize="none", sigma=10
        )
        ref_series = pd.Series(
            index=[1, 2], data=[0.88249690 + 0.60653066 + 0.32465247, 
                                0.19789870 + 0.42955736 + 0.72614904]
        )
        tm.assert_series_equal(result, ref_series, check_names=False, check_dtype=False)


    def test_primal_gaussian_dest_weights(self):
        """ Test the access to opportunities with destination weights. """
        destination_weights = pd.Series(data=[1, 3, 5], index=[20, 21, 22])
        result = calc_access_to_opportunities(
             self.cost_matrix, gaussian, destination_weights=destination_weights, origin_weights=None, 
             normalize="none", sigma=10
        )
        ref_series = pd.Series(
            index=[1, 2], data=[0.88249690 + 3*0.60653066 + 5*0.32465247, 
                                0.19789870 + 3*0.42955736 + 5*0.72614904]
        )
        tm.assert_series_equal(result, ref_series, check_names=False, check_dtype=False)

    def test_primal_gaussian_orig_weights(self):
        """ Test the access to opportunities with origin weights. """
        origin_weights = pd.Series(index=[1, 2], data=[12, 15])
        result = calc_access_to_opportunities(
             self.cost_matrix, gaussian, destination_weights=None, origin_weights=origin_weights, 
             normalize="none", sigma=10
        )
        ref_result = (0.88249690 + 0.60653066 + 0.32465247) * 12 + \
                     (0.19789870 + 0.42955736 + 0.72614904) * 15
        self.assertAlmostEqual(result, ref_result, places=5)

    def test_primal_gaussian_both_weights(self):
        """ Test the access to opportunities with both origin and destination weights. """
        origin_weights = pd.Series(index=[1, 2], data=[12, 15])
        destination_weights = pd.Series(data=[1, 3, 5], index=[20, 21, 22])
        result = calc_access_to_opportunities(
             self.cost_matrix, gaussian, destination_weights=destination_weights, origin_weights=origin_weights, 
             normalize="none", sigma=10
        )
        ref_result = (0.88249690 + 3*0.60653066 + 5*0.32465247) * 12 + \
                     (0.19789870 + 3*0.42955736 + 5*0.72614904) * 15
        self.assertAlmostEqual(result, ref_result, places=5)
