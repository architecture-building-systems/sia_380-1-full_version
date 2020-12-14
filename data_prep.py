import numpy as np
import pandas as pd
import math
import datetime
import pvlib
import os
import sys
sys.path.insert(1, r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator")
import supply_system
import emission_system
import time

def sia_standardnutzungsdaten(category):
    """
    :param
    category: string that specifies which SIA standardnutzungsdaten should be returned
    :return: dictionary of specified parameter for all building categories
    """

    if category == 'room_temperature_heating':
        return {1: 20., 2: 20., 3: 20., 4: 20., 5: 20., 6: 20, 7: 20, 8: 22, 9: 18, 10: 18, 11: 18,
                                 12: 28}  # 380-1 Tab7

    # This is currently not used to have a flexible cooling setpoint
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

    else:
        print('You are trying to look up data from SIA that are not implemented')

def electric_appliances_sia(energy_reference_area, type=1, value="standard"):
    """
    This function calculates the use of electric appliances according to SIA 2024
    :param energy_reference_area: float, m2, energy reference area of the room/building
    :param type: int, use type according to SIA2024 (Gebaudekategorie)
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


def build_yearly_emission_factors(source, type="annual", export_assumption="c"):
    """
    :param source: string, currently the choices are SIA, eu and KBOB. empa_ac should not yet be used
    :param type: string, only necessary for empa_ac
    :param export_assumption: string, only necessary for empa_ac
    :return: numpy array of length 8760 with the dimension kgCO2eq/kWh
    """

    if source =="SIA": #TODO: compare with values from KBOB
        #SIA has a constant factor, the type therefore does not matter
        hourly_emission_factor = np.repeat(139, 8760) / 1000.0  # kgCO2eq/kWh SIA380

    elif source == "KBOB":
        # KBOB has a constant factor, the type therefore does not matter
        hourly_emission_factor = np.repeat(102, 8760) / 1000.0  # kgCO2eq/kWh KBOB: 2009/1:2016 Verbrauchermix-CH
    elif source == "eu":
        # here a constant factor of the european power mix is assumed, the type therefore does not matter
        hourly_emission_factor = np.repeat(630, 8760) / 1000.0  # kgCO2eq/kWh www.co2-monitor.ch/de/information/glossar/
        #ENTSO - E - Mix: 5480000 (UBP), 524 (GWP)

    elif source == "empa_ac":


        choice = "TEF" + export_assumption
        emissions_df = pd.read_excel(r"C:\Users\walkerl\Documents\code\proof_of_concept\data\emission_factors_AC.xlsx",
                                 index="Time")
        emissions_df = emissions_df.set_index('Time')

        if type == "annual":
            hourly_emission_factor = np.repeat(emissions_df.resample('Y').mean()[choice].to_numpy(),
                                           8760) / 1000.0  # kgCO2eq/kWh
        if type=="monthly":
            hourly_emission_factor = np.repeat(emissions_df.resample('M').mean()[choice].to_numpy(),
                                           8760) / 1000.0  # kgCO2eq/kWh
        if type=="hourly":
            hourly_emission_factor = emissions_df[choice].to_numpy() / 1000.0

    else:
        quit("Emission factors for electricity could not be built. Simulation stopped")


    return hourly_emission_factor

def build_yearly_emission_factors_UBP(source_UBP, type="annual", export_assumption="c"):
    """
    :param source_UBP: string, currently the choice is only KBOB
    :return: numpy array of length 8760 with the dimension kgCO2eq/kWh
    """

    if source_UBP =="KBOB":
        #KBOB has a constant factor, the type therefore does not matter
        hourly_emission_factor_UBP = np.repeat(347000, 8760) / 1000.0  # UBP/kWh KBOB: 2009/1:2016 Verbrauchermix-CH

    elif source == "empa_ac":


        choice = "TEF" + export_assumption
        emissions_df = pd.read_excel(r"C:\Users\walkerl\Documents\code\proof_of_concept\data\emission_factors_AC.xlsx",
                                 index="Time")
        emissions_df = emissions_df.set_index('Time')

        if type == "annual":
            hourly_emission_factor_UBP = np.repeat(emissions_df.resample('Y').mean()[choice].to_numpy(),
                                           8760) / 1000.0  # UBP/kWh
        if type=="monthly":
            hourly_emission_factor_UBP = np.repeat(emissions_df.resample('M').mean()[choice].to_numpy(),
                                           8760) / 1000.0  # UBP/kWh
        if type=="hourly":
            hourly_emission_factor_UBP = emissions_df[choice].to_numpy() / 1000.0

    else:
        quit("Emission factors for electricity could not be built. Simulation stopped")

    return hourly_emission_factor_UBP


def build_grid_emission_hourly(export_assumption="c"):
    """
    DO NOT USE THIS YET
    :param export_assumption:
    :return:
    """
    emissions_df = pd.read_excel(r"C:\Users\walkerl\Documents\code\proof_of_concept\data\emission_factors_AC.xlsx")
    choice="TEF"+export_assumption
    hourly_emission_factors = emissions_df[choice].to_numpy()/1000.0
    return(hourly_emission_factors)

def fossil_emission_factors(system_type):
    """
     for now, wood and pellets are listed in these are also combustion based systems
    :param system_type: string that describes the combustion based heating system
    :return: np array for 8760 hours of the year with emission factor for delivered energy according to SIA in
    kgCO2eq/kWh. The factors are, however constant over the year.
    """
    treibhausgaskoeffizient = {"Oil": 0.319, "Natural Gas": 0.249, "Wood": 0.020, "Pellets": 0.048, "district":0.089}
    #kgCO2/kWh SIA380 2015 Anhang C Tab 5 (Update to KBOB 2016: Oil: 0.322, Wood: 0.045, Pellets: 0.038)
    hourly_emission_factor = np.repeat(treibhausgaskoeffizient[system_type], 8760)  # kgCO2eq/kWh SIA380
    return hourly_emission_factor

def fossil_emission_factors_UBP(system_type):
    """
     for now, wood and pellets are listed in these are also combustion based systems
    :param system_type: string that describes the combustion based heating system
    :return: np array for 8760 hours of the year with emission factor for delivered energy according to SIA in
    kgCO2eq/kWh. The factors are, however constant over the year.
    """
    UBPkoeffizient = {"Oil": 251., "Natural Gas": 151., "Wood": 152., "Pellets": 108., "district":75.5} #UBP/kWh KBOB: 2009/1:2016
    hourly_emission_factor_UBP = np.repeat(UBPkoeffizient[system_type], 8760)
    return hourly_emission_factor_UBP


def extract_wall_data(filepath, name="Betonwand, Wärmedämmung mit Lattenrost, Verkleidung", area=0,
                               type="GWP[kgCO2eq/m2]", ):
    """
    THIS FUNCTION WAS WRITTEN TO GET DATA FROM BAUTEILKATALOG... THE WEBSITE IS OFFLINE
    TODO: Remove function or finish it if Bauteilkatalog shows up again.
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


def translate_system_sia_to_rc(system):
    """
    These can be adapted if needed. At the moment all the combustion based systems are chosen to be new oil Boilers.
    This makes sense for the energy calculations. For the emission calculations the respective emission factors are
    chosen as "fossil emission factors" making it add up in the end.
    TODO: Maybe there is a better way to do this? However it works fine for now.
    :param system: string with heating or cooling system
    :return: rc supply system object
    """
    system_dictionary = {'Oil':supply_system.OilBoilerNew, 'Natural Gas':supply_system.OilBoilerNew ,
                         'Wood':supply_system.OilBoilerMed , 'Pellets':supply_system.OilBoilerNew,
                         'GSHP':supply_system.HeatPumpWater, 'ASHP':supply_system.HeatPumpAir,
                         'electric':supply_system.ElectricHeating, 'district':supply_system.OilBoilerNew,
                         'None':supply_system.DirectHeater}
    return system_dictionary[system]

def translate_heat_emission_system(system):
    """
    Attention: supply temperatures are hardcoded in the RC simulator and need to agree with the ones chosen for
    monthly calculations.
    The system None has to be defined as not None for RC because the supply temperature flows into the heat demand
    calculation. TODO: Check if this could be solved differently.
    :param system: string with the heat emissions system
    :return: rc emission system object
    """
    system_dictionary = {'air':emission_system.AirConditioning, 'radiator':emission_system.NewRadiators,
                         'floor heating':emission_system.FloorHeating, 'ceiling heating':emission_system.FloorHeating,
                         'None':emission_system.AirConditioning}

    return system_dictionary[system]

def lookup_supply_temperatures_according_to_rc(system):
    """
    Todo: Figure out how to deal with 'None'
    :param system: string with the heat or cold emssion system
    :return: tuple with (heating supply temperature, cooling supply temperature)
    """
    system_dictionary = {'air':(40., 6.), 'radiator':(50., 12.), 'floor heating':(40., 12.), 'ceiling heating':(40., 12.),
                         'None':(40., 6.), 'electric':(50, None)} # The system 'air' is used for None

    return system_dictionary[system]

def calculate_monthly_ashp_cop(heat_supply_temp, cold_supply_temp, weather_data_sia, heat_pump_efficiency=0.55):

    outside_temperature = weather_data_sia['temperature']
    heating_delta_temp = heat_supply_temp-outside_temperature
    heating_delta_temp[heating_delta_temp < 15.0] = 15.0
    monthly_heating_cop = heat_pump_efficiency * (heat_supply_temp + 273.15) / heating_delta_temp
    cooling_delta_temp = outside_temperature - cold_supply_temp
    cooling_delta_temp[cooling_delta_temp < 15.0] = 15.0
    monthly_cooling_cop = heat_pump_efficiency * (cold_supply_temp+273.15)/cooling_delta_temp

    return monthly_heating_cop, monthly_cooling_cop

def calculate_monthly_gshp_cop(heat_supply_temp, cold_supply_temp, ground_temperature=10, heat_pump_efficiency=0.55):
    outside_temperature = ground_temperature
    heating_delta_temp = max(15, heat_supply_temp-outside_temperature)

    monthly_heating_cop = heat_pump_efficiency * (heat_supply_temp + 273.15) / heating_delta_temp


    cooling_delta_temp = max(15, outside_temperature - cold_supply_temp)
    monthly_cooling_cop = heat_pump_efficiency * (cold_supply_temp+273.15)/cooling_delta_temp

    return monthly_heating_cop, monthly_cooling_cop

def hourly_to_monthly(hourly_array):
    """
    This function sums up hourly values to monthly values.
    :param hourly_array: hourly np.array with 8760 entries
    :return: monthly array with 12 entries that sum up the respective hour¨ly values.
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
    This function averages hourly values to monthly values
    :param hourly_array: hourly np.array with 8760 entries
    :return: monthly array with 12 entries that show the average of the hourly values.
    """
    hours_per_month = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])*24
    monthly_values = np.empty(12)
    start_hour = 0

    for month in range(12):
        end_hour = start_hour+hours_per_month[month]
        monthly_values[month] = hourly_array[start_hour:end_hour].mean()
        start_hour = start_hour + hours_per_month[month]
    return monthly_values

