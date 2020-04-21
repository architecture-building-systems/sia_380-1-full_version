
"""
Tool to Evaluate Radiation incident on a surface of a set angle. This is an adapted version of the script used
in @Jayathissa's RC simulator solar gain calculations.

"""

import pandas as pd
import math
import datetime
import pvlib


__authors__ = ["Linus Walker, Prageeth Jayathissa"]
__copyright__ = "Copyright 2016, Architecture and Building Systems - ETH Zurich"
__credits__ = ["pysolar, Quaschning Volker,  Rolf Hanitsch"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Linus Walker"
__email__ = "walker@arch.ethz.ch"
__status__ = "production"



class Location(object):
    """Set the Location of the Simulation with an Energy Plus Weather File"""

    def __init__(self, epwfile_path):

        # Set EPW Labels and import epw file
        epw_labels = ['year', 'month', 'day', 'hour', 'minute', 'datasource', 'drybulb_C', 'dewpoint_C', 'relhum_percent',
                      'atmos_Pa', 'exthorrad_Whm2', 'extdirrad_Whm2', 'horirsky_Whm2', 'glohorrad_Whm2',
                      'dirnorrad_Whm2', 'difhorrad_Whm2', 'glohorillum_lux', 'dirnorillum_lux', 'difhorillum_lux',
                      'zenlum_lux', 'winddir_deg', 'windspd_ms', 'totskycvr_tenths', 'opaqskycvr_tenths', 'visibility_km',
                      'ceiling_hgt_m', 'presweathobs', 'presweathcodes', 'precip_wtr_mm', 'aerosol_opt_thousandths',
                      'snowdepth_cm', 'days_last_snow', 'Albedo', 'liq_precip_depth_mm', 'liq_precip_rate_Hour']

        # Import EPW file
        self.weather_data = pd.read_csv(
            epwfile_path, skiprows=8, header=None, names=epw_labels).drop('datasource', axis=1)


    def calc_sun_position(self, latitude_deg, longitude_deg, year, hoy):
        """
        Calculates the Sun Position for a specific hour and location

        :param latitude_deg: Geographical Latitude in Degrees
        :type latitude_deg: float
        :param longitude_deg: Geographical Longitude in Degrees
        :type longitude_deg: float
        :param year: year
        :type year: int
        :param hoy: Hour of the year from the start. The first hour of January is 1
        :type hoy: int
        :return: altitude, azimuth: Sun position in altitude and azimuth degrees [degrees]
        :rtype: tuple
        """

        # Convert to Radians
        latitude_rad = math.radians(latitude_deg)
        longitude_rad = math.radians(longitude_deg)

        # Set the date in UTC based off the hour of year and the year itself
        start_of_year = datetime.datetime(year, 1, 1, 0, 0, 0, 0)
        utc_datetime = start_of_year + datetime.timedelta(hours=hoy)

        # Angular distance of the sun north or south of the earths equator
        # Determine the day of the year.
        day_of_year = utc_datetime.timetuple().tm_yday

        # Calculate the declination angle: The variation due to the earths tilt
        # http://www.pveducation.org/pvcdrom/properties-of-sunlight/declination-angle
        declination_rad = math.radians(
            23.45 * math.sin((2 * math.pi / 365.0) * (day_of_year - 81)))

        # Normalise the day to 2*pi
        # There is some reason as to why it is 364 and not 365.26
        angle_of_day = (day_of_year - 81) * (2 * math.pi / 364)

        # The deviation between local standard time and true solar time
        equation_of_time = (9.87 * math.sin(2 * angle_of_day)) - \
            (7.53 * math.cos(angle_of_day)) - (1.5 * math.sin(angle_of_day))

        # True Solar Time
        solar_time = ((utc_datetime.hour * 60) + utc_datetime.minute +
                      (4 * longitude_deg) + equation_of_time) / 60.0

        # Angle between the local longitude and longitude where the sun is at
        # higher altitude
        hour_angle_rad = math.radians(15 * (12 - solar_time))

        # Altitude Position of the Sun in Radians
        altitude_rad = math.asin(math.cos(latitude_rad) * math.cos(declination_rad) * math.cos(hour_angle_rad) +
                                 math.sin(latitude_rad) * math.sin(declination_rad))

        # Azimuth Position fo the sun in radians
        azimuth_rad = math.asin(
            math.cos(declination_rad) * math.sin(hour_angle_rad) / math.cos(altitude_rad))

        # I don't really know what this code does, it has been imported from
        # PySolar
        if(math.cos(hour_angle_rad) >= (math.tan(declination_rad) / math.tan(latitude_rad))):
            return math.degrees(altitude_rad), math.degrees(azimuth_rad)
        else:
            return math.degrees(altitude_rad), (180 - math.degrees(azimuth_rad))




class PhotovoltaicSurface(object):
    """docstring for Window"""

    def __init__(self, azimuth_tilt, altitude_tilt=90, stc_efficiency=0.16,
                 performance_ratio=0.8, area=1):

        self.altitude_tilt_rad = math.radians(altitude_tilt)
        self.azimuth_tilt_rad = math.radians(azimuth_tilt)
        self.efficiency = stc_efficiency
        self.performance_ratio = performance_ratio
        self.area = area


    def pv_simulation(self, Loc):



    def calc_solar_yield(self, sun_altitude, sun_azimuth, normal_direct_radiation, horizontal_diffuse_radiation,
                         global_horizontal_radiation, extraterestrial_direct_radiation):
        """
        Calculates the Solar yield of a defined PV area.

        :param sun_altitude: Altitude Angle of the Sun in Degrees
        :type sun_altitude: float
        :param sun_azimuth: Azimuth angle of the sun in degrees
        :type sun_azimuth: float
        :param normal_direct_radiation: Normal Direct Radiation from weather file
        :type normal_direct_radiation: float
        :param horizontal_diffuse_radiation: Horizontal Diffuse Radiation from weather file
        :type horizontal_diffuse_radiation: float
        :return: self.incident_solar, Incident Solar Radiation on window
        :return: self.solar_gains - Solar gains in building after transmitting through the window
        :rtype: float
        """


        relative_air_mass = pvlib.atmosphere.get_relative_airmass(90 - sun_altitude)
        solar_incident = pvlib.irradiance.get_total_irradiance(self.altitude_tilt, 180 - self.azimuth_tilt,
                                                               90 - sun_altitude,
                                                               180 - sun_azimuth, normal_direct_radiation,
                                                               global_horizontal_radiation,
                                                               horizontal_diffuse_radiation,
                                                               dni_extra=extraterestrial_direct_radiation,
                                                               model='perez',
                                                               airmass=relative_air_mass)['poa_global']


        self.solar_yield = self.incident_solar * self.efficiency * self.performance_ratio



if __name__ == '__main__':
    pass
