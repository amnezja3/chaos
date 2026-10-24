"""Fail-closed scope for optional world pilot; never affects ordinary scanning."""
import math
import os
import time


def allowed(user,spatial):
    try:
        account=os.environ.get('CHAOS_POI_WORLD_PILOT_USER','')
        if not account or not isinstance(user,str) or user!=account:return False
        until=float(os.environ.get('CHAOS_POI_WORLD_PILOT_UNTIL','0'))
        if not math.isfinite(until) or not 0<until-time.time()<=86400:return False
        lat,lon=map(float,os.environ.get('CHAOS_POI_WORLD_PILOT_CENTER','').split(','))
        radius=float(spatial['radius'])
        actual_lat=float(spatial['lat']);actual_lon=float(spatial['lon'])
        if not all(map(math.isfinite,(lat,lon,radius,actual_lat,actual_lon))):return False
        if not -90<=lat<=90 or not -180<=lon<=180 or radius!=300:return False
        return round(actual_lat,6)==round(lat,6) and round(actual_lon,6)==round(lon,6)
    except (ValueError,TypeError,KeyError):
        return False
