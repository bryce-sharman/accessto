import numpy as np
import pandas as pd

""" Module with function that calculate access to opportunities given a cost matrix and optional weights. """

def process_cost_matrix(df, fill_value=np.NaN):
    """ 
    Process cost matrix from tall format produced by OTP2TravelTimeComputer and
    R5PYTravelTimeComputer to a wide format suitable for accessibility calculations.
    
    Paramters
    ---------
    df: pandas.DataFrame
        Cost matrix in format produced by OTP2TravelTimeComputer and R5PYTravelTimeComputer.
        This format expects the following columns: 'from_id', 'to_id', 'travel_time'.
        The index is not used.
    fill_value: float, optional
        Value with which to fill any blanks in the matrix after post-processing

    Returns:
    pd.DataFrame
        cost matrix in wide format, with indices corresponding to 'from_id`, `to_id`

    """
    s = df.set_index(['from_id', 'to_id']).squeeze()
    return s.unstack(fill_value=fill_value)


#region Impedance Functions
def within_threshold(df, threshold):
    """ Calculates impedance matrix assuming cumulative opportunities (1 if cost is within threshold, 0 otherwise)

    Parameters
    ----------
    df: pd.DataFrame
        Cost matrix in format produced by OTP2TravelTimeComputer and R5PYTravelTimeComputer.
    threshold: float or int
        threshold to test, should be real number > 0

    Returns
    -------
    pd.DataFrame
        Impedance matrix in wide format.

    """
    cost_matrix = process_cost_matrix(df)
    cm = cost_matrix.to_numpy()
    impedance = np.where(cm <= threshold, 1, 0)
    return_df = pd.DataFrame(
        data=impedance, 
        index=cost_matrix.index, 
        columns=cost_matrix.columns, 
        dtype=np.int32
    )
    return_df.index.name = "from_id"
    return_df.columns.name = "to_id"
    return_df.name="within_threshold_impedance"
    return return_df

def negative_exp(df, beta):
    """ Calculates impedance matrix assuming negative exponential decay function.

    Parameters
    ----------
    df: pd.DataFrame
        Cost matrix in format produced by OTP2TravelTimeComputer and R5PYTravelTimeComputer.
    beta: float
        beta parameter of negative exponential function. Should be a real number < 0.

    Returns
    -------
    pd.DataFrame
        Impedance matrix in wide format.

    """
    cost_matrix = process_cost_matrix(df)
    if beta >= 0:
        raise ValueError("Expecting negative `beta` parameter.")
    cm = cost_matrix.to_numpy()
    impedance = np.exp(beta * cm)
    return_df = pd.DataFrame(
        data=impedance, 
        index=cost_matrix.index, 
        columns=cost_matrix.columns, 
        dtype=np.float64
    )
    return_df.index.name = "from_id"
    return_df.columns.name = "to_id"
    return_df.name="neg_exp_impedance"
    return return_df


def gaussian(df, sigma):
    """ Calculates impedance matrix assuming Gaussian decay function.

    Parameters
    ----------
    df: pd.DataFrame
        Cost matrix in format produced by OTP2TravelTimeComputer and R5PYTravelTimeComputer.
    sigma: float
        standard deviation parameter of Guassian function, should be float > 0.
    
    Returns
    -------
    pd.DataFrame
        Impedance matrix in wide format.

    """    
    cost_matrix = process_cost_matrix(df)
    if sigma <= 0:
        raise ValueError("Expecting positive `sigma` parameter.")
    cm = cost_matrix.to_numpy()
    impedance = np.exp(-(cm * cm) / (2 * sigma * sigma))
    return_df = pd.DataFrame(
        data=impedance, 
        index=cost_matrix.index, 
        columns=cost_matrix.columns, 
        dtype=np.float64
    )
    return_df.index.name = "from_id"
    return_df.columns.name = "to_id"
    return_df.name="gaussian_impedance"
    return return_df

# #endregion
    
#region Primary access measures  (cumulative opportunities)
def calc_impedance_matrix(df, impedance_function, **kwargs):
    """ Calculates the impedance matrix given the stored cost matrix, saving in .impedance_matrix attribute. 
    
    Parameters
    ----------
    df: pandas.DataFrame
        Cost matrix in format produced by OTP2TravelTimeComputer and R5PYTravelTimeComputer.
        This format expects the following columns: 'from_id', 'to_id', 'travel_time'.
        The index is not used.

    impedance_function: function
        One of the impedance functions specified in this module. Current options are:
            within_threshold - for cumulative opportunities access
            negative_exp - for negative exponential gravity model
            gaussian - for gaussian weighted gravity model

    **kwargs:
        parameters expected by impedance function.

    Returns
    -------
    pd.DataFrame
        Impedance matrix in wide format.

    """
    return impedance_function(df, **kwargs)

