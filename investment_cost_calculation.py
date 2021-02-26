import pandas as pd
import numpy as np
import data_prep as dp

def calculate_system_related_investment_cost(ee_database_path, gebaeudekategorie, energy_reference_area,
                                                heizsystem, heat_emission_system,
                                                heat_distribution, nominal_heating_power, dhw_heizsystem,
                                                cooling_system, cold_emission_system, nominal_cooling_power,
                                                pv_area, pv_type, pv_efficiency, has_mechanical_ventilation,
                                                zinssatz):
    """
    This function calculates the annual investment cost for all energy systems and their related costs such as distribution
    systems. The spreadsheet embodied_emissions_systems.xlsx acts as the input.
    The total investment cost are divided by an annuity factor (composed of depreciation time (lifetime) and rate of return i)
    in order to obtain annualized investment costs.
    At the moment, future investments are neglected. It is assumed, that all investments are made at time = 0.
    TODO: add disposal costs as future costs which come into play at the end of a system's life (discounted)
    :param ee_database_path: string, filepath to system database
    :param gebaeudekategorie: float, SIA bulding category
    :param energy_reference_area: float, in m2
    :param heizsystem: string, as listed in system database
    :param heat_emission_system: string, as listed in system database
    :param heat_distribution: string, as listed in system database
    :param nominal_heating_power: float, in W
    :param dhw_heizsystem: string, as listed in system database
    :param cooling_system: string, as listed in system database
    :param cold_emission_system: string, as listed in system database
    :param nominal_cooling_power: float, in W
    :param pv_area: float, in m2
    :param pv_type: string, as listed in system database
    :param pv_efficiency: float in %/100
    :param has_mechanical_ventilation: boolean (True/False)
    :param zinssatz: float, in %
    :return: annual investment cost of system components in CHF/a
    """
    # TODO maybe there is a need to change linear cost development to non-linear, especially for PV!
    database = pd.read_excel(ee_database_path, index_col="Name")
    if zinssatz == 0.0:
        i = 0.0000001
    else:
        i = zinssatz/100

    ## Heater
    heater_cost_per_kw = database['Cost'][heizsystem]  # this data is in CHF/kW
    heater_lifetime = database['lifetime'][heizsystem]
    heater_cost = heater_cost_per_kw * nominal_heating_power / 1000.0 * (i/(1-pow((i+1),-heater_lifetime)))  # heating power comes in W

    # dhw heating is assumed to be included in the space heating capacity


    ## Cooler  TODO: IF COOLING POWER IS BIGGER THAN HEATING POWER IT IS NOT CALCULATED CORRECTLY
    if cooling_system == heizsystem:
        if nominal_cooling_power <= nominal_heating_power:
            cooler_cost = 0.0
        else:
            cooler_cost_per_kw = database['Cost'][cooling_system]  # this data is in CHF/kW
            cooler_lifetime = database['lifetime'][cooling_system]
            # cooling power comes in W
            cooler_cost = cooler_cost_per_kw * nominal_cooling_power / 1000.0 * (i/(1-pow((i+1),-cooler_lifetime)))
            heater_cost = 0.0

    else:
        cooler_cost_per_kw = database['Cost'][cooling_system]  # this data is in CHF/kW
        cooler_lifetime = database['lifetime'][cooling_system]
        # cooling power comes in W
        cooler_cost = cooler_cost_per_kw * nominal_cooling_power / 1000.0 * (i/(1-pow((i+1),-cooler_lifetime)))



    ## Heat emission
    if heat_emission_system == 'air':
        # In that case 0.0 is assigned to heat emission system because it is already considered in
        # mechanical ventilation
        heat_emission_cost_per_area = 0.0
        heat_emission_lifetime = 1.0  # to avoid division by 0
        if has_mechanical_ventilation == False:
            print("you chose heat distribution by air but do not have mechanical ventilation")
            quit()
    else:
        heat_emission_cost_per_area = database['Cost'][heat_emission_system]  # this data is in CHF/kW
        heat_emission_lifetime = database['lifetime'][heat_emission_system]

    heat_emission_cost = heat_emission_cost_per_area * energy_reference_area * (i/(1-pow((i+1),-heat_emission_lifetime)))


    ## Heat distribution
    if heat_distribution == "hydronic":
        if int(gebaeudekategorie) == 1:
            heat_distribution_cost_per_area = database['Cost']['hydronic heat distribution residential']
            heat_distribution_lifetime = database['lifetime']['hydronic heat distribution residential']
        elif int(gebaeudekategorie) == 3:
            heat_distribution_cost_per_area = database['Cost']['hydronic heat distribution office']

            heat_distribution_lifetime = database['lifetime']['hydronic heat distribution office']

        else:
            heat_distribution_cost_per_area = 0.0
            heat_distribution_lifetime = 1.0  # this avoids division by zero if embodied = 0
            print("no embodied emissions for heat distribution")

    elif heat_distribution == 'electric':
        heat_distribution_cost_per_area = 0.0
        heat_distribution_lifetime = 1.0  # to avoid division by zero

    elif heat_distribution == 'air':
        #Todo: I am not sure if that makes sense or if it would be included in mechanidcal ventilation
        heat_distribution_cost_per_area = database['Value'][heat_distribution]  # this data is in CHF/kW
        heat_distribution_lifetime = database['lifetime'][heat_distribution]
    else:
        print('You did not specify a correct heat distribution system')
        quit()

    heat_distribution_cost = heat_distribution_cost_per_area * energy_reference_area * (
            i/(1-pow((i+1),-heat_distribution_lifetime)))



    ## Cold distribution and emission TODO: IF COOLING POWER IS BIGGER THAN HEATING POWER IT IS NOT CALCULATED CORRECTLY
    if heat_emission_system == cold_emission_system:
        cold_emission_cost = 0.0

    else:
        cold_emission_cost_per_area = database['Cost'][cold_emission_system]  # this data is in CHF/kW
        cold_emission_lifetime = database['lifetime'][cold_emission_system]
        cold_emission_cost = cold_emission_cost_per_area * energy_reference_area * (
            i/(1-pow((i+1),-cold_emission_lifetime)))  # cooling power comes in W

    thermal_cost = heater_cost + cooler_cost + heat_distribution_cost + heat_emission_cost + cold_emission_cost


    # Calculation of embodied emissions for ventilation system
    if has_mechanical_ventilation == True:
        ventilation_cost_per_era = database['Cost']['mechanical ventilation']
        ventilation_lifetime = database['lifetime']['mechanical ventilation']
        ventilation_cost = ventilation_cost_per_era * energy_reference_area * (i/(1-pow((i+1),-ventilation_lifetime)))
    else:
        ventilation_cost = 0.0

    # Calculation of embodied emissions for the electrical systems
    ## PV System
    pv_kWp = pv_area * pv_efficiency  # at STC Irradiance = 1kW/m2
    pv_cost_per_kw = dp.pv_cost_interpolation(pv_kWp)  # this data is in CHF/kWp
    pv_lifetime = database['lifetime'][pv_type]
    pv_cost = pv_cost_per_kw * pv_kWp * (i/(1-pow((i+1),-pv_lifetime)))

    electrical_cost = pv_cost

    # Calculation of total building systems cost: heater, cooler, distribution, emission, electric (PV), ventilation
    investment_cost_thermal_electrical = thermal_cost + electrical_cost + ventilation_cost

    return investment_cost_thermal_electrical
    # in CHF/a


