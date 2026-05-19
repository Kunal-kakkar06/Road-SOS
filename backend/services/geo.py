import math

def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Returns distance in kilometres between two GPS points.
    Use the standard Haversine formula:
    a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlng/2)
    c = 2 * atan2(√a, √(1−a))
    d = R * c
    """
    # Radius of the Earth in km
    R = 6371.0

    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlng / 2) ** 2)
         
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    
    return distance
