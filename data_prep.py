import numpy as np
import pandas as pd
import math
import datetime
import pvlib
import os
import sys
sys.path.insert(1, r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator")
import supply_system



def embodied_emissions_heat_generation_kbob_per_kW(system_type):
    """
    This function takes a heat generation system type and returns the respective embodied emissions per kW of installed
    power.
    --> this function is very basic and needs to be improved.
    :param system_type: string of gshp, ashp, electric heater
    :return: float, embodied kgCO2 equivalent per kW of installed power
    """

    ## Define embodied emissions: # In a later stage this could be included in the RC model "supply_system.py file"
    if system_type == "gshp":
        coeq = 272.5 #kg/kW [KBOB 2016]
    elif system_type == "ashp":
        coeq = 363.75 #kg/kW [KBOB 2016]

    elif system_type == "electric heater":
        coeq = 7.2/5.0  #kg/kW [ecoinvent auxiliary heating unit production, electric, 5kW]

    else:
        print("Embodied emissions for this system type are not defined")
        pass

    return coeq

def embodied_emissions_borehole_per_m():

    coeq_borehole = 28.1 #kg/m[KBOB 2016]
    return coeq_borehole

def embodied_emissions_heat_emission_system_per_m2(em_system_type):

    if em_system_type == "underfloor heating":
        coeq_underfloor_heating = 5.06 #kg/m2 [KBOB]

    return coeq_underfloor_heating

def embodied_emissions_pv_per_kW():
    coeq_pv = 2080 # kg/kWp [KBOB 2016]
    return coeq_pv

def sia_standardnutzungsdaten(category):


    if category == 'room_temperature_heating':
        return {1: 20., 2: 20., 3: 20., 4: 20., 5: 20., 6: 20, 7: 20, 8: 22, 9: 18, 10: 18, 11: 18,
                                 12: 28}  # 380-1 Tab7
    if category == 'room_temperature_cooling':
        return 26.0
        # Only a very limited number of subcases does not have 26 as the cooling temperature value.
            #{1: 26., 2: 26., 3: 26., 4: 26., 5: 26., 6: 26., 7: 26, 8: 26, ...}  # SIA 2024

    elif category == 'regelzuschaege':
        return {"Einzelraum": 0., "Referenzraum": 1., "andere": 2.}  # 380-1 Tab8

    elif category == 'area_per_person':
        return {1: 40., 2: 60., 3: 20., 4: 10., 5: 10., 6: 5, 7: 5., 8: 30., 9: 20., 10: 100., 11: 20.,
                       12: 20.}  # 380-1 Tab9
    elif category == 'gain_per_person':
        return {1: 70., 2: 70., 3: 80., 4: 70., 5: 90., 6: 100., 7: 80., 8: 80., 9: 100., 10: 100., 11: 100.,
                       12: 60.}  # 380-1 Tab10

    elif category == 'presence_time':
        return {1: 12., 2: 12., 3: 6., 4: 4., 5: 4., 6: 3., 7: 3., 8: 16., 9: 6., 10: 6., 11: 6.,
                     12: 4.}  # 380-1 Tab11

    elif category == 'gains_from_electrical_appliances':
    # this part of elektrizitatsbedarf only goes into thermal calculations. Electricity demand is calculated
    # independently.
        return {1: 28., 2: 22., 3: 22., 4: 11., 5: 33., 6: 33., 7: 17., 8: 28., 9: 17., 10: 6., 11: 6.,
                           12: 56.}  # 380-1 Tab12

    elif category == 'reduction_factor_for_electricity':
        return {1: 0.7, 2: 0.7, 3: 0.9, 4: 0.9, 5: 0.8, 6: 0.7, 7: 0.8, 8: 0.7, 9: 0.9, 10: 0.9, 11: 0.9,
                              12: 0.7}  # 380-1 Tab13

    elif category == 'effective_air_flow':
        return {1: 0.7, 2: 0.7, 3: 0.7, 4: 0.7, 5: 0.7, 6: 1.2, 7: 1.0, 8: 1.0, 9: 0.7, 10: 0.3, 11: 0.7,
                         12: 0.7}  # 380-1 Tab14
    # aussenluft_strome = {1: 2.1}  # UBA-Vergleichsstudie
    else:
        print('You are trying to look up data from SIA that are not implemented')


# def persons_from_area_sia(energy_reference_area, type=1):
#
#     if type ==1:
#         personenflache = 50.  # m2/p
#
#     elif type == 3:
#         personenflache = 14.
#
#     occupants = energy_reference_area / personenflache
#     return occupants

def electric_appliances_sia(energy_reference_area, type=1, value="standard"):
    """
    This function calculates the use of electric appliances according to SIA 2024
    :param energy_reference_area: float, m2, energy reference area of the room/building
    :param type: int, use type according to SIA2024
    :param value: str, reference value according to SIA choice of "standard", "ziel" and "bestand"
    :return: np.array of hourly electricity demand for appliances in Wh
    """
    if type==1:  # Typ 1 SIA Wohnen (1.1 MFH, 1.2 EFH)
        max_hourly = {"standard":8.0, "ziel": 4.0, "bestand":10.0}
        demand_profile = max_hourly[value] * np.repeat(
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.8, 0.2, 0.1, 0.1, 0.1, 0.1, 0.8, 0.2, 0.1, 0.1, 0.1, 0.2, 0.8, 1.0, 0.2,
             0.2, 0.2, 0.1], 365)
    elif type==3: #Typ 3 SIA Einzel-, Gruppenbüro
        max_hourly = {"standard": 7.0, "ziel": 3.0, "bestand": 15.0}
        demand_profile = max_hourly[value] * np.repeat(
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.6, 0.8, 1.0, 0.8, 0.4, 0.6, 1.0, 0.8, 0.6, 0.2, 0.1, 0.1, 0.1,
             0.1, 0.1, 0.1], 365)

    else:
        print("No demand schedule for electrical appliances has been defined for this case.")

    return demand_profile * energy_reference_area #Wh