def sia_electricity_per_erf_hourly(occupancy_path, gebaeudekategorie_sia, has_mechanical_ventilation):
        """
        This function distributes the electricity demand of SIA380-1 according to occupancy schedules of SIA2024
        It is questionable if this is correct but probably a good first approximation.
        :param occupancy_path: the same occupancy path used for the RC model according to SIA 2024 where monthly and
        weekly schedules are combined.
        :return:
        """

        # Diese Angaben werden ebenfalls in runSIA380 verwendet und sollten früher oder später nach data_prep oder
        # in ein file verschoben werden.
        elektrizitatsbedarf = {1: 28., 2: 22., 3: 22., 4: 11., 5: 33., 6: 33., 7: 17., 8: 28., 9: 17., 10: 6., 11: 6.,
                               12: 56.}  # 380-1 Tab12

        if has_mechanical_ventilation:
            # SIA2024 - 2015 in kWh/m2a
            ventilation_electricity = {1.1: 0.8, 1.2: 0.5, 2.1: 2.8, 2.2: 6.6, 3.1: 1.4, 3.2: 2.0}
        else:
            ventilation_electricity = {1.1: 0., 1.2: 0., 2.1: 0., 2.2: 0., 3.1: 0., 3.2: 0.}

        occupancyProfile = pd.read_csv(occupancy_path)
        occupancy_factor = np.empty(8760)
        total = occupancyProfile['People'].sum()
        for hour in range(8760):
            occupancy_factor[hour] = occupancyProfile.loc[hour, 'People']/total

        return occupancy_factor * (elektrizitatsbedarf[int(gebaeudekategorie_sia)] + ventilation_electricity[gebaeudekategorie_sia])

