import pandas as pd
import numpy as np


def calculate_system_related_embodied_emissions(ee_database_path, gebaeudekategorie, energy_reference_area,
                                                heizsystem, heat_emission_system,
                                                heat_distribution, nominal_heating_power, dhw_heizsystem,
                                                cooling_system, cold_emission_system, nominal_cooling_power,
                                                pv_area, pv_type, pv_efficiency, has_mechanical_ventilation,
                                                max_aussenluft_volumenstrom):
    """
    This function is used to calculate the annualized embodied emissions of the considered building systems. A database
    file is called that includes impact and lifetime values. Further the system sizing has to be known for some power
    based components. Other components are sized directly from the energy reference area.
    Currently included: heat/cold production, heat/cold distribution, heat/cold emission
    TODO: possibly add electrical systems plus ventilation
    :param ee_database_path: string, database path where the system's impact and lifetimes are stored (xlsx file)
    :param gebaeudekategorie: float/int of SIA building category
    :param energy_reference_area: float
    :param heizsystem: string of the heating system type
    :param heat_emission_system: string of heat emission system
    :param heat_distribution: string of heat distribution system
    :param nominal_heating_power: float [W] heating sizing. MAKE SURE TO USE CORRECT DIMENSION
    :param dhw_heizsystem: string dhw heating system (currently not used, assumed to be the heating system)
    :param cooling_system: string of cooling system
    :param cold_emission_system: string of cold emission system
    :param nominal_cooling_power: [W] float cooling sizing. MAKE SURE TO USE CORRECT DIMENSION
    :param pv_area: m2 float/int
    :param pv_type: string of pv type as in database
    :param pv_efficiency: stc efficiency is required for m2 to kWp transformation
    :return: embodied emissions for building systems
    """

    database = pd.read_excel(ee_database_path, index_col="Name")

    # Calculation of embodied emissions for the thermal systems

    ## Heater
    heater_embodied_per_kw = database['Value'][heizsystem]  # this data is in kgCO2eq/kW
    heater_lifetime = database['lifetime'][heizsystem]
    heater_embodied = heater_embodied_per_kw * nominal_heating_power/1000.0/heater_lifetime  # heating power comes in W
    heater_embodied_per_kw_UBP = database['Value_UBP'][heizsystem] # this data is in UBP/kW
    heater_embodied_UBP = heater_embodied_per_kw_UBP * nominal_heating_power/1000.0/heater_lifetime # heating power comes in W


    #dhw heating is assumed to be included in the space heating capacity

    ## Cooler  TODO: IF COOLING POWER IS BIGGER THAN HEATING POWER IT IS NOT CALCULATED CORRECTLY
    if cooling_system == heizsystem:
        if nominal_cooling_power <= nominal_heating_power:
            cooler_embodied = 0.0
            cooler_embodied_UBP = 0.0
        else:
            cooler_embodied_per_kw = database['Value'][cooling_system] # this data is in kgCO2eq/kW
            cooler_lifetime = database['lifetime'][cooling_system]
            cooler_embodied = cooler_embodied_per_kw * nominal_cooling_power/1000.0/cooler_lifetime # cooling power comes in W
            heater_embodied = 0
            cooler_embodied_per_kw_UBP = database['Value_UBP'][cooling_system]  # this data is in UBP
            cooler_embodied_UBP = cooler_embodied_per_kw_UBP * nominal_cooling_power / 1000.0 / cooler_lifetime
            heater_embodied_UBP = 0

    else:
        cooler_embodied_per_kw = database['Value'][cooling_system]  # this data is in kgCO2eq/kW
        cooler_lifetime = database['lifetime'][cooling_system]
        cooler_embodied = cooler_embodied_per_kw * nominal_cooling_power/1000.0/cooler_lifetime  # cooling power comes in W
        cooler_embodied_per_kw_UBP = database['Value_UBP'][cooling_system]  # this data is in UBP/kW
        cooler_embodied_UBP = cooler_embodied_per_kw_UBP * nominal_cooling_power / 1000.0 / cooler_lifetime # cooling power comes in W


    ## Heat emission

    if heat_emission_system == 'air':
        # In that case 0.0 is assigned to heat emission system because it is already considered in
        # mechanical ventilation
        heat_emission_embodied_per_kw = 0.0
        heat_emission_embodied_per_kw_UBP = 0.0
        heat_emission_lifetime = 1.0  # to avoid division by 0
        if has_mechanical_ventilation == False:
            print("you chose heat distribution by air but do not have mechanical ventilation")
            quit()

    else:
        heat_emission_embodied_per_kw = database['Value'][heat_emission_system]  # this data is in kgCO2eq/kW
        heat_emission_lifetime = database['lifetime'][heat_emission_system]
        heat_emission_embodied_per_kw_UBP = database['Value_UBP'][heat_emission_system]  # this data is in UBP/kW

    heat_emission_embodied = heat_emission_embodied_per_kw * nominal_heating_power / 1000.0 / heat_emission_lifetime  # heating power comes in W
    heat_emission_embodied_UBP = heat_emission_embodied_per_kw_UBP * nominal_heating_power / 1000.0 / heat_emission_lifetime  # heating power comes in W


    ## Distribution

    if heat_distribution == "hydronic":
        if int(gebaeudekategorie) == 1:
            heat_distribution_embodied_per_area = database['Value']['hydronic heat distribution residential']
            heat_distribution_embodied_per_area_UBP = database['Value_UBP']['hydronic heat distribution residential']
            heat_distribution_lifetime = database['lifetime']['hydronic heat distribution residential']
        elif int(gebaeudekategorie) == 3:
            heat_distribution_embodied_per_area = database['Value']['hydronic heat distribution office']

            heat_distribution_embodied_per_area_UBP = database['Value_UBP']['hydronic heat distribution office']
            heat_distribution_lifetime = database['lifetime']['hydronic heat distribution office']

        else:
            heat_distribution_embodied_per_area = 0.0
            heat_distribution_embodied_per_area_UBP = 0.0
            heat_distribution_lifetime = 1.0  # this avoids division by zero if embodied = 0
            print("no embodied emissions for heat distribution")

    elif heat_distribution == 'electric':
        heat_distribution_embodied_per_area = 0.0
        heat_distribution_embodied_per_area_UBP = 0.0
        heat_distribution_lifetime = 1.0  # to avoid division by zero

    elif heat_distribution == 'air':
        #Todo: I am not sure if that makes sense or if it would be included in mechanidcal ventilation
        heat_distribution_embodied_per_area = database['Value'][heat_distribution]  # this data is in kgCO2eq/kW
        heat_distribution_embodied_per_area_UBP = database['Value_UBP'][heat_distribution]  # this data is in UBP/kW
        heat_distribution_lifetime = database['lifetime'][heat_distribution]
    else:
        print('You did not specify a correct heat distribution system')

    embodied_heat_distribution = heat_distribution_embodied_per_area * energy_reference_area / heat_distribution_lifetime
    embodied_heat_distribution_UBP = heat_distribution_embodied_per_area_UBP * energy_reference_area / heat_distribution_lifetime




    ## Cold distribution and emission TODO: IF COOLING POWER IS BIGGER THAN HEATING POWER IT IS NOT CALCULATED CORRECTLY
    if heat_emission_system == cold_emission_system:

        cold_emission_embodied = 0.0
        cold_emission_embodied_UBP = 0.0


    else:
        cold_emission_embodied_per_kw = database['Value'][heat_emission_system]  # this data is in kgCO2eq/kW
        cold_emission_embodied_per_kw_UBP = database['Value_UBP'][heat_emission_system]  # this data is in UBP/kW
        cold_emission_embodied = cold_emission_embodied_per_kw * nominal_cooling_power / 1000.0  # cooling power comes in W
        cold_emission_embodied_UBP = cold_emission_embodied_per_kw_UBP * nominal_cooling_power / 1000.0  # cooling power comes in W


    embodied_thermal = heater_embodied + cooler_embodied + embodied_heat_distribution + heat_emission_embodied +\
                                                                cold_emission_embodied
    embodied_thermal_UBP = heater_embodied_UBP + cooler_embodied_UBP + embodied_heat_distribution_UBP +\
                           heat_emission_embodied_UBP + cold_emission_embodied_UBP



    # Calculation of embodied emissions for ventilation system

    if has_mechanical_ventilation == True:
         ventilation_embodied_per_era = database['Value']['mechanical ventilation'] * max_aussenluft_volumenstrom
         ventilation_lifetime = database['lifetime']['mechanical ventilation']
         embodied_ventilation = ventilation_embodied_per_era * energy_reference_area / ventilation_lifetime

         ventilation_embodied_per_era_ubp = database['Value_UBP']['mechanical ventilation'] * max_aussenluft_volumenstrom
         embodied_ventilation_ubp = ventilation_embodied_per_era * energy_reference_area / ventilation_lifetime
    else:
        embodied_ventilation = 0.0
        embodied_ventilation_ubp = 0.0


    # Calculation of embodied emissions for the electrical systems



    ## PV System
    pv_embodied_per_kw = database['Value'][pv_type]  # this data is in kgCO2eq/kWp
    pv_embodied_per_kw_UBP = database['Value_UBP'][pv_type]  # this data is in UBP/kWp
    pv_lifetime = database['lifetime'][pv_type]
    pv_embodied = pv_embodied_per_kw * pv_area * pv_efficiency / pv_lifetime  # at STC Irradiance = 1kW/m2
    pv_embodied_UBP = pv_embodied_per_kw_UBP * pv_area * pv_efficiency / pv_lifetime  # at STC Irradiance = 1kW/m2

    embodied_electrical = pv_embodied
    embodied_electrical_UBP = pv_embodied_UBP

    embodied_thermal_electrical_vent = embodied_thermal + embodied_electrical + embodied_ventilation
    embodied_thermal_electrical_vent_UBP = embodied_thermal_UBP + embodied_electrical_UBP + embodied_ventilation_ubp

    return embodied_thermal_electrical_vent, embodied_thermal_electrical_vent_UBP



