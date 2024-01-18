import numpy as np
import pandas as pd

from .matrix import Matrix

""" Module with function that calculate access to opportunities given a cost matrix and optional weights. """


#region Impedance Functions
def within_threshold(cost_matrix, threshold):
    """ Calculates impedance matrix assuming cumulative opportunities (1 if cost is within threshold, 0 otherwise)

    Parameters
    ----------
    cost_matrix: Matrix
        Cost matrix

    threshold: float or int
        threshold to test, should be real number > 0

    Returns
    -------
    Matrix
        Impedance matrix

    """
    if not (isinstance, cost_matrix, Matrix):
        raise AttributeError("parameter `cost_matrix` should be an instance of class Matrix.")
    if not (isinstance(threshold, float) or  isinstance(threshold, int)):
        raise AttributeError("Parameter `threshold` must either be a real number.")
    if threshold <= 0:
        raise ValueError("Expecting positive `threshold` parameter.")    

    cm = cost_matrix.matrix.to_numpy()
    impedance = np.where(cm <= threshold, 1, 0)
    return Matrix(data=impedance, origins=cost_matrix.matrix.index, destinations=cost_matrix.matrix.columns, name="within_threshold_impedance")


def negative_exp(cost_matrix, beta):
    """ Calculates impedance matrix assuming negative exponential decay function.

    Parameters
    ----------
    cost_matrix: Matrix
        Cost matrix

    beta: float
        beta parameter of negative exponential function. Should be a real number < 0.

    Returns
    -------
    Matrix
        Impedance matrix

    """
    if not (isinstance, cost_matrix, Matrix):
        raise AttributeError("parameter `cost_matrix` should be an instance of class Matrix.")
    if not (isinstance(beta, float) or  isinstance(beta, int)):
        raise AttributeError("Parameter `beta` must either be a negative real number.")
    if beta >= 0:
        raise ValueError("Expecting negative `beta` parameter.")
     
    cm = cost_matrix.matrix.to_numpy()
    impedance = np.exp(beta * cm)
    return Matrix(data=impedance, origins=cost_matrix.matrix.index, destinations=cost_matrix.matrix.columns, name="neg_exp_impedance")


def gaussian(cost_matrix, sigma):
    """ Calculates impedance matrix assuming Gaussian decay function.

    Parameters
    ----------
    cost_matrix: Matrix
        Cost matrix

    sigma: float
        standard deviation parameter of Guassian function, should be float > 0.
    
    Returns
    -------
    Matrix
        Impedance matrix

    """    
    if not (isinstance, cost_matrix, Matrix):
        raise AttributeError("parameter `cost_matrix` should be an instance of class Matrix.")
    if not (isinstance(sigma, float) or  isinstance(sigma, int)):
        raise AttributeError("Parameter `sigma` must either be a positve real number.")
    if sigma <= 0:
        raise ValueError("Expecting positive `sigma` parameter.")

    cm = cost_matrix.matrix.to_numpy()
    impedance = np.exp(-(cm * cm) / (2 * sigma * sigma))
    return Matrix(data=impedance, origins=cost_matrix.matrix.index, destinations=cost_matrix.matrix.columns, name="gaussian_impedance")

#endregion
    
#region Primary access measures  (cumulative opportunities)
def calc_impedance_matrix(cost_matrix, impedance_function, **kwargs):
    """ Calculates the impedance matrix given the stored cost matrix, saving in .impedance_matrix attribute. 
    
    Parameters
    ----------
    cost_matrix: Matrix
        Cost matrix

    impedance_function: function
        One of the impedance functions specified in this module. Current options are:
            within_threshold - for cumulative opportunities access
            negative_exp - for negative exponential gravity model
            gaussian - for gaussian weighted gravity model

    **kwargs:
        parameters expected by impedance function.

    Matrix
        Impedance matrix

    """
    return impedance_function(cost_matrix, **kwargs)

