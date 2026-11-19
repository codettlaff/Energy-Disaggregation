"""Generate processed Open-Meteo weather data with solar position."""
import os
import pandas as pd
import pvlib
import requests

def generate_open_meteo_data():

    # Location: approximate coordinates for Ausgrid postcode 2076
    time_zone = 'Australia/Sydney'
    lat = -33.8688
    lon = 151.2093

    base_dir = os.path.join(os.path.dirname(__file__), '..')
    processed_data_dir = os.path.join(base_dir, 'processed_data')
    os.makedirs(processed_data_dir, exist_ok=True)

    # Download hourly ERA5 weather data
    params = {
        'latitude': lat,
        'longitude': lon,
        'start_date': '2010-07-01',
        # One day past the Ausgrid range, so the 23:30 slot on 2013-06-30 can be interpolated
        'end_date': '2013-07-01',
        'hourly': 'temperature_2m,wind_speed_10m,shortwave_radiation,cloud_cover,'
                'direct_normal_irradiance,diffuse_radiation,sunshine_duration',
        'models': 'era5',
        'timezone': time_zone,
        'temperature_unit': 'celsius',
        'precipitation_unit': 'mm'}
    response = requests.get('https://archive-api.open-meteo.com/v1/archive', params=params)
    response.raise_for_status()
    df = pd.DataFrame(response.json()['hourly'])

    # Convert to datetime and interpolate from hourly to 30-minute resolution
    df['datetime'] = pd.to_datetime(df['time'])
    df = df.drop(columns='time')
    df = df.set_index('datetime').resample('30min').interpolate().reset_index()
    df = df[df['datetime'] <= '2013-06-30 23:30'].reset_index(drop=True)

    # Add solar position. Times are Sydney local; pvlib treats naive times as UTC,
    # so localise first. The repeated 02:00-02:59 hour when DST ends is treated as
    # standard time; it is night either way, so the choice does not matter.
    local_times = pd.DatetimeIndex(df['datetime']).tz_localize(
        time_zone, ambiguous=False, nonexistent='shift_forward')
    solar_position = pvlib.solarposition.get_solarposition(
        time=local_times, latitude=lat, longitude=lon)
    df['solar_zenith'] = solar_position['zenith'].values
    df['solar_azimuth'] = solar_position['azimuth'].values

    df.to_csv(os.path.join(processed_data_dir, 'open_meteo_processed_data.csv'), index=False)

if __name__ == "__main__":
    generate_open_meteo_data()