def build_yearly_emission_factors(export_assumption="c"):

    choice = "TEF" + export_assumption
    emissions_df = pd.read_excel(r"C:\Users\walkerl\Documents\code\proof_of_concept\data\emission_factors_AC.xlsx",
                                 index="Time")
    emissions_df = emissions_df.set_index('Time')
    emissions_df.resample('Y').mean()
    #swiss
    hourly_emission_factor = np.repeat(emissions_df.resample('Y').mean()[choice].to_numpy(), 8760)/1000.0 #kgCO2eq/kWh

    return hourly_emission_factor

def build_yearly_emission_factors_sia():
    hourly_emission_factor = np.repeat(139, 8760) / 1000.0  # kgCO2eq/kWh SIA380
    return hourly_emission_factor

def build_yearly_emission_factors_eu():
    hourly_emission_factor = np.repeat(630, 8760) / 1000.0  # kgCO2eq/kWh www.co2-monitor.ch/de/information/glossar/
    return hourly_emission_factor

def build_monthly_emission_factors(export_assumption="c"):
    """
    This function creates simple monthly emission factors of the Swiss consumption mix based on the year 2015.
    It returns an hourly list of the monthly values. No input is needed. The list is generated here to omit hard coding
    values within the simulatin process.
    :return: np array of length 8760 with monthly emission factors on hourly resolution.
    """
    if export_assumption=="c":
        grid_emission_factor = {"jan": .1366, "feb": .1548, "mar": .1403, "apr": .1170, "may": .0578, "jun": .0716,
                                "jul": .0956, "aug": .1096, "sep": .1341, "oct": .1750, "nov": .1644, "dec": .1577}  # for TEFc (AC)

    elif export_assumption=="d":
        grid_emission_factor = {"jan": .1108, "feb": .1257, "mar": .1175, "apr": .0937, "may": .0400, "jun": .0463,
                                "jul": .0594, "aug": .0931, "sep": .1111, "oct": .1418, "nov": .1344, "dec": .1343}  # for TEFd (AC)

    else:
        "Choice of export assumption not valid"

    ## Factors above According to ST Alice Chevrier
    ## hours of the months:
    # jan:  0 - 743
    # feb:  744 - 1415
    # mar:  1440 - 2159
    # apr:  2160 - 2906
    # may:  2907 - 3623
    # jun:  3624 - 4343
    # jul:  4344 - 5087
    # aug:  5088 - 5831
    # sep:  5832 - 6551
    # oct:  6552 - 7295
    # nov:  7296 - 8015
    # dec:  8016 - 8759

    hourly_emission_factors = np.concatenate([
        np.repeat(grid_emission_factor["jan"], 744),
        np.repeat(grid_emission_factor["feb"], 672),
        np.repeat(grid_emission_factor["mar"], 744),
        np.repeat(grid_emission_factor["apr"], 720),
        np.repeat(grid_emission_factor["may"], 744),
        np.repeat(grid_emission_factor["jun"], 720),
        np.repeat(grid_emission_factor["jul"], 744),
        np.repeat(grid_emission_factor["aug"], 744),
        np.repeat(grid_emission_factor["sep"], 720),
        np.repeat(grid_emission_factor["oct"], 744),
        np.repeat(grid_emission_factor["nov"], 720),
        np.repeat(grid_emission_factor["dec"], 744)
    ])  # in g/kWh
    return hourly_emission_factors

