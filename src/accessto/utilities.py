from geopandas import GeoDataFrame
from .enumerations import ID_COLUMN

def test_od_input(gdf):
    """ Test origin/destination input to ensure that it meets expected format.
    
    Arguments:
        gdf: 

    Raises:
        RuntimeError:
            Invalid format

    """
    if not isinstance(gdf, GeoDataFrame):
        raise RuntimeError("Points list are not a geopandas.GeoDataFrame")
    if ID_COLUMN not in gdf.columns:
        raise RuntimeError("Points list must have columns 'ID'.")
    