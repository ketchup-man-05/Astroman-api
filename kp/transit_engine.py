import swisseph as swe
from datetime import datetime, timezone

def get_planets_at(when):
    """Planet longitudes AND retrograde flags at `when` (aware datetime; naive is read as UTC),
    using strict KP Ayanamsha. Powers both the live-planet header and the transit check at a
    future supportive window."""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    else:
        when = when.astimezone(timezone.utc)
    decimal_hour = when.hour + (when.minute / 60.0) + (when.second / 3600.0)
    jd = swe.julday(when.year, when.month, when.day, decimal_hour)
    
    # CRITICAL: Must be Krishnamurti for KP Horary Sub-Lord accuracy
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    
    planets = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, 
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, 
        "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE
    }
    
    positions = {}
    retrogrades = {}
    
    for name, p_id in planets.items():
        # FLG_SPEED tracks if the planet is moving backward (retrograde)
        raw_result = swe.calc_ut(jd, p_id, swe.FLG_SIDEREAL | swe.FLG_SPEED)
        coords = raw_result[0]
        
        positions[name] = coords[0]
        speed = coords[3]
        
        if name in ["Sun", "Moon", "Rahu", "Ketu"]:
            retrogrades[name] = False
        else:
            retrogrades[name] = speed < 0 

    # Ketu is exactly 180 degrees from Rahu
    positions["Ketu"] = (positions["Rahu"] + 180) % 360
    retrogrades["Ketu"] = False

    return positions, retrogrades


def get_live_planets():
    """Returns planet longitudes AND Retrograde status using strict KP Ayanamsha."""
    return get_planets_at(datetime.now(timezone.utc))