def calc_access_to_opportunities(df, impedance_function, destination_weights=None, origin_weights=None, normalize="none", **kwargs):
    """ Calculates the access to opportunities, can be referred to as a 'primal' access measure. 

    These measures include cumulative opportunities, weighted gravity and competitive (not yet implemented) measures.
    
    Parameters
    ----------
    df: pandas.DataFrame
        Cost matrix in format produced by OTP2TravelTimeComputer and R5PYTravelTimeComputer.
        This format expects the following columns: 'from_id', 'to_id', 'travel_time'.
        The index is not used.

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
    if normalize not in ["median", "average", "maximum", "none"]:
        raise ValueError("Invalid `normalize` parameter. ")


    impedance_matrix = calc_impedance_matrix(df, impedance_function, **kwargs)

    if destination_weights is None:
        destination_access = pd.Series(
            index=impedance_matrix.index, data=impedance_matrix.sum(axis=1))
    else:
        if not destination_weights.index.equals(impedance_matrix.columns):
            RuntimeWarning("Reindexing destination weights vector to match cost matrix columns.")
            destination_weights = destination_weights.reindex(impedance_matrix.columns, fill_value=0.0)
        destination_access = pd.Series(
                index=impedance_matrix.index, data=destination_weights.dot(impedance_matrix.transpose()))

    if origin_weights is not None:
        if not origin_weights.index.equals(impedance_matrix.index):
            origin_weights = origin_weights.reindex(impedance_matrix.index, fill_value=0.0)
            RuntimeWarning('Reindex origin weights vector to mach cost_matrix` index.')
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
def has_opportunity(df: pd.DataFrame, threshold: int | float, reverse_direction: bool=False):
    """ Calculates whether any opportunities are within threshold cost. 

    Parameters
    ---------
    df: pandas.DataFrame
        Cost matrix in format produced by OTP2TravelTimeComputer and R5PYTravelTimeComputer.
        This format expects the following columns: 'from_id', 'to_id', 'travel_time'.
        The index is not used.
    threshold: float or int
        threshold to test, should be real number > 0
    reverse_direction: bool
        If False, tests whether any destination is within threshold cost of origin, this is the default.
        If True, reverses test to if any origin is within threshold distance of destination.

    Returns
    -------
    pandas.Series
        1 if any opportunity is within threshold, 0 otherwise
        If reverse_direction is False then the index is the cost_matrix origins,
        otherwise the index is the cost_matrix destinations.

     """
    test_within_threshold = calc_impedance_matrix(df, within_threshold, threshold=threshold)
    
    if not reverse_direction:
        data = np.max(test_within_threshold.to_numpy(), axis=1)
        index = test_within_threshold.index
    else:
        data = np.max(test_within_threshold.to_numpy(), axis=0)
        index = test_within_threshold.columns
    return pd.Series(data=data, index=index, dtype=np.int32)
    
def closest_opportunity(df: pd.DataFrame, reverse_direction: bool=False):
    """ Calculates cost to the closest opportunity from each origin.

    Parameters
    ---------
    df: pandas.DataFrame
        Cost matrix in format produced by OTP2TravelTimeComputer and R5PYTravelTimeComputer.
        This format expects the following columns: 'from_id', 'to_id', 'travel_time'.
        The index is not used.
    reverse_direction: bool
        If False, calculates closest opportunity from each origin, this is the default.
        If True, reverses test to calculate closest opportunity to destination.

    Returns
    -------
    pandas.Series
        Closest opportunity from each origin (if reverse_direction flag is False),
        or to each destination (if reverse_direction flag is True).

    """
    cost_matrix = process_cost_matrix(df)
    cm = cost_matrix.to_numpy()

    if not reverse_direction:
        data = np.min(cm, axis=1, initial=10000.0, where=np.isfinite(cm))
        index = cost_matrix.index
    else:
        data = np.min(cm, axis=0, initial=10000.0, where=np.isfinite(cm))
        index = cost_matrix.columns
    return pd.Series(data=data, index=index)

def nth_closest_opportunity(df, n, reverse_direction: bool=False):
    """ Calculates cost to the nth closest opportunity from each origin.

    Parameters
    ----------
    df: pandas.DataFrame
        Cost matrix in format produced by OTP2TravelTimeComputer and R5PYTravelTimeComputer.
        This format expects the following columns: 'from_id', 'to_id', 'travel_time'.
        The index is not used.
    n: int
        Nth-opportunity to which to calculate cost. Expecting an integer >= 2.
    reverse_direction: bool
        If False, calculates nth-closest opportunity from each origin, this is the default.
        If True, reverses test to calculate nth-closest opportunity to destination.

    Returns
    -------
    pandas.Series
        pandas series where the index is the same as that of the cost_matrix
        Each value corresponds to the nth-closest opportunity from the origin.

    """
    if not isinstance(n, int):
        raise AttributeError('Parameter `n` should be an integer >= 2.')
    if not n >= 2:
        raise ValueError('Parameter `n` should be an integer >= 2.')
    cost_matrix = process_cost_matrix(df)
    cm = cost_matrix.to_numpy()
    if not reverse_direction:
        data = np.sort(cm, axis=1)[:, n-1]
        index=cost_matrix.index
    else:
        data = np.sort(cm, axis=0)[n-1, :]
        index=cost_matrix.columns
    return pd.Series(data=data, index=index)

# #endregion