def calc_access_to_opportunities(cost_matrix, impedance_function, destination_weights=None, origin_weights=None, normalize="none", **kwargs):
    """ Calculates the access to opportunities, can be referred to as a 'primal' access measure. 

    These measures include cumulative opportunities, weighted gravity and competitive (not yet implemented) measures.
    
    Parameters
    ----------
    cost_matrix: Matrix
        Cost matrix

    impedance_function: function
        One of the impedance functions specified in this module. Current options are:
            within_threshold - for cumulative opportunities access
            negative_exp - for negative exponential gravity model
            gaussian - for gaussian weighted gravity model

    destination_weights: pd.Series, optional
        Destination weights for accessibility calculation, if None then weights 1.0 are assigned.
        Index must match cost_matrix columns.

    origin_weights: pd.Series, optional
        If defined, will sum access to opportunites for all origins into a single number.
        Index must match cost_matrix index.

    normalize: str
        one of the following options:
            "median": normalize access with respect to median access
            "average": normalize access with respect to average access
            "maximum": normalize access with respect to highest access
            "none": do not normalize. This is the default option
        This parameter is ignored if origin_weights is defined.

    **kwargs:
        parameters expected by impedance function.

    Returns
    -------
    pandas.Series or float
        if origin_weights is not defined, returns pandas.Series with the access to opportinities for each origin
        if origin_weights is defined, retuns float with the total access to opportunities for all origins.
    """
    if not (isinstance, cost_matrix, Matrix):
        raise AttributeError("parameter `cost_matrix` should be an instance of class Matrix.")
    if destination_weights is not None:
        if not(isinstance, destination_weights, pd.Series):
            raise AttributeError(
                "parameter `destination_weights` should be a pandas Series matching the cost_matrix colums.")
        if not destination_weights.index.equals(cost_matrix.matrix.columns):
            raise RuntimeError('If defined, `destination_weights` index must match `cost_matrix` columns.')
    if origin_weights is not None:
        if not(isinstance, origin_weights, pd.Series):
            raise AttributeError(
                "parameter `origin_weights` should be a pandas Series matching the cost_matrix index.")
        if not origin_weights.index.equals(cost_matrix.matrix.index):
            raise RuntimeError('If defined, `origin_weights` index must match `cost_matrix` index.')
    if normalize not in ["median", "average", "maximum", "none"]:
        raise ValueError("Invalid `normalize` parameter. ")


    impedance_matrix = calc_impedance_matrix(cost_matrix, impedance_function, **kwargs)

    if destination_weights is None:
        destination_access = pd.Series(
            index=impedance_matrix.matrix.index, data=impedance_matrix.matrix.sum(axis=1))
    else:
        destination_access = pd.Series(
            index=impedance_matrix.matrix.index, data=destination_weights.dot(impedance_matrix.matrix.transpose()))
    destination_access.name = "access_to_opportunities"

    if origin_weights is not None:
        return destination_access.dot(origin_weights)
    else:
        # Apply normalization
        if normalize == "median":
            return destination_access / destination_access.median()
        elif normalize == "average":
            return destination_access / destination_access.mean()
        elif normalize == "max":
            return destination_access / destination_access.max()
        else:
            return destination_access

#endregion
    
#region Dual access measures
def has_opportunity(cost_matrix, threshold):
    """ Calculates whether any opportunities are within input threshold for each origin. 

    Parameters
    ---------
    cost_matrix: Matrix
        Cost matrix
    threshold: float or int
        threshold to test, should be real number > 0

    Returns
    -------
    pandas.Series
        pandas series where the index is the same as that of the cost_matrix
        Each value is 1 if any opportunity is within threshold of that point, 0 otherwise
    """
    if not (isinstance, cost_matrix, Matrix):
        raise AttributeError("parameter `cost_matrix` should be an instance of class Matrix.")
    test_within_threshold = calc_impedance_matrix(cost_matrix, within_threshold, threshold=threshold)
    return pd.Series(data=np.max(test_within_threshold.matrix.to_numpy(), axis=1), index=cost_matrix.matrix.index)
    
def closest_opportunity(cost_matrix):
    """ Calculates cost to the closest opportunity from each origin.

    Parameters
    ---------
    cost_matrix: Matrix
        Cost matrix

    Returns
    -------
    pandas.Series
        pandas series where the index is the same as that of the cost_matrix
        Each value is the cost to the closest destination from this origin

    """
    if not (isinstance, cost_matrix, Matrix):
        raise AttributeError("parameter `cost_matrix` should be an instance of class Matrix.")
    cm = cost_matrix.matrix.to_numpy()
    return pd.Series(data=np.min(cm, axis=1), index=cost_matrix.matrix.index)

def nth_closest_opportunity(cost_matrix, n):
    """ Calculates cost to the nth closest opportunity from each origin.

    Parameters
    ----------
    cost_matrix: pandas.DataFrame
        Cost matrix with origin IDs as index and column IDs as columns. Values should be floats > 0
    n: int
        Nth-opportunity to which to calculate cost. Expecting an integer >= 2.

    Returns
    -------
    pandas.Series
        pandas series where the index is the same as that of the cost_matrix
        Each value corresponds to the nth-closest opportunity from the origin.

    """
    if not (isinstance, cost_matrix, Matrix):
        raise AttributeError("parameter `cost_matrix` should be an instance of class Matrix.")
    if not isinstance(n, int):
        raise AttributeError('Parameter `n` should be an integer >= 2.')
    if not n >= 2:
        raise ValueError('Parameter `n` should be an integer >= 2.')
    cm = cost_matrix.matrix.to_numpy()
    return pd.Series(data=np.partition(cm, kth=n-1, axis=1)[:, n-1], index=cost_matrix.matrix.index)



#endregion