def build_grid_emission_hourly(export_assumption="c"):
    emissions_df = pd.read_excel(r"C:\Users\walkerl\Documents\code\proof_of_concept\data\emission_factors_AC.xlsx")
    choice="TEF"+export_assumption
    hourly_emission_factors = emissions_df[choice].to_numpy()/1000.0
    return(hourly_emission_factors)

def fossil_emission_factors(system_type):
    """
     for now, wood and pellets are listed in these are also combustion based systems
     TODO: omit fossils and maybe only include pellets
    :param system_type:
    :return:
    """
    treibhausgaskoeffizient = {"Oil": 0.319, "Natural Gas": 0.249, "Wood": 0.020, "Pellets": 0.048}
    #kgCO2/kWh SIA380 2015 Anhang C Tab 5
    hourly_emission_factor = np.repeat(treibhausgaskoeffizient[system_type], 8760)  # kgCO2eq/kWh SIA380
    return hourly_emission_factor


def extract_wall_data(filepath, name="Betonwand, Wärmedämmung mit Lattenrost, Verkleidung", area=0,
                               type="GWP[kgCO2eq/m2]", ):
    """
    MAKE SURE TO HAVE THE RIGHT DIMENSIONS IN YOUR SOURCE FILE AND IN YOUR CALCULATION
    THIS FUNCTION HAS TO BE EXTENDED AND CONSOLIDATED
    :param filepath:
    :param name:
    :param area:
    :param type:
    :return:
    """
    data = pd.read_excel(filepath, header=0, index_col=1)
    if type == "U-value":
        return data[data["Bezeichnung"] == name][type][:1].values[0]

    elif area <=0:
        print("No wall area is specified for the calculation of the wall's embodied impact")
        return 0

    else:
        return(data[data["Bezeichnung"] == name][type][:1].values[0]*area)
        ## The zero is here for the moment becaues each element is included with 0.18 and 0.25m insulation.
        ## This way always the 0.18 version is chosen.


def extract_decarbonization_factor(grid_decarbonization_path, grid_decarbonization_until, grid_decarbonization_type,
                                   from_year, to_year):

    decarb_factors = pd.read_excel(grid_decarbonization_path, sheet_name=str(grid_decarbonization_until),
                                   header=[6,7], index_col=0)[grid_decarbonization_type]['Factor'].loc[from_year:to_year]

    return decarb_factors.to_numpy()

### This shows how to use the function:
# grid_decarbonization_until = 2050  # Choose from 2050, 2060 and 2080
# grid_decarbonization_type = 'linear'  # Choose from 'linear', exponential, quadratic, constant
# grid_decarbonization_path = r'C:\Users\walkerl\Documents\code\proof_of_concept\data\future_decarbonization\Decarbonization sceanrios.xlsx'
# from_year = 2019
# to_year = 2080
#
# extract_decarbonization_factor(grid_decarbonization_until, grid_decarbonization_type, from_year, to_year)


def translate_system_sia_to_rc(system):
    """
    These can be adapted if needed. At the moment all the combustion based systems are chosen to be new oil Boilers.
    This makes sense for the energy calculations. For the emission calculations the respective emission factors are
    chosen as "fossil emission factors" making it add up in the end.
    :param system:
    :return:
    """
    system_dictionary = {'Oil':supply_system.OilBoilerNew, 'Natural Gas':supply_system.OilBoilerNew ,
                         'Wood':supply_system.OilBoilerMed , 'Pellets':supply_system.OilBoilerNew,
                         'GSHP':supply_system.HeatPumpWater, 'ASHP':supply_system.HeatPumpAir,
                         'electric':supply_system.ElectricHeating}
    return system_dictionary[system]

def hourly_to_monthly(hourly_array):
    """
    This function sums up hourly values to monthly values
    :param hourly_array:
    :return:
    """
    hours_per_month = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])*24
    monthly_values = np.empty(12)
    start_hour = 0

    for month in range(12):
        end_hour = start_hour+hours_per_month[month]
        monthly_values[month] = hourly_array[start_hour:end_hour].sum()
        start_hour = start_hour + hours_per_month[month]
    return monthly_values

