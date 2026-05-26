"""
Google Maps ETA service with haversine fallback.
If GOOGLE_MAPS_API_KEY is set, uses the real Directions API.
Otherwise, uses straight-line distance + city speed estimation.
"""
import os
import math
from dotenv import load_dotenv

load_dotenv()

_gmaps = None


def _get_gmaps():
    global _gmaps
    if _gmaps is None:
        key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not key or key.startswith("AIzaSy_your"):
            return None
        try:
            import googlemaps
            _gmaps = googlemaps.Client(key=key)
        except ImportError:
            print("[Maps] googlemaps package not installed — using fallback")
            return None
    return _gmaps


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate great-circle distance between two points in km."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


async def get_eta_and_distance(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> dict:
    """
    Returns ETA and distance from origin to hospital.
    Uses Google Maps Directions API with live traffic if API key is set.
    Falls back to haversine + city speed estimate otherwise.
    """
    route_url = (
        f"https://www.google.com/maps/dir/"
        f"{origin_lat},{origin_lng}/"
        f"{dest_lat},{dest_lng}"
    )

    # Try Google Maps API first
    gmaps = _get_gmaps()
    if gmaps is not None:
        try:
            result = gmaps.directions(
                origin=(origin_lat, origin_lng),
                destination=(dest_lat, dest_lng),
                mode="driving",
                departure_time="now",
                traffic_model="best_guess",
            )

            if result:
                leg = result[0]["legs"][0]
                duration_minutes = leg.get(
                    "duration_in_traffic", leg["duration"]
                )["value"] // 60
                distance_km = leg["distance"]["value"] / 1000

                return {
                    "duration_minutes": duration_minutes,
                    "duration_text": f"{duration_minutes} min",
                    "distance_km": round(distance_km, 1),
                    "route_url": route_url,
                }
        except Exception as e:
            print(f"[Maps] Google API error: {e} — using fallback")

    # Fallback: haversine distance + city speed estimate
    km = haversine_km(origin_lat, origin_lng, dest_lat, dest_lng)
    # Road distance is typically ~1.3x straight-line in cities
    road_km = km * 1.3
    # Estimate ~25 km/h average in Bengaluru traffic
    mins = max(int(road_km / 25 * 60), 1)

    return {
        "duration_minutes": mins,
        "duration_text": f"~{mins} min",
        "distance_km": round(road_km, 1),
        "route_url": route_url,
    }