def sia_annaul_dhw_demand(gebaeudekategorie_sia):
    """
    TODO: Move this function into the SIA standard values function
    :param gebaeudekategorie_sia:
    :return:
    """

    ### Datenbanken: Werte von SIA 380 2015
    annual_dhw_demand = {1.1: 19.8, 1.2: 13.5, 2.1: 39.5, 2.2: 0., 3.1: 3.6, 3.2: 3.6, 3.3: 0.0, 3.4: 0.0, 4.1: 5.3,
                         4.2: 0.0,
                         4.3: 0.0, 4.4: 7.9, 5.1: 2.7, 5.2: 2.7, 5.3: 1.5, 6.1: 108.9, 7.1: 7.3, 7.2: 7.3,
                         8.1: 67.7,
                         8.2: 0.0, 8.3: 0.0, 9.1: 2.4, 9.2: 2.4, 9.3: 2.4, 10.1: 0.9, 11.1: 52.9, 11.2: 87.1,
                         12: None}

    return annual_dhw_demand[gebaeudekategorie_sia]

def epw_to_sia_irrad(epw_path, model="isotropic"):
    """
    THIS FUNCTION DOES NOT WORK PROPERLY WHEN COMPARED TO METEONORM SIA DATA.
    ESPECIALLY THE DIFFUSE MODEL SHOULD BE CHANGED TO PEREZ
    :param epw_path: string of filepath
    :param model: Choice of sky model used for transformation. "isotropic" will work with all epw files perez sky
                    can produce errors.
    :return: dictionary for SIA compatible irradiation data. Dicitonary filled with numpy arrays of floats. Output in
    MJ as in SIA 2028.
    """
    start = time.time()

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

    solar_zenith_deg, solar_azimuth_deg = calc_sun_position(latitude, longitude)

    normal_direct_radiation = weather_data['dirnorrad_Whm2']
    horizontal_diffuse_radiation = weather_data['difhorrad_Whm2']
    global_horizontal_value = weather_data['glohorrad_Whm2']
    dni_extra = weather_data['extdirrad_Whm2']
    relative_air_mass = pvlib.atmosphere.get_relative_airmass(zenith=solar_zenith_deg)
    temperature = weather_data['drybulb_C']



    global_south_vertical = pvlib.irradiance.get_total_irradiance(90, 180, solar_zenith_deg,
                                                                        solar_azimuth_deg, normal_direct_radiation,
                                                                        global_horizontal_value,
                                                                        horizontal_diffuse_radiation,
                                                                        dni_extra=dni_extra,
                                                                        model=model,
                                                                        airmass=relative_air_mass)['poa_global'].to_numpy()


    global_east_vertical = pvlib.irradiance.get_total_irradiance(90, 90, solar_zenith_deg,
                                                                       solar_azimuth_deg, normal_direct_radiation,
                                                                       global_horizontal_value,
                                                                       horizontal_diffuse_radiation,
                                                                       dni_extra=dni_extra,
                                                                       model=model,
                                                                       airmass=relative_air_mass)['poa_global'].to_numpy()

    global_west_vertical = pvlib.irradiance.get_total_irradiance(90, 270, solar_zenith_deg,
                                                                       solar_azimuth_deg, normal_direct_radiation,
                                                                       global_horizontal_value,
                                                                       horizontal_diffuse_radiation,
                                                                       dni_extra=dni_extra,
                                                                       model=model,
                                                                       airmass=relative_air_mass)['poa_global'].to_numpy()

    global_north_vertical = pvlib.irradiance.get_total_irradiance(90, 0, solar_zenith_deg,
                                                                        solar_azimuth_deg, normal_direct_radiation,
                                                                        global_horizontal_value,
                                                                        horizontal_diffuse_radiation,
                                                                        dni_extra=dni_extra,
                                                                        model=model,
                                                                        airmass=relative_air_mass)['poa_global'].to_numpy()


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