def hourly_to_monthly_average(hourly_array):
    """
    This function sums up hourly values to monthly values
    :param hourly_array:
    :return:
    """
    hours_per_month = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])*24
    monthly_values = np.empty(12)
    start_hour = 0

    for month in range(12):
        end_hour = start_hour+hours_per_month[month]
        monthly_values[month] = hourly_array[start_hour:end_hour].mean()
        start_hour = start_hour + hours_per_month[month]
    return monthly_values

def sia_electricity_per_erf_hourly(occupancy_path, gebaeudekategorie_sia):
        """
        This function distributes the electricity demand of SIA380-1 according tooccupancy schedules of SIA2024
        It is questionable if this is correct but probably a good first approximation.
        :param occupancy_path: the same occupancy path used for the RC model according to SIA 2024 where monthly and
        weekly schedules are combined.
        :return:
        """

        # Diese Angaben werden ebenfalls in runSIA380 verwendet und sollten früher oder später nach data_prep oder
        # in ein file verschoben werden.
        elektrizitatsbedarf = {1: 28., 2: 22., 3: 22., 4: 11., 5: 33., 6: 33., 7: 17., 8: 28., 9: 17., 10: 6., 11: 6.,
                               12: 56.}  # 380-1 Tab12

        occupancyProfile = pd.read_csv(occupancy_path)
        occupancy_factor = np.empty(8760)
        total = occupancyProfile['People'].sum()
        for hour in range(8760):
            occupancy_factor[hour] = occupancyProfile.loc[hour, 'People']/total

        return occupancy_factor * elektrizitatsbedarf[int(gebaeudekategorie_sia)]

def sia_annaul_dhw_demand(gebaeudekategorie_sia):

    ### Datenbanken: Werte von SIA 380 2015
    annual_dhw_demand = {1.1: 19.8, 1.2: 13.5, 2.1: 39.5, 2.2: 0., 3.1: 3.6, 3.2: 3.6, 3.3: 0.0, 3.4: 0.0, 4.1: 5.3,
                         4.2: 0.0,
                         4.3: 0.0, 4.4: 7.9, 5.1: 2.7, 5.2: 2.7, 5.3: 1.5, 6.1: 108.9, 7.1: 7.3, 7.2: 7.3,
                         8.1: 67.7,
                         8.2: 0.0, 8.3: 0.0, 9.1: 2.4, 9.2: 2.4, 9.3: 2.4, 10.1: 0.9, 11.1: 52.9, 11.2: 87.1,
                         12: None}

    return annual_dhw_demand[gebaeudekategorie_sia]

