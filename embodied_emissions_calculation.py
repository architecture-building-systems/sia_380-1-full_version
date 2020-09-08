import pandas as pd
import numpy as np


def calculate_system_related_embodied_emissions(ee_database_path, gebaeudekategorie, energy_reference_area,
                                                heizsystem, heat_emission_system,
                                                heat_distribution, nominal_heating_power, dhw_heizsystem,
                                                cooling_system, cold_emission_system, nominal_cooling_power,
                                                pv_area, pv_type, pv_efficiency):
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


    ## Heat distribution

    if (heat_distribution != 'air') and (heat_distribution != 'electric'):

        heat_emission_embodied_per_kw = database['Value'][heat_emission_system]  # this data is in kgCO2eq/kW
        heat_emission_embodied = heat_emission_embodied_per_kw * nominal_heating_power / 1000.0  # heating power comes in W

        if int(gebaeudekategorie) == 1:
            heat_distribution_embodied_per_era = database['Value']['hydronic heat distribution residential']
        elif int(gebaeudekategorie) == 2:
            heat_distribution_embodied_per_era = database['Value']['hydronic heat distribution office']
        else:
            heat_distribution_embodied_per_era = 0.0
            print("no embodied emissions for heat distribution")
    else:
        heat_distribution_embodied_per_era = 0.0
        heat_emission_embodied = 0.0
        print("no embodied emissions for heat distribution")

    embodied_heat_distribution = heat_distribution_embodied_per_era * energy_reference_area

    ## Cold distribution and emission TODO: IF COOLING POWER IS BIGGER THAN HEATING POWER IT IS NOT CALCULATED CORRECTLY
    if heat_emission_system == cold_emission_system:
        cold_emission_embodied = 0.0
    else:
        cold_emission_embodied_per_kw = database['Value'][heat_emission_system]  # this data is in kgCO2eq/kW
        cold_emission_embodied = cold_emission_embodied_per_kw * nominal_heating_power / 1000.0  # cooling power comes in W

    embodied_thermal = heater_embodied + cooler_embodied + embodied_heat_distribution + heat_emission_embodied +\
                                                                cold_emission_embodied



    # Calculation of embodied emissions for ventilation system

    # if has_mechanical_ventilation == True:
    #     ventilation_embodied_per_era = database['Value']['mechanical ventilation'] * aussenluftvolumenstrom
    #     embodied_ventilation = ventilation_embodied_per_era * energy_reference_area
    # else:
    #     embodied_ventilation = 0.0


    # Calculation of embodied emissions for the electrical systems



    ## PV System
    pv_embodied_per_kw = database['Value'][pv_type]  # this data is in kgCO2eq/kWp
    pv_embodied = pv_embodied_per_kw * pv_area * pv_efficiency  # at STC Irradiance = 1kW/m2


    ## electricity distribution
    # for now empty. here I could decide AC/DC

    embodied_electrical = pv_embodied_per_kw

    return embodied_thermal  + embodied_electrical #+ embodied_ventilation
    # Calculation of embodied emissions for building envelope



def calculate_envelope_emissions(database_path, total_wall_area, wall_type, total_window_area,
                                 window_type, total_roof_area, roof_type):

    database = pd.read_excel(database_path, index_col="Name")

    wall_embodied_per_area = database['GWP[kgCO2eq/m2]'][wall_type]
    wall_embodied = total_wall_area * wall_embodied_per_area

    window_embodied_per_area = database['GWP[kgCO2eq/m2]'][window_type]
    window_embodied = window_embodied_per_area * total_window_area

    roof_embodied_per_area = database['GWP[kgCO2eq/m2]'][roof_type]
    roof_embodied = roof_embodied_per_area * total_roof_area

    return wall_embodied + window_embodied + roof_embodied   # in total GHG emissions (kgCO2eq)






if __name__ == "__main__":

    systems_database_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\embodied_emissions_systems.xlsx"
    envelope_database_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\embodied_emissions_envelope.xlsx"

    gebaeudekategorie = 1
    era = 250.0  #m2
    heizsystem = "ASHP"
    heat_emission_system = "floor heating"
    normheizleistung = 8000.0 #W
    dhw_heizsystem = heizsystem
    heat_distribution = "air"


    cooling_system = "ASHP"
    cooling_power = normheizleistung
    cold_emission_system = "floor heating"
    cooling_power = 8000.0  # W


    pv_area = 20.0  # m2
    pv_type = "m-Si"
    pv_efficiency = 0.18

    total_wall_area = 60.0  # m2
    wall_type = "Betonwand, Wärmedämmung mit Lattenrost, Verkleidung Steinwolle 0.25m insulation thickness"

    total_window_area = 15.0  # m2
    window_type = "Holzflügelfenster 3-fach ESG"

    total_roof_area = 20.0  # m2
    roof_type = "Betonwand, Wärmedämmung mit Lattenrost, Verkleidung Steinwolle 0.25m insulation thickness" # Hier ist für die Programmierphase eine Wand eingegeben.


    embodied_emissions_of_systems = calculate_system_related_embodied_emissions(systems_database_path, gebaeudekategorie, era,
                                                                     heizsystem, heat_emission_system, heat_distribution,
                                                                     normheizleistung,
                                                                     dhw_heizsystem, cooling_system, cold_emission_system,
                                                                     cooling_power,  pv_area, pv_type, pv_efficiency)


    embodied_emissions_of_envelope = calculate_envelope_emissions(envelope_database_path, total_wall_area, wall_type,
                                                                  total_window_area, window_type, total_roof_area, roof_type)