def calc_sun_position(latitude_deg, longitude_deg):
    """
    Calculate the sun position for a certain place on earth.
    :param latitude_deg: float, location latitude in degrees
    :param longitude_deg: float, location longitude in degrees
    :return: tuple of two numpy arrays with the solar position for every hour of the year in deg according to the
            convention that north is 0/360° for azimuth
    """

    # Set the date in UTC based off the hour of year and the year itself
    start_of_year = datetime.datetime(2019, 1, 1, 0, 0, 0, 0)
    end_of_year = datetime.datetime(2019, 12, 31, 23, 0, 0, 0)
    utc_datetime = pd.date_range(start_of_year, end_of_year, periods=8760)

    day_of_year = utc_datetime.dayofyear

    ## declination in radians
    declination = pvlib.solarposition.declination_cooper69(day_of_year) #in radians!!

    lstm = 15 * round(longitude_deg/15, 0)

    # Normalise the day to 2*pi
    # There is some reason as to why it is 364 and not 365.26
    angle_of_day = (day_of_year - 81) * (2 * np.pi / 364)

    # The deviation between local standard time and true solar time
    equation_of_time = (9.87 * np.sin(2 * angle_of_day)) - \
        (7.53 * np.cos(angle_of_day)) - (1.5 * np.sin(angle_of_day))

    # True Solar Time
    solar_time = ((utc_datetime.hour * 60) + utc_datetime.minute +
                  (4 * (longitude_deg - lstm)) + equation_of_time) / 60.0

    # Angle between the local longitude and longitude where the sun is at
    # higher altitude
    hour_angle_deg = (15 * (12 - solar_time))

    start = time.time()
    ## zenith in radians!!
    zenith_rad = pvlib.solarposition.solar_zenith_analytical(latitude=np.radians(latitude_deg),
                                                          hourangle=np.radians(hour_angle_deg),
                                                          declination=declination).to_numpy()

    azimuth_rad = pvlib.solarposition.solar_azimuth_analytical(latitude=np.radians(latitude_deg),
                                                               hourangle=np.radians(hour_angle_deg),
                                                               declination=declination,
                                                               zenith=zenith_rad).to_numpy()

    zenith_deg = np.degrees(zenith_rad)
    azimuth_deg = np.degrees(azimuth_rad)

    return zenith_deg, azimuth_deg


