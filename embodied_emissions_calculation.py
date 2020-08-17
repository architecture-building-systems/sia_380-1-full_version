import pandas as pd
import numpy as np


def calculate_system_related_embodied_emissions(ee_database_path, heizsystem, nominal_heating_power, dhw_heizsystem,
                                                cooling_system,, cold_emission_system, nominal_cooling_power,
                                                heat_emission_system, pv_area, pv_type, total_wall_area, wall_type,
                                                total_window_area, window_type):
    """
    :param ee_database_path: string filepath
    :param heizsystem: string
    :param nominal_heating_power: float in W for nominal heat power
    :param dhw_heizsystem:
    :param cooling_system:
    :param heat_emission_system:
    :param pv_area:
    :param pv_type:
    :param total_wall_area:
    :param wall_type:
    :param total_window_area:
    :param window_type:
    :return: embodied emissions of energy systems, so far without ventilation.
    """

    database = pd.read_excel(ee_database_path, index_col="Name")

    # Calculation of embodied emissions for the thermal systems

    ## Heater
    heater_embodied_per_kw = database['Value'][heizsystem]  # this data is in kgCO2eq/kW
    heater_embodied = heater_embodied_per_kw * nominal_heating_power /1000.0  # heating power comes in W

    #dhw heating is assumed to be included in the space heating capacity

    ## Cooler  TODO: IF COOLING POWER IS BIGGER THAN HEATING POWER IT IS NOT CALCULATED CORRECTLY
    if cooling_system == heizsystem:
        cooler_embodied = 0.0
    else:
        cooler_embodied_per_kw = database['Value'][cooling_system]  # this data is in kgCO2eq/kW
        cooler_embodied = cooler_embodied_per_kw * nominal_cooling_power /1000.0 # cooling power comes in W


    ## Heat distribution and emission
    heat_emission_embodied_per_kw = database['Value'][heat_emission_system] #this data is in kgCO2eq/kW
    heat_emission_embodied = heat_emission_embodied_per_kw * normheizleistung /1000.0 # heating power comes in W

    ## Cold distribution and emission TODO: IF COOLING POWER IS BIGGER THAN HEATING POWER IT IS NOT CALCULATED CORRECTLY
    if heat_emission_system == cold_emission_system:
        cold_emission_embodied = 0
    else:
        cold_emission_embodied_per_kw = database['Value'][heat_emission_system]  # this data is in kgCO2eq/kW
        cold_emission_embodied = cold_emission_embodied_per_kw * normheizleistung / 1000.0  # cooling power comes in W

    embodied_thermal = heater_embodied + cooler_embodied + heat_emission_embodied + cold_emission_embodied


    # Calculation of embodied emissions for ventilation system

    #TODO: do ventilation


    # Calculation of embodied emissions for the electrical systems

    ## PV System
    pv_embodied_per_kw = database['Value'][pv_type]  # this data is in kgCO2eq/kWp
    pv_embodied = pv_embodied_per_kw * pv_area * pv_efficiency  # at STC Irradiance = 1kW/m2


    ## electricity distribution
    # for now empty. here I could decide AC/DC

    embodied_electrical = pv_embodied_per_kw

    return embodied_thermal + embodied_electrical
    # Calculation of embodied emissions for building envelope


    ## walls

    ## windows

    ## roof








database_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\embodied_emissions.xlsx"
heizsystem = "ASHP"
normheizleistung = 8000 #W
dhw_heizsystem = heizsystem

cooling_system = "ASHP"
cooling_power = normheizleistung

heat_emission_system = "floor heating"

pv_area = 20.0  # m2
pv_type = "m-Si"

total_wall_area = 60.0  # m2
wall_type = "standard"

total_window_area = 15.0  # m2
window_type = "standard"


embodied_emissions = calculate_system_related_embodied_emissions(database_path, heizsystem, normheizleistung,
                                                                 dhw_heizsystem, cooling_system, cooling_power,
                                                                 heat_emission_system, pv_area, pv_type,
                                                                 total_wall_area, wall_type, total_window_area,
                                                                 window_type)

print(embodied_emissions)