def calculate_envelope_investment_cost(database_path, total_wall_area, wall_type, total_window_area,
                                 window_type, total_roof_area, roof_type, floor_area, ceiling_type, zinssatz):
    """
    This function calculates the annual investment cost for envelope components. The total investment cost are divided
    by an annuity factor (composed of depreciation time (lifetime) and rate of return i) in order to obtain annualized
    investment costs. The spreadsheet embodied_enissions_envelope.xslx acts as an input.
    TODO: add disposal costs as future costs which come into play at the end of a envelope's life
    :param database_path: string, filepath to envelope database
    :param total_wall_area: float, in m2
    :param wall_type: string, as listed in envelope database
    :param total_window_area: float, in m2
    :param window_type: as listed in envelope database
    :param total_roof_area: float, in m2
    :param roof_type: as listed in envelope database
    :param energy_reference_area: float, in m2
    :param ceiling_type: as listed in envelope database
    :return: annual investment cost of envelope components
    """

    database = pd.read_excel(database_path, index_col="Name")
    if zinssatz == 0.0:
        i = 0.0000001
    else:
        i = zinssatz/100

    # Walls
    wall_cost_per_area = database['Cost[CHF/m2]'][wall_type]
    wall_lifetime = database['lifetime'][wall_type]
    wall_cost = total_wall_area * wall_cost_per_area * (i/(1-pow((i+1),-wall_lifetime)))

    # Windows
    window_cost_per_area = database['Cost[CHF/m2]'][window_type]
    window_lifetime = database['lifetime'][window_type]
    window_cost = window_cost_per_area * total_window_area * (i/(1-pow((i+1),-window_lifetime)))

    # Roof
    roof_cost_per_area = database['Cost[CHF/m2]'][roof_type]
    roof_lifetime = database['lifetime'][roof_type]
    roof_cost = roof_cost_per_area * total_roof_area * (i/(1-pow((i+1),-roof_lifetime)))

    # Ceilings/Floor
    floor_cost_per_area = database['Cost[CHF/m2]'][ceiling_type]
    floor_lifetime = database['lifetime'][ceiling_type]
    floor_cost = floor_cost_per_area * floor_area * (i/(1-pow((i+1),-floor_lifetime)))

    investment_cost_envelope = wall_cost + window_cost + roof_cost + floor_cost


    return investment_cost_envelope
    # in CHF/a

if __name__ == "__main__":
    pass