def calc_sun_position_II(latitude_deg, longitude_deg, year, hoy):
    """
    TODO: I don't think this function is still in use. Check it and remove if possible.
    :param latitude_deg:
    :param longitude_deg:
    :param year:
    :param hoy:
    :return:
    """

    # Set the date in UTC based off the hour of year and the year itself
    start_of_year = datetime.datetime(year, 1, 1, 0, 0, 0, 0)
    utc_datetime = start_of_year + datetime.timedelta(hours=hoy)
    day_of_year = int(hoy/24)+1

    ## declination in radians
    declination = pvlib.solarposition.declination_cooper69(day_of_year) #in radians!!

    lstm = 15 * round(longitude_deg/15, 0)

    # Normalise the day to 2*pi
    # There is some reason as to why it is 364 and not 365.26
    angle_of_day = (day_of_year - 81) * (2 * math.pi / 364)

    # The deviation between local standard time and true solar time
    equation_of_time = (9.87 * math.sin(2 * angle_of_day)) - \
        (7.53 * math.cos(angle_of_day)) - (1.5 * math.sin(angle_of_day))

    # True Solar Time
    solar_time = ((utc_datetime.hour * 60) + utc_datetime.minute +
                  (4 * (longitude_deg - lstm)) + equation_of_time) / 60.0

    # Angle between the local longitude and longitude where the sun is at
    # higher altitude
    hour_angle_deg = (15 * (12 - solar_time))

    ## zenith in radians!!
    zenith_rad = pvlib.solarposition.solar_zenith_analytical(latitude=math.radians(latitude_deg),
                                                          hourangle=math.radians(hour_angle_deg),
                                                          declination=declination)

    azimuth_rad = pvlib.solarposition.solar_azimuth_analytical(latitude=math.radians(latitude_deg),
                                                               hourangle=math.radians(hour_angle_deg),
                                                               declination=declination,
                                                               zenith=zenith_rad)

    zenith_deg = math.degrees(zenith_rad)
    azimuth_deg = math.degrees(azimuth_rad)

    return zenith_deg, azimuth_deg


def read_location_from_epw(epw_path):
    """
    This function reads the longitude and latitude from an epw file. This is used so that the actual location of a
    building is not needed as an extra input.
    :param epw_path: string of epw path
    :return: tuple of longitude and latitude in degreees
    """
    epw_data = pvlib.iotools.read_epw(epw_path, coerce_year=None)
    longitude = epw_data[1]['longitude']
    latitude = epw_data[1]['latitude']
    return longitude, latitude

def string_orientation_to_angle(string_orientation):
    """
    This function follows the good convention. N=0°, S = 180°, E = 90°. It can be used to translate the string
    inputs used in SIA to degrees used in RC or other parts of the code
    :param string_orientation:
    :return:float, degrees
    """
    translation = {"N":0., 'NE':45., 'E':90., 'SE':135.0, 'S':180., 'SW':225.0, 'W':270, 'NW':315.0}
    return translation[string_orientation]

def photovoltaic_yield_hourly(pv_azimuth, pv_tilt, stc_efficiency, performance_ratio, pv_area,
                              epw_path, model="isotropic"):
    """
    :param pv_azimuth: angle or array of angles with north convention (N=0/360)
    :param pv_tilt: tilt or arrays of tilt of the pv array 0deg = horizontal
    :param stc_efficiency: pv module efficiency from data sheet (stc = standard test conditions)
    :param performance_ratio: a fixed percentage that describes the quality of the system
    :param pv_area: area in m2
    :param epw_path: string with filepath to the respective weatherfile of the location
    :param model: string of sky model: can for example be "isotropic", "perez" This influences the diffuse radiation.
    :return: np.array with hourly yield values in [Wh] !make sure to use Wh as the output.
    """
    epw_labels = ['year', 'month', 'day', 'hour', 'minute', 'datasource', 'drybulb_C', 'dewpoint_C', 'relhum_percent',
                  'atmos_Pa', 'exthorrad_Whm2', 'extdirrad_Whm2', 'horirsky_Whm2', 'glohorrad_Whm2',
                  'dirnorrad_Whm2', 'difhorrad_Whm2', 'glohorillum_lux', 'dirnorillum_lux', 'difhorillum_lux',
                  'zenlum_lux', 'winddir_deg', 'windspd_ms', 'totskycvr_tenths', 'opaqskycvr_tenths', 'visibility_km',
                  'ceiling_hgt_m', 'presweathobs', 'presweathcodes', 'precip_wtr_mm', 'aerosol_opt_thousandths',
                  'snowdepth_cm', 'days_last_snow', 'Albedo', 'liq_precip_depth_mm', 'liq_precip_rate_Hour']

    # Import EPW file
    header_data = pd.read_csv(epw_path, header=None, nrows=1)
    latitude = header_data.iloc[0, 6]
    longitude = header_data.iloc[0, 7]
    weather_data = pd.read_csv(epw_path, skiprows=8, header=None, names=epw_labels).drop('datasource', axis=1)

    solar_zenith_deg, solar_azimuth_deg = calc_sun_position(latitude, longitude)

    normal_direct_radiation = weather_data['dirnorrad_Whm2']
    horizontal_diffuse_radiation = weather_data['difhorrad_Whm2']
    global_horizontal_value = weather_data['glohorrad_Whm2']
    dni_extra = weather_data['extdirrad_Whm2']
    relative_air_mass = pvlib.atmosphere.get_relative_airmass(zenith=solar_zenith_deg)

    irrad = pvlib.irradiance.get_total_irradiance(pv_tilt, pv_azimuth, solar_zenith_deg,
                                                      solar_azimuth_deg, normal_direct_radiation,
                                                      global_horizontal_value,
                                                      horizontal_diffuse_radiation,
                                                      dni_extra=dni_extra,
                                                      model=model,
                                                      airmass=relative_air_mass)['poa_global']

    hourly_yield = irrad * pv_area * stc_efficiency * performance_ratio  # in Wh


    return hourly_yield.to_numpy()


