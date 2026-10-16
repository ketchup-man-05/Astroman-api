def _geocoders():
    """Lazy geopy import — common cities work without it installed."""
    try:
        from geopy.geocoders import Nominatim, Photon
        return Nominatim, Photon
    except ImportError:
        return None, None


def get_coordinates(city_name):
    """Takes a city name and returns the exact Latitude and Longitude safely."""
    city_clean = city_name.lower().strip()

    # 1. Fast-track common cities to bypass cloud API blocks instantly
    common_cities = {
        "shimla": (31.1048, 77.1734),
        "delhi": (28.7041, 77.1025),
        "new delhi": (28.6139, 77.2090),
        "mumbai": (19.0760, 72.8777),
        "bangalore": (12.9716, 77.5946),
        "chennai": (13.0827, 80.2707),
        "london": (51.5074, -0.1278),
        "new york": (40.7128, -74.0060)
    }
    if city_clean in common_cities:
        return common_cities[city_clean]

    Nominatim, Photon = _geocoders()
    if Photon is None:
        return None, None

    # 2. Try Photon (Cloud-friendly open geocoder)
    try:
        geolocator = Photon(user_agent="astroman_kp_bot")
        location = geolocator.geocode(city_name, timeout=5)
        if location:
            return round(location.latitude, 4), round(location.longitude, 4)
    except Exception:
        pass

    # 3. Fallback to Nominatim
    try:
        geolocator = Nominatim(user_agent="astroman_kp_bot_backup")
        location = geolocator.geocode(city_name, timeout=5)
        if location:
            return round(location.latitude, 4), round(location.longitude, 4)
    except Exception:
        pass

    return None, None
