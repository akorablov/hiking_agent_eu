import geocoder

def get_current_location():
    """
    Determines the user's current location based on their IP address.
    Returns:
        tuple: (latitude, longitude, city, country_code)
               Returns (None, None, None, None) if the location cannot be determined.
    """
    try:
        g = geocoder.ip('me')
        if g.ok:
            return g.latlng[0], g.latlng[1], g.city, g.country
        else:
            print("Could not determine location from IP.")
            return None, None, None, None
    except Exception as e:
        print(f"An error occurred during location lookup: {e}")
        return None, None, None, None

if __name__ == '__main__':
    latitude, longitude, city, country = get_current_location()
    if latitude:
        print(f"Latitude: {latitude}, Longitude: {longitude}, City: {city}, Country: {country}")
    else:
        print("Could not get your location.")
