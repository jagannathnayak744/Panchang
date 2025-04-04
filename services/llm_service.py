


# llm_service.py
import math
import re
import random
import requests
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import ephem
from skyfield.api import load
from skyfield.framelib import ecliptic_frame
from models.panchang import Panchang

GOOGLE_API_KEY = "AIzaSyARW0InTpmvVUavE1Ur6zhJgIMuYvdZv2U"

def geocode_location(location_name: str) -> tuple:
    """Get coordinates using Google Geocoding API"""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'address': location_name, 'key': GOOGLE_API_KEY}
    response = requests.get(url, params=params)
    data = response.json()
    
    if data['status'] != 'OK':
        raise ValueError(f"Geocoding error: {data.get('error_message', 'Unknown error')}")
    
    loc = data['results'][0]['geometry']['location']
    return loc['lat'], loc['lng']

def get_timezone(lat: float, lng: float) -> ZoneInfo:
    """Get timezone using Google Time Zone API"""
    url = "https://maps.googleapis.com/maps/api/timezone/json"
    params = {
        'location': f"{lat},{lng}",
        'timestamp': 0,
        'key': GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if data['status'] != 'OK':
        raise ValueError(f"Timezone error: {data.get('error_message', 'Unknown error')}")
    
    return ZoneInfo(data['timeZoneId'])

def get_sun_times(lat: float, lng: float, date: date, tz: ZoneInfo) -> tuple:
    """Calculate sunrise/sunset times in local timezone"""
    observer = ephem.Observer()
    observer.date = date
    observer.lat = str(lat)
    observer.lon = str(lng)
    
    try:
        sunrise = ephem.localtime(observer.next_rising(ephem.Sun())).astimezone(tz)
        sunset = ephem.localtime(observer.next_setting(ephem.Sun())).astimezone(tz)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        sunrise = sunset = None
        
    return sunrise, sunset

def get_moon_times(lat: float, lng: float, date: date, tz: ZoneInfo) -> tuple:
    """Calculate moonrise/moonset times in local timezone"""
    observer = ephem.Observer()
    observer.date = date
    observer.lat = str(lat)
    observer.lon = str(lng)
    
    try:
        moonrise = ephem.localtime(observer.next_rising(ephem.Moon())).astimezone(tz)
        moonset = ephem.localtime(observer.next_setting(ephem.Moon())).astimezone(tz)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        moonrise = moonset = None
        
    return moonrise, moonset

def get_sun_moon_longitudes(input_date: date):
    """Calculate tropical longitudes of Sun and Moon"""
    eph = load('de421.bsp')
    ts = load.timescale()
    date_utc = ts.utc(input_date.year, input_date.month, input_date.day)
    
    sun_position = eph['earth'].at(date_utc).observe(eph['sun']).apparent().frame_latlon(ecliptic_frame)
    moon_position = eph['earth'].at(date_utc).observe(eph['moon']).apparent().frame_latlon(ecliptic_frame)
    
    return sun_position[1].degrees % 360, moon_position[1].degrees % 360

def calculate_ayanamsa(input_date: date) -> float:
    """Lahiri ayanamsa approximation"""
    year_fraction = input_date.year + (input_date.timetuple().tm_yday / 365.25)
    return 23.853 + (year_fraction - 2000) * 0.013958

def calculate_tithi(sun_long: float, moon_long: float):
    """Calculate Tithi with paksha"""
    diff = (moon_long - sun_long) % 360
    tithi_number = int(diff // 12) + 1

    tithi_list = [
        "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", 
        "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", 
        "Trayodashi", "Chaturdashi", "Purnima", "Pratipada", "Dwitiya", 
        "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami", 
        "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", 
        "Amavasya"
    ]

    paksha = "Shukla" if tithi_number <= 15 else "Krishna"
    return tithi_list[(tithi_number - 1) % 30], paksha

def calculate_yoga(sun_long: float, moon_long: float, ayanamsa: float):
    """Calculate Yoga with sidereal adjustment"""
    sid_sun = (sun_long - ayanamsa) % 360
    sid_moon = (moon_long - ayanamsa) % 360
    yoga_angle = (sid_sun + sid_moon) % 360
    return [
        "Vishkumbha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
        "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda", "Vriddhi",
        "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata",
        "Variyana", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha",
        "Shukla", "Brahma", "Indra", "Vaidhriti"
    ][int(yoga_angle // (13 + 20/60)) % 27]

def calculate_karana(sun_long: float, moon_long: float):
    """Calculate Karana"""
    diff = (moon_long - sun_long) % 360
    karana_index = int(diff // 6) % 60
    return (["Kimstughna"] + ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]*8 + 
            ["Shakuni", "Chatushpada", "Nagava"])[karana_index]

def calculate_nakshatra(moon_long: float, sunrise_dt: datetime):
    """Calculate Nakshatra with end time"""
    moon_long_corr = (moon_long - 26.666) % 360
    index = int(moon_long_corr // 13.3333) % 27

    nakshatra_names = [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
        "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", 
        "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", 
        "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", 
        "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
    ]
    
    # Calculate end time
    remainder = 13.3333 - (moon_long_corr % 13.3333)
    hours_remaining = remainder / (13.176396 / 24)
    end_time = sunrise_dt + timedelta(hours=hours_remaining)
    return f"{nakshatra_names[index]} upto {end_time.strftime('%H:%M')}"

def get_kaal_timings(sunrise, sunset):
    """
    Dynamically calculate Rahu Kaal, Gulika Kaal, and Yamaganda timings.
    - Each period = (sunset - sunrise) / 8.
    """

    if not isinstance(sunrise, datetime) or not isinstance(sunset, datetime):
        raise ValueError("Sunrise and Sunset must be datetime objects")

    total_day_duration = sunset - sunrise
    part_duration = total_day_duration / 8  # Divide daytime into 8 equal parts

    # Weekday-based time slot mappings (0=Monday, 6=Sunday)
    rahu_kaal_slots = [2, 7, 5, 6, 4, 3, 8]  # 1-based index
    yamaganda_slots = [4, 3, 2, 1, 7, 6, 5]
    gulika_kaal_slots = [7, 5, 6, 3, 2, 1, 4]

    # Get the current weekday index (0=Monday, 6=Sunday)
    weekday_idx = sunrise.weekday()

    # Calculate the start times dynamically
    rahu_start = sunrise + (rahu_kaal_slots[weekday_idx] - 1) * part_duration
    yamaganda_start = sunrise + (yamaganda_slots[weekday_idx] - 1) * part_duration
    gulika_start = sunrise + (gulika_kaal_slots[weekday_idx] - 1) * part_duration

    return {
        "Rahu Kaal": (rahu_start.strftime("%I:%M %p"), (rahu_start + part_duration).strftime("%I:%M %p")),
        "Gulika Kaal": (gulika_start.strftime("%I:%M %p"), (gulika_start + part_duration).strftime("%I:%M %p")),
        "Yamaganda": (yamaganda_start.strftime("%I:%M %p"), (yamaganda_start + part_duration).strftime("%I:%M %p"))
    }




    
def get_samvat_vikram(year: int):
    """Calculate Hindu eras"""
    cycle = [
        "Prabhava", "Vibhava", "Shukla", "Pramoda", "Prajapati", "Angiras",
        "Shrimukha", "Bhava", "Yuvan", "Dhatri", "Ishvara", "Bahudhanya",
        "Pramadi", "Vikrama", "Vishu", "Chitrabhanu", "Svabhanu", "Tarana",
        "Parthiva", "Vyaya", "Sarvajit", "Sarvadhari", "Virodhi", "Vikriti",
        "Khara", "Nandana", "Vijaya", "Jaya", "Manmatha", "Durmukhi",
        "Hevilambi", "Vilambi", "Vikari", "Sharvari", "Plava", "Shubhakrit",
        "Shobhana", "Krodhi", "Vishvavasu", "Parabhava", "Plavanga", "Keelaka",
        "Saumya", "Sadharana", "Virodhikrit", "Paridhavi", "Pramadi", "Ananda",
        "Rakshasa", "Nala", "Pingala", "Kalayukti", "Siddharthi", "Raudra",
        "Durmati", "Dundubhi", "Rudhirodgari", "Raktakshi", "Krodhana", "Kshaya"
    ]
    return (
        f"{year-78} - {cycle[(year+9) % 60]}",
        f"{year+57} - {cycle[(year+56) % 60]}"
    )

def generate_panchang(input_date: date, location: str) -> Panchang:
    """Main Panchang generation function"""
    try:
        # Get coordinates and timezone
        lat, lng = geocode_location(location)
        tz = get_timezone(lat, lng)
        
        # Calculate celestial times
        sunrise, sunset = get_sun_times(lat, lng, input_date, tz)
        moonrise, moonset = get_moon_times(lat, lng, input_date, tz)
        
        # Calculate day name in local timezone
        local_date = datetime(input_date.year, input_date.month, input_date.day, tzinfo=tz)
        day_name = local_date.strftime("%A")
        
        # Calculate astronomical positions
        sun_long, moon_long = get_sun_moon_longitudes(input_date)
        ayanamsa = calculate_ayanamsa(input_date)
        
        # Calculate Panchang elements
        tithi, paksha = calculate_tithi(sun_long, moon_long)
        yoga = calculate_yoga(sun_long, moon_long, ayanamsa)
        karana = calculate_karana(sun_long, moon_long)
        nakshatra = calculate_nakshatra(moon_long, sunrise)
        
        # Calculate time periods
        time_slots = get_kaal_timings(sunrise, sunset)
       
        
        # Hindu eras
        shaka, vikram = get_samvat_vikram(input_date.year)
        
        return Panchang(
            date=input_date,
            sunrise=sunrise.strftime("%I:%M:%S %p"),
            sunset=sunset.strftime("%I:%M:%S %p"),
            moonrise=moonrise.strftime("%I:%M:%S %p") if moonrise else "N/A",
            moonset=moonset.strftime("%I:%M:%S %p") if moonset else "N/A",
            tithi=tithi,
            nakshatra=nakshatra,
            yoga=yoga,
            karana=karana,
            paksha=paksha,
            day=day_name,
            dishashool={"Monday": "East", "Tuesday": "North", "Wednesday": "North",
                       "Thursday": "South", "Friday": "West", "Saturday": "East",
                       "Sunday": "West"}.get(day_name),
            shaka_samvat=shaka,
            vikram_samvat=vikram,
            timings=time_slots
        )
        
    except Exception as e:
        raise RuntimeError(f"Panchang calculation failed: {str(e)}")