def calculate_envelope_emissions(database_path, total_wall_area, wall_type, total_window_area,
                                 window_type, total_roof_area, roof_type, energy_reference_area, ceiling_type):
    """
    This function calculate the embodied emissions of the building envelope based on the input database and the given
    geometrical values (Ausmass). The database includes values per respective dimension and lifetime.
    :param database_path: string, filepath to envelope database
    :param total_wall_area: float, m2
    :param wall_type: string, wall type that can be found in database
    :param total_window_area: float, m2
    :param window_type: string, window type that can be found in database
    :param total_roof_area: float, m2
    :param roof_type: string, roof type that can be found in database
    :param energy_reference_area: m2 energy reference area
    :param ceiling_type: string, ceiling type for intermediate floors
    :return:
    """

    database = pd.read_excel(database_path, index_col="Name")

    wall_embodied_per_area = database['GWP[kgCO2eq/m2]'][wall_type]
    wall_embodied_per_area_UBP = database['UBP[/m2]'][wall_type]
    wall_lifetime = database['lifetime'][wall_type]
    wall_embodied = total_wall_area * wall_embodied_per_area/wall_lifetime
    wall_embodied_UBP = total_wall_area * wall_embodied_per_area_UBP/wall_lifetime

    window_embodied_per_area = database['GWP[kgCO2eq/m2]'][window_type]
    window_embodied_per_area_UBP = database['UBP[/m2]'][window_type]
    window_lifetime = database['lifetime'][window_type]
    window_embodied = window_embodied_per_area * total_window_area/window_lifetime
    window_embodied_UBP = window_embodied_per_area_UBP * total_window_area/window_lifetime

    roof_embodied_per_area = database['GWP[kgCO2eq/m2]'][roof_type]
    roof_embodied_per_area_UBP = database['UBP[/m2]'][roof_type]
    roof_lifetime = database['lifetime'][roof_type]
    roof_embodied = roof_embodied_per_area * total_roof_area/roof_lifetime
    roof_embodied_UBP = roof_embodied_per_area_UBP * total_roof_area / roof_lifetime

    floor_embodied_per_area = database['GWP[kgCO2eq/m2]'][ceiling_type]
    floor_embodied_per_area_UBP = database['UBP[/m2]'][ceiling_type]
    floor_lifetime = database['lifetime'][ceiling_type]
    floor_embodied = floor_embodied_per_area * energy_reference_area / floor_lifetime
    floor_embodied_UBP = floor_embodied_per_area_UBP * energy_reference_area / floor_lifetime

    embodied_envelope = wall_embodied + window_embodied + roof_embodied + floor_embodied
    embodied_envelope_UBP = wall_embodied_UBP + window_embodied_UBP + roof_embodied_UBP + floor_embodied_UBP

    return embodied_envelope, embodied_envelope_UBP
    # in total GHG emissions per year (kgCO2eq/a) and (UBP/a)



if __name__ == "__main__":
    pass