def epw_to_sia_irrad(epw_path):
    """
    THIS FUNCTION DOES NOT WORK PROPERLY WHEN COMPARED TO METEONORM SIA DATA.
    ESPECIALLY THE DIFFUSE MODEL SHOULD BE CHANGED TO PEREZ
    :param epw_path:
    :return: dictionary for SIA compatible irradiation data. Dicitonary filled with numpy arrays of floats. Output in
    MJ as in SIA 2028.
    """
    # Set EPW Labels and import epw file
    epw_labels = ['year', 'month', 'day', 'hour', 'minute', 'datasource', 'drybulb_C', 'dewpoint_C', 'relhum_percent',
                  'atmos_Pa', 'exthorrad_Whm2', 'extdirrad_Whm2', 'horirsky_Whm2', 'glohorrad_Whm2',
                  'dirnorrad_Whm2', 'difhorrad_Whm2', 'glohorillum_lux', 'dirnorillum_lux', 'difhorillum_lux',
                  'zenlum_lux', 'winddir_deg', 'windspd_ms', 'totskycvr_tenths', 'opaqskycvr_tenths', 'visibility_km',
                  'ceiling_hgt_m', 'presweathobs', 'presweathcodes', 'precip_wtr_mm', 'aerosol_opt_thousandths',
                  'snowdepth_cm', 'days_last_snow', 'Albedo', 'liq_precip_depth_mm', 'liq_precip_rate_Hour']

    # Import EPW file
    header_data = pd.read_csv(epw_path, header=None, nrows=1)
    latitude = header_data.iloc[0,6]
    longitude = header_data.iloc[0,7]
    weather_data = pd.read_csv(epw_path, skiprows=8, header=None, names=epw_labels).drop('datasource', axis=1)

    global_horizontal_hourly = weather_data['glohorrad_Whm2'].to_numpy()
    global_south_vertical = np.empty(8760)
    global_east_vertical = np.empty(8760)
    global_west_vertical = np.empty(8760)
    global_north_vertical = np.empty(8760)
    temperature = np.empty(8760)

    for hour in range(8760):
        solar_altitude, solar_azimuth = calc_sun_position(latitude, longitude, 2020, hour)
        normal_direct_radiation = weather_data['dirnorrad_Whm2'][hour]
        horizontal_diffuse_radiation = weather_data['difhorrad_Whm2'][hour]
        global_horizontal_value = weather_data['glohorrad_Whm2'][hour]
        dni_extra = weather_data['extdirrad_Whm2'][hour]
        relative_air_mass = pvlib.atmosphere.get_relative_airmass(90-solar_altitude)
        temperature[hour] = weather_data['drybulb_C'][hour]


        # South (azimuth south convention)

        # I use the get_total_irradiance_function of pvlib module. Beware that this function has different
        # angle conventions than the RC Window Model. Therfore a 180-solar azimuth is required.

        global_south_vertical[hour] = pvlib.irradiance.get_total_irradiance(90, 180, 90-solar_altitude,
                                                                            180-solar_azimuth, normal_direct_radiation,
                                                                            global_horizontal_value,
                                                                            horizontal_diffuse_radiation,
                                                                            dni_extra=dni_extra,
                                                                            model='perez',
                                                                            airmass=relative_air_mass)['poa_global']


        global_east_vertical[hour] = pvlib.irradiance.get_total_irradiance(90, 90, 90-solar_altitude,
                                                                           180-solar_azimuth, normal_direct_radiation,
                                                                           global_horizontal_value,
                                                                           horizontal_diffuse_radiation,
                                                                           dni_extra=dni_extra,
                                                                           model='perez',
                                                                           airmass=relative_air_mass)['poa_global']

        global_west_vertical[hour] = pvlib.irradiance.get_total_irradiance(90, 270, 90-solar_altitude,
                                                                           180-solar_azimuth, normal_direct_radiation,
                                                                           global_horizontal_value,
                                                                           horizontal_diffuse_radiation,
                                                                           dni_extra=dni_extra,
                                                                           model='perez',
                                                                           airmass=relative_air_mass)['poa_global']

        global_north_vertical[hour] = pvlib.irradiance.get_total_irradiance(90, 0, 90-solar_altitude,
                                                                            180-solar_azimuth, normal_direct_radiation,
                                                                            global_horizontal_value,
                                                                            horizontal_diffuse_radiation,
                                                                            dni_extra=dni_extra,
                                                                            model='perez',
                                                                            airmass=relative_air_mass)['poa_global']



    global_south_vertical = np.nan_to_num(global_south_vertical, 0.0)
    global_east_vertical = np.nan_to_num(global_east_vertical, 0.0)
    global_west_vertical = np.nan_to_num(global_west_vertical, 0.0)
    global_north_vertical = np.nan_to_num(global_north_vertical, 0.0)
    mj_to_wh_factor = 1000.0 / 3.6

    global_horizontal = hourly_to_monthly(global_horizontal_hourly)/mj_to_wh_factor
    global_south_vertical = hourly_to_monthly(global_south_vertical)/mj_to_wh_factor
    global_east_vertical = hourly_to_monthly(global_east_vertical)/mj_to_wh_factor
    global_west_vertical = hourly_to_monthly(global_west_vertical)/mj_to_wh_factor
    global_north_vertical = hourly_to_monthly(global_north_vertical)/mj_to_wh_factor
    temperature = hourly_to_monthly_average(temperature)

    # The values are returned in MJ as this unit is used by SIA (see SIA2028 2010)
    return {'global_horizontal': global_horizontal, 'global_south':global_south_vertical,
            'global_east':global_east_vertical, 'global_west':global_west_vertical,
            'global_north':global_north_vertical, 'temperature':temperature}


def calc_sun_position(latitude_deg, longitude_deg, year, hoy):
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

def read_location_from_epw(epw_path):
    epw_data = pvlib.iotools.read_epw(epw_path, coerce_year=None)
    longitude = epw_data[1]['longitude']
    latitude = epw_data[1]['latitude']
    return longitude, latitude

def string_orientation_to_angle_RC(string_orientation):
    """
    This function follows the convention of the RC model. 0 is south
    :param string_orientation:
    :return:
    """
    translation = {"N":180., 'NE':135., 'E':90., 'SE':45.0, 'S':0., 'SW':-45.0, 'W':-90, 'NW':-135.0}
    return translation[string_orientation]