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
    heater_lifetime = database['lifetime'][heizsystem]
    heater_embodied = heater_embodied_per_kw * nominal_heating_power/1000.0/heater_lifetime  # heating power comes in W

    #dhw heating is assumed to be included in the space heating capacity

    ## Cooler  TODO: IF COOLING POWER IS BIGGER THAN HEATING POWER IT IS NOT CALCULATED CORRECTLY
    if cooling_system == heizsystem:
        if nominal_cooling_power <= nominal_heating_power:
            cooler_embodied = 0.0
        else:
            cooler_embodied_per_kw = database['Value'][cooling_system] # this data is in kgCO2eq/kW
            cooler_lifetime = database['lifetime'][cooling_system]
            cooler_embodied = cooler_embodied_per_kw * nominal_cooling_power/1000.0/cooler_lifetime
            heater_embodied = 0


    else:
        cooler_embodied_per_kw = database['Value'][cooling_system]  # this data is in kgCO2eq/kW
        cooler_lifetime = database['lifetime'][cooling_system]
        cooler_embodied = cooler_embodied_per_kw * nominal_cooling_power/1000.0/cooler_lifetime  # cooling power comes in W


    ## Heat emission

    if (heat_distribution == 'air') and (heat_distribution == 'electric'):
        heat_emisison_embodied_per_kw = 0.0
        heat_emission_lifetime = 1.0  # to avoid division by 0
    else:
        heat_emission_embodied_per_kw = database['Value'][heat_emission_system]  # this data is in kgCO2eq/kW
        heat_emission_lifetime = database['lifetime'][heat_emission_system]

    heat_emission_embodied = heat_emission_embodied_per_kw * nominal_heating_power / 1000.0 / heat_emission_lifetime  # heating power comes in W

    ## Distribution

    if heat_distribution == "hydronic":
        if int(gebaeudekategorie) == 1:
            heat_distribution_embodied_per_area = database['Value']['hydronic heat distribution residential']
            heat_distribution_lifetime = database['lifetime']['hydronic heat distribution residential']
        elif int(gebaeudekategorie) == 2:
            heat_distribution_embodied_per_area = database['Value']['hydronic heat distribution office']
            heat_distribution_lifetime = database['lieftime']['hydronic heat distribution office']
        else:
            heat_distribution_embodied_per_area = 0.0
            heat_distribution_lifetime = 1.0  # this avoids division by zero if embodied = 0
            print("no embodied emissions for heat distribution")

    elif heat_distribution == 'electric':
        heat_distribution_embodied_per_area = 0.0
        heat_distribution_lifetime = 1.0  # to avoid division by zero

    else:
        heat_distribution_per_area = database['Value'][heat_distribution]  # this data is in kgCO2eq/kW
        heat_distribution_lifetime = database['lifetime'][heat_distribution]

    embodied_heat_distribution = heat_distribution_embodied_per_area * energy_reference_area / heat_distribution_lifetime




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
    pv_lifetime = database['lifetime'][pv_type]
    pv_embodied = pv_embodied_per_kw * pv_area * pv_efficiency / pv_lifetime  # at STC Irradiance = 1kW/m2

    embodied_electrical = pv_embodied

    return embodied_thermal + embodied_electrical #+ embodied_ventilation



def calculate_envelope_emissions(database_path, total_wall_area, wall_type, total_window_area,
                                 window_type, total_roof_area, roof_type, energy_reference_area, floor_type):

    database = pd.read_excel(database_path, index_col="Name")

    wall_embodied_per_area = database['GWP[kgCO2eq/m2]'][wall_type]
    wall_lifetime = database['lifetime'][wall_type]
    wall_embodied = total_wall_area * wall_embodied_per_area/wall_lifetime

    window_embodied_per_area = database['GWP[kgCO2eq/m2]'][window_type]
    window_lifetime = database['lifetime'][window_type]
    window_embodied = window_embodied_per_area * total_window_area/window_lifetime

    roof_embodied_per_area = database['GWP[kgCO2eq/m2]'][roof_type]
    roof_lifetime = database['lifetime'][roof_type]
    roof_embodied = roof_embodied_per_area * total_roof_area/roof_lifetime

    floor_embodied_per_area = database['GWP[kgCO2eq/m2'][floor_type]
    floor_lifetime = database['lifetime'][floor_type]
    floor_embodied = floor_embodied_per_area * energy_reference_area / floor_lifetime

    return wall_embodied + window_embodied + roof_embodied + floor_embodied
    # in total GHG emissions per year (kgCO2eq/a)






if __name__ == "__main__":

    systems_database_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\embodied_emissions_systems.xlsx"
    envelope_database_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\embodied_emissions_envelope.xlsx"

    gebaeudekategorie = 1
    era = 250.0  #m2
    heizsystem = "ASHP"
    heat_emission_system = "floor heating"
    normheizleistung = 8000 #W
    dhw_heizsystem = heizsystem
    heat_distribution = "hydronic"


    cooling_system = "ASHP"
    cooling_power = normheizleistung
    cold_emission_system = "floor heating"
    cooling_power = np.array([5000.0, 8000.0])  # W


    pv_area = 50.0  # m2
    pv_type = "m-Si"
    pv_efficiency = 0.18

    total_wall_area = 500.0  # m2
    wall_type = "Betonwand, Wärmedämmung mit Lattenrost, Verkleidung Steinwolle 0.25m insulation thickness"

    total_window_area = 100.0  # m2
    window_type = "Holzflügelfenster 3-fach ESG"

    total_roof_area = 200.0  # m2
    roof_type = "Betonwand, Wärmedämmung mit Lattenrost, Verkleidung Steinwolle 0.25m insulation thickness" # Hier ist für die Programmierphase eine Wand eingegeben.


    a = embodied_emissions_of_systems = calculate_system_related_embodied_emissions(systems_database_path, gebaeudekategorie, era,
                                                                     heizsystem, heat_emission_system, heat_distribution,
                                                                     normheizleistung,
                                                                     dhw_heizsystem, cooling_system, cold_emission_system,
                                                                     cooling_power,  pv_area, pv_type, pv_efficiency)


    b = embodied_emissions_of_envelope = calculate_envelope_emissions(envelope_database_path, total_wall_area, wall_type,
                                                                  total_window_area, window_type, total_roof_area, roof_type)

    print(a)
    print(b)