def estimate_self_consumption(electricity_demand, pv_peak_power, building_category):
    """
    Source: https://pvspeicher.htw-berlin.de/wp-content/uploads/2015/05/HTW-Berlin-Solarspeicherstudie.pdf BILD 16
    These plots were analyzed and translated into the formula used below with a logarithmic assumption
    This function should not be used in all geographic locations(!) Use for Swiss or German context
    UPDATE: A new curve has been made for residential and office buildings that match the SIA but have been
            exponentially fitted from an own model creation.
    :param electricity_demand: monthly value in Wh
    :param pv_prod_month: monthly value in Wh
    :param pv_peak_power: one value in kW
    :return: monthly self consumption values in %
    """
    if pv_peak_power == 0:
        monthly_sc = np.repeat(100.0,12)

    elif int(building_category) == 1:
        monthly_stoc = (pv_peak_power / 12) / (electricity_demand / 1000)
        monthly_sc = (0.12 + 0.92 * np.exp(-1.64*monthly_stoc))*100.0

    elif int(building_category) == 3:
        monthly_stoc = (pv_peak_power / 12) / (electricity_demand / 1000)
        monthly_sc = (0.15 + 0.70 * np.exp(-0.81*monthly_stoc))*100.0

        ## updated self-consumption formula for office
        # monthly_sc = (0.17 + 0.68 * np.exp(-0.79 * monthly_stoc)) * 100.0


    else:

        # Factor 1/12 because source is calculated on annual basis
        monthly_stoc = (pv_peak_power / 12) / (electricity_demand / 1000)
        monthly_sc = (0.17 + 0.68 * np.exp(-0.79 * monthly_stoc))*100.0
        print("No self consumption model available for this building category. Office model is chosen.")
        # This maximises self consumption at 95% and the pure calculation could go above 100% (!)
    monthly_sc[monthly_sc >=95] = 95.0
    monthly_sc[monthly_sc <= 5] = 5.0


    return monthly_sc


def calculate_self_consumption(hourly_demand, hourly_production):
    """
    This function simply calculates the self consumption based on simulation results for demand and solar production.
    :param hourly_demand: np.array of hourly values
    :param hourly_production: np.array of hourly values
    :return: float, annual value.
    """

    if hourly_production.sum() == 0:
        self_consumption_ratio = 0
    else:
        self_consumption = np.empty(len(hourly_demand))
        for hour in range(len(hourly_demand)):
            self_consumption[hour] = min(hourly_production[hour], hourly_demand[hour])
        self_consumption_ratio = self_consumption.sum()/hourly_production.sum()
    return self_consumption_ratio



#### Robustness part
def maximin(performance_matrix, minimizing=False):

    if minimizing==False:
        min_vector = performance_matrix.min(axis=1)
        maximin = min_vector.max()
        maximin_scenario = min_vector.idxmax()

        return(maximin_scenario, maximin)

    elif minimizing==True:
        max_vector = performance_matrix.max(axis=1)
        minimax = max_vector.min()
        maximin_scenario = max_vector.idxmin()

        return (maximin_scenario, minimax)


