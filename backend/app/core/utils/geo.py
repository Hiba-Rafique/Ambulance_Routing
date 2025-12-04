"""
Geographic utility functions for distance calculations.
"""
import math
from typing import Tuple

def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate the great circle distance between two points
    on the earth specified in decimal degrees of latitude and longitude.
    
    Args:
        lat1, lon1: Latitude and Longitude of point 1 (in decimal degrees)
        lat2, lon2: Latitude and Longitude of point 2 (in decimal degrees)
        
    Returns:
        Distance in kilometers between the two points
    """
    # Convert decimal degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Radius of Earth in kilometers
    radius = 6371.0
    
    return radius * c
