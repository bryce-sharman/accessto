""" Module containing the class Matrix, and other functions to help matrix FileIO. """

from pathlib import Path
import numpy as np
import pandas as pd
from pandas.api.types import is_integer_dtype, is_float_dtype

INDEX_NAMES = ["origin_id", "destination_id"]

def read_csv(fp, fill_value=999.99, name="matrix"):
    """ Read matrix from CSV formatted file, in either tall or wide format, storing in the matrix attribute.
    
    Parameters
    ----------
    fp: str or pathlib.Path
        Filepath to file containing the matrix
    fill_value: float
        value with which to replace empty cells.
    name: str, optional
        Matrix name, defaults to "matrix"

    Returns
    -------
    Matrix
        Input data from file in Matrix format

    Notes
    -----

    The assumed tall file format is:
    origin_header, destination_header, cost_header
    origin_id_1, destination_id_1, cost_1
    origin_id_2, destination_id_2, cost_2
    origin_id_3, destination_id_3, cost_3

    The assumed wide file fomat is:
               , destination_id_1, destination_id_2, ...
    origin_id_1, cost_1_1        , cost_1_2        , ...
    origin_id_2, cost_2_1        , cost_2_2        , ...

    origin_ids and destination_ids are all assumed to be integers. 

    """
    fp = Path(fp)
    if not fp.is_file():
        raise FileNotFoundError(f"File {fp} does not exist.")
    df = pd.read_csv(fp, index_col=[0], header=[0])
    
    # Infer if in tall or wide format
    # Try and convert the columns to an integer, if raises an value error, then test for tall format.
    try:
        df.columns = df.columns.astype(int)
        # At this point we know we have integer columns and hence should be a wide format
        #  already in the right shape, just rename
        df.index.name = INDEX_NAMES[0]
        df.columns.name = INDEX_NAMES[1]
        
    except ValueError:
        # If has three columns in total (first is the index) then it's tall format, otherwise it's an error
        if df.shape[1] != 2:
            raise RuntimeError("Invalid file format. File has text column labels suggesting tall format, " 
                               "but does not have required three columns.")
        # Add the first column to the index
        df = df.set_index(df.columns[0], append=True)
        s = df.squeeze()
        s.index.names = INDEX_NAMES
        df = s.unstack().fillna(fill_value)
  
    return Matrix(df=df, name=name)


class Matrix():
    """ Matrix is a thin wrapper on a pandas DataFrame that checks class inputs to ensure validity and contains specific read/write methods. 

    The purpose of this class is primarily to ensure that other parts of the code to not need to check matrix validity and handle file IO.
    
    There are different ways that a Matrix class can be initialized:
    - from another Matrix (think copy constructor)
    - from a pandas DataFrame
    - with separate arguments for matrix values, origin IDs and destination IDs
    - an empty Matrix

    Matrices can also be constructed from the read_csv function included in the module.

    Parameters
    ----------
    matrix: Matrix or None
        If defined, creates the matrix object based on another matrix, used to create a copy of another matrix 
    df: pandas DataFrame of None
        If defined, creates the matrix object based on a pandas dataframe, which is assumed to be in the same format as used in a Matrix.
    data=: array-like or None
    origins: array-like or None
    destinations: array-like or None
        If defined, creates the matrix from the `data`, `origins` and `destinations` arguments.
        The data is expected to be a two-dimensional array wile the origins and destinations are one-dimension arrays, corresponding 
        is size to the input `data`
    name=: str, Optional
        matrix name, defaults to "matrix"

    Attributes
    ----------
    matrix: pd.DataFrame 
        Matrix in wide format. Index is expected to be the origin point ids, columns is expected to be the destination point ids.
    name: str
        Matrix name, storing here instead of on the DataFrame to allow for blank constructions.


    Methods
    -------
    to_csv: 
        Write matrix to CSV file, can either write in tall or wide formats.

    """

    def __init__(self, matrix=None, df = None, data=None, origins=None, destinations=None, name="matrix"):

        if matrix is not None:
            # Copy from another Matrix object
            if df is not None or data is not None or origins is not None or destinations is not None:
                raise AttributeError("If `matrix` parameter is defined, then `df`, `data`, `origins` and `destinations` must all be None.")
            if not isinstance(matrix, Matrix):
                raise AttributeError("`matrix` parameter must be of type Matrix.")
            self._matrix = matrix.matrix.copy()
        elif df is not None:
            # Set from pandas DataFrame
            if data is not None or origins is not None or destinations is not None:
                raise AttributeError("If `df` parameter is defined, then `data`, `origins` and `destinations` must all be None.")
            if not isinstance(df, pd.DataFrame):
                raise AttributeError("`df` parameter must be a pandas DataFrame.")
            self._test_matrix(df)
            self._matrix = df
        elif data is not None:
            # From separate data, origins and destinations
            if origins is None or destinations is None:
                raise AttributeError("If parameter `data` is defined, then `origins` and `destinations` must also be defined.")
            test_df = pd.DataFrame(data=data, index=origins, columns=destinations)
            self._test_matrix(test_df)
            self._matrix = test_df
        else:
            # create an empty matrix, probably to read data from a file later
            self._matrix = None
        self._name = name

    def __eq__(self, matrix):
        """ Return True if the matrices are the same (allow the names to differ). """
        return self._matrix.equals(matrix.matrix)


    #region Properties
    @property
    def matrix(self):
        return self._matrix

    @matrix.setter
    def matrix(self, matrix):
        self._test_matrix(matrix)
        self._matrix = matrix

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if isinstance(name, str):
            self._name = name
    #endregion

    def to_csv(self, fp, format="tall"):
        """ Write matrix to CSV file, can either write in tall or wide formats.

        Parameters
        ----------
        fp: str or pathlib.Path
            Filepath to which to write the matrix    
        format: str
            matrix format, must be either "tall" or "wide"
        
        Returns
        -------
        None

        """
        fp = Path(fp)
        if format == "tall":
            df = self._matrix.stack()
            df.to_csv(fp)
        elif format == "wide":
            self._matrix.to_csv(fp)
        else:
            raise AttributeError("format must be one of 'tall' or 'wide'")


    def _test_matrix(self, df):
        """ Tests an input matrix for valid inputs.
        
        Tests include:
            - is a Pandas DataFrame
            - is two-dimensional
            - values are all integers or floats and are all > 0 (should be true for either cost or impedance matrices.)
            - index and columns are both composed of integers

        Parameters
        ----------
        df: pd.DataFrame
            matrix to test
        
        Returns
        -------
        None

        Raises
        ------
        AttributeError:
            matrix is not a pandas DataFrame
            index or columns are not integers
            values are not integers or floats
        ValueError:
            non-integer index or columns
            negative entries in values
        """
        err_msg1 = "matrix should be pandas DataFrame with integer index and columns corresponding to point IDS. " \
                   "Values should be real numbers > 0."
        err_msg2 = "All values in either a cost or an impedance matrix should be real numbers > 0."
        if not (isinstance, df, pd.DataFrame):
            raise AttributeError(err_msg1)
        if not (len(df.shape) == 2 and is_integer_dtype(df.index) and is_integer_dtype(df.columns)):
            raise ValueError(err_msg1)
        # Now loop over all columns and check that the dtypes are int or float
        for c in df.columns:
            if not (is_integer_dtype(df[c]) or is_float_dtype(df[c])):
                raise AttributeError(err_msg1)
            if df[c].min() < 0:
                raise ValueError(err_msg2)
        return