def maximax(performance_matrix, minimizing=False):
    if minimizing == False:
        max_vector = performance_matrix.max(axis=1)
        maximax = max_vector.max()
        maximax_scenario = max_vector.idxmax()

        return (maximax_scenario, maximax)

    elif minimizing==True:
        min_vector = performance_matrix.min(axis=1)
        minimin = min_vector.min()
        maximin_scenario = min_vector.idxmin()

        return (maximin_scenario, minimin)



def hurwicz(performance_matrix, coefficient_of_pessimism, minimizing=False):

    if minimizing==False:
        max_vector = performance_matrix.max(axis=1)
        min_vector = performance_matrix.min(axis=1)
        hurwicz_vector = coefficient_of_pessimism * min_vector + (1.0-coefficient_of_pessimism)*max_vector
        hurwicz = hurwicz_vector.max()
        hurwicz_scenario = hurwicz_vector.idxmax()


    elif minimizing==True:
        max_vector = performance_matrix.min(axis=1)
        min_vector = performance_matrix.max(axis=1)
        hurwicz_vector = coefficient_of_pessimism * min_vector + (1.0-coefficient_of_pessimism)*max_vector
        hurwicz = hurwicz_vector.min()
        hurwicz_scenario = hurwicz_vector.idxmin()

    return (hurwicz_scenario, hurwicz)

def laplace_insufficient_reasoning(performance_matrix, minimizing=False):
    laplace_vector = performance_matrix.mean(axis=1)
    if minimizing==False:
        laplace = laplace_vector.max()
        laplace_scenario = laplace_vector.idxmax()

    elif minimizing==True:
        laplace = laplace_vector.min()
        laplace_scenario = laplace_vector.idxmin()

    return (laplace_scenario, laplace)

def minimax_regret(performance_matrix, minimizing=False):

    if minimizing==False:
        column_maxes = performance_matrix.max()
        regret_matrix = -(performance_matrix-column_maxes)
        max_regret_vector = regret_matrix.max(axis=1)
        if max_regret_vector.lt(0.0).any():
            print("negative regrets were simulated, check if you formulated your problem correctly")

        minimax_regret = max_regret_vector.min()
        minimax_regret_scenario = max_regret_vector.idxmin()


    if minimizing==True:
        column_mins = performance_matrix.min()
        regret_matrix = performance_matrix-column_mins
        max_regret_vector = regret_matrix.max(axis=1)
        if max_regret_vector.lt(0.0).any():
            print("negative regrets were simulated, check if you formulated your problem correctly")

        minimax_regret = max_regret_vector.min()
        minimax_regret_scenario = max_regret_vector.idxmin()


    return(minimax_regret_scenario, minimax_regret)

def percentile_based_skewness(performance_matrix, minimizing=False):
    q_ten = performance_matrix.quantile(0.1, axis=1)  # Ten percent percentile
    q_fifty = performance_matrix.quantile(0.5, axis=1)  # Median
    q_ninety = performance_matrix.quantile(0.9, axis=1)  # 90 percent percentile

    skew_vector = ((q_ninety+q_ten)/2 - q_fifty)/((q_ninety-q_ten)/2)
    if minimizing==False:
        max_skew = skew_vector.max()
        max_skew_position = skew_vector.idxmax()

        return(max_skew_position, max_skew)

    elif minimizing==True:
        min_skew = skew_vector.min()
        min_skew_position = skew_vector.idxmin()
        return (min_skew_position, min_skew)



def starrs_domain_criterion(performance_matrix, threshold, minimizing=False):

    if minimizing==False:
        pass_fail_matrix = (performance_matrix >= threshold)*1

    elif minimizing==True:
        pass_fail_matrix = (performance_matrix <= threshold) * 1

    score_vector = pass_fail_matrix.mean(axis=1)
    starr = score_vector.max()
    starr_scenario = np.argwhere(score_vector.to_numpy()==starr).flatten().tolist()
    if len(starr_scenario)==1:
        starr_scenario = starr_scenario[0]
    return(starr_scenario, starr)




