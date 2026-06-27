import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Oblicza odległość w kilometrach między dwoma punktami geograficznymi.
    Współrzędne muszą być podane w stopniach dziesiętnych.
    """
    # Promień Ziemi w kilometrach
    R = 6371000

    # Konwersja stopni na radiany
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Różnice współrzędnych
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Wzór Haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Odległość w kilometrach
    distance = R * c
    return distance

if __name__ == "__main__":
    lat1 = 52.2296756  # Warszawa
    lon1 = 21.0122287
    lat2 = 50.0646501  # Kraków
    lon2 = 19.9449799

    distance_m = haversine_distance(lat1, lon1, lat2, lon2)
    print(f"Odległość: {distance_m:.2f} m")
