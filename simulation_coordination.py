import os
import numpy as np
import simulation_engine as se
import simulation_engine_dynamic as sime
import data_prep as dp
import embodied_emissions_calculation as eec
import pandas as pd
import time


"""
###################################### SYSTEM DEFINITION ###############################################################
Im this first part of the code, building, its location and all the related systems are defined.
"""

main_path = os.path.abspath(os.path.dirname(__file__))

# Filepaths for input files
scenarios_path = os.path.join(main_path, 'data', 'scenarios.xlsx')
configurations_path = os.path.join(main_path, 'data', 'configurations.xlsx')

# Filepaths to databases:
sys_ee_database_path = os.path.join(main_path, 'data', 'embodied_emissions_systems.xlsx')
env_ee_database_path = os.path.join(main_path, 'data', 'embodied_emissions_envelope.xlsx')

# Filepaths for result files:
performance_matrix_path_hourly = os.path.join(main_path, 'data', 'operational_emissions_hourly.xlsx')
performance_matrix_path_monthly = os.path.join(main_path, 'data', 'operational_emissions_monthly.xlsx')
embodied_systems_stat_performance_path = os.path.join(main_path, 'data', 'embodied_systems_monthly.xlsx')
embodied_systems_dyn_performance_path = os.path.join(main_path, 'data', 'embodied_systems_hourly.xlsx')
embodied_envelope_performance_path = os.path.join(main_path, 'data', 'embodied_envelope.xlsx')

dyn_heat_path = os.path.join(main_path, 'data', 'heat_demand_hourly.xlsx')
dyn_cold_path = os.path.join(main_path, 'data', 'cooling_demand_hourly.xlsx')
stat_heat_path = os.path.join(main_path, 'data', 'heat_demand_monthly.xlsx')
stat_cold_path = os.path.join(main_path, 'data', 'cooling_demand_monthly.xlsx')

# sc_ratio_path = os.path.join(main_path, 'data', 'sc_ratio_hourly.xlsx')
# econ_dyn_path = os.path.join(main_path, 'data', 'gross_electricity_consumption.xlsx')



scenarios = pd.read_excel(scenarios_path)
configurations = pd.read_excel(configurations_path, index_col="Configuration", skiprows=[1])
emission_performance_matrix_dyn = np.empty((len(configurations.index), len(scenarios.index)))
emission_performance_matrix_stat = np.empty((len(configurations.index), len(scenarios.index)))
heating_demand_dyn = np.empty((len(configurations.index), len(scenarios.index)))
heating_demand_stat = np.empty((len(configurations.index), len(scenarios.index)))
cooling_demand_dyn = np.empty((len(configurations.index), len(scenarios.index)))
cooling_demand_stat = np.empty((len(configurations.index), len(scenarios.index)))

nominal_heating_power_stat = np.empty(len(configurations.index))
nominal_cooling_power_stat = np.empty(len(configurations.index))
nominal_heating_power_dyn = np.empty(len(configurations.index))
nominal_cooling_power_dyn = np.empty(len(configurations.index))

# annual_self_consumption_ratios_dyn = np.empty((len(configurations.index), len(scenarios.index)))
# annual_electricity_consumption_dyn = np.empty((len(configurations.index), len(scenarios.index)))

# LCA angaben

electricity_factor_type = "annual"  # Can be "annual", "monthly", "hourly" (Hourly will only work for hourly model and
                                     # source: empa_ac )




for config_index, config in configurations.iterrows():


    ## Erforderliche Nutzereingaben:
    gebaeudekategorie_sia = config["building category"]
    regelung = "andere"  # oder "Referenzraum" oder "andere"
    hohe_uber_meer = config['altitude']# Eingabe
    energiebezugsflache = config['energy reference area']  # m2
    anlagennutzungsgrad_wrg = 0.0  # SIA 380-1 Tab 23
    warmespeicherfahigkeit_pro_EBF = config['thermal mass per erf']  # Wert noch nicht klar, bestimmen gemäss SN EN ISO 13786 oder Tab25 Einheiten?
    korrekturfaktor_luftungs_eff_f_v = 1.0  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24
    infiltration_volume_flow_planned = config['infiltration volume flow']  # Gemäss SIA 380-1 2016 3.5.5 soll 0.15m3/(hm2) verwendet werden. Korrigenda anschauen
    ventilation_volume_flow = config['ventilation volume flow'] # give a number in m3/(hm2) or select "SIA" to follow SIA380-1 code
    area_per_person = config['area per person']  # give a number or select "SIA" to follow the SIA380-1 code (typical for MFH 40)


    ## Gebäudehülle
    u_windows = config['u-value window']
    g_windows = config['g-value window']
    u_walls = config['u-value wall']
    u_roof = config['u-value roof']
    u_floor = config['u-value floor']
    b_floor = 0.4 # lasse ich so, weil nicht direkt beeinflussbar

    ## Systeme
    """
    Choice: Oil, Natural Gas, Wood, Pellets, GSHP, ASHP, electric
    Thes ystem choice is translated to a similar system available in the RC Simulator
    """
    heizsystem = config['heating system']  # zb"ASHP"
    dhw_heizsystem = heizsystem ## This is currently a limitation of the RC Model. Automatically the same!
    cooling_system = config['cooling system']
    pv_efficiency = config['PV efficiency']
    pv_performance_ratio = config['PV performance ratio']
    pv_area = config['PV area']  # m2, can be directly linked with roof size
    pv_tilt = config['PV tilt']  # in degrees
    pv_azimuth = config['PV azimuth']  # The north=0 convention applies
    wall_areas = np.array(config['wall areas'].split(" "), dtype=float)
    window_areas = np.array(config['window areas'].split(" "), dtype=float)
    window_orientations = np.array(config['window orientations'].split(" "), dtype=str)


    ## Bauteile:
    # Windows: [[Orientation],[Areas],[U-value],[g-value]]
    windows = np.array([window_orientations,
                        window_areas,
                        np.repeat(u_windows, len(window_orientations)),
                        np.repeat(g_windows, len(window_orientations))],
                       dtype=object)  # dtype=object is necessary because there are different data types

    # walls: [[Areas], [U-values]] zuvor waren es 4 x 412.5
    walls = np.array([wall_areas,
                      np.repeat(u_walls, len(wall_areas))])


    # roof: [[Areas], [U-values]]
    roof = np.array([[config["roof area"]], [u_roof]])

    # floor to ground (for now) [[Areas],[U-values],[b-values]]
    floor = np.array([[config["floor area"]], [u_floor], [b_floor]])

    print("Configuration %s prepared" %config_index)

    for scenario_index, scenario in scenarios.iterrows():

        start=time.time()

        print("Calculating Scenario %s" %(scenario_index))

        weatherfile_path = scenario["weatherfile"]
        occupancy_path = scenario['occupancy schedule']
        heating_setpoint = scenario['heating setpoint']  # give a number in deC or select "SIA" to follow the SIA380-1 code
        cooling_setpoint = scenario['cooling setpoint']  # give a number in deC or select "SIA" to follow the SIA380-1 code

        electricity_factor_source = scenario['emission source']

        weather_data_sia = dp.epw_to_sia_irrad(weatherfile_path)
        infiltration_volume_flow = infiltration_volume_flow_planned * scenario['infiltration volume flow factor']  # This accounts for improper construction/tightness
        # print("weather to SIA")
        # print(time.time() - intermediate)
        # intermediate = time.time()

        """
        ###################################### SYSTEM SIMULATION ###############################################################
        In this part the performance simulation is happening in three steps:
            1. An hourly time series for PV yield ist calculated
            2. A demand time series for DHW is calculated
            3. A demand time series for room heating is calculated
            4. A demand time series for room cooling is calculated (at the moment only for dynamic model)
            5. Operational emissions based on final electricity demand and other heat sources is calculated in the respective
               model time resolution.
        
        These steps are either carried out in the dynamic or in the static model. This is chosen above.       
        """

        ## PV calculation
        # pv yield in Wh for each hour
        pv_yield_hourly = dp.photovoltaic_yield_hourly(pv_azimuth, pv_tilt, pv_efficiency, pv_performance_ratio, pv_area,
                                      weatherfile_path)


        ## heating demand and emission calculation

        Gebaeude_static = se.Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor, energiebezugsflache,
                                 anlagennutzungsgrad_wrg, infiltration_volume_flow, ventilation_volume_flow,
                                 warmespeicherfahigkeit_pro_EBF, korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer,
                                      heating_setpoint, cooling_setpoint, area_per_person)

        Gebaeude_static.heating_system = heizsystem
        Gebaeude_static.dhw_heating_system = dhw_heizsystem  ## Achtung, momentan ist der COP für DHW und für Heizung gleich.
        Gebaeude_static.cooling_system = cooling_system  # Diese Definitionens sollten verschoben werden zur definition des Objekts


        Gebaeude_static.pv_production = pv_yield_hourly
        Gebaeude_static.run_SIA_380_1(weather_data_sia)
        Gebaeude_static.run_ISO_52016_monthly(weather_data_sia)
        Gebaeude_static.run_dhw_demand()

        Gebaeude_static.run_SIA_electricity_demand(occupancy_path)

        Gebaeude_dyn = sime.Sim_Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor, energiebezugsflache,
                                       anlagennutzungsgrad_wrg, infiltration_volume_flow, ventilation_volume_flow,
                                       warmespeicherfahigkeit_pro_EBF,
                                       korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer, heizsystem, cooling_system,
                                       dhw_heizsystem, heating_setpoint, cooling_setpoint, area_per_person)

        Gebaeude_dyn.pv_production = pv_yield_hourly  # in kWh (! ACHTUNG, RC immer in Wh !)

        Gebaeude_dyn.run_rc_simulation(weatherfile_path=weatherfile_path,
                                     occupancy_path=occupancy_path)

        Gebaeude_dyn.run_SIA_electricity_demand(occupancy_path)



        #### OPERATIONAL IMPACT SIMULATION ####

        Gebaeude_dyn.run_dynamic_emissions(emission_factor_source=electricity_factor_source,
                                           emission_factor_type=electricity_factor_type, grid_export_assumption="c")

        Gebaeude_static.pv_peak_power = pv_area * pv_efficiency  # in kW (required for simplified Eigenverbrauchsabschätzung)
        Gebaeude_static.run_SIA_380_emissions(emission_factor_source=electricity_factor_source,
                                              emission_factor_type=electricity_factor_type, avg_ashp_cop=2.8)



        emission_performance_matrix_dyn[config_index, scenario_index] = Gebaeude_dyn.operational_emissions.sum()/energiebezugsflache

        heating_demand_dyn[config_index, scenario_index] = Gebaeude_dyn.heating_demand.sum()/1000.0/energiebezugsflache
        cooling_demand_dyn[config_index, scenario_index] = Gebaeude_dyn.cooling_demand.sum()/1000.0/energiebezugsflache


        emission_performance_matrix_stat[config_index, scenario_index] = Gebaeude_static.operational_emissions.sum()
        heating_demand_stat[config_index, scenario_index] = Gebaeude_static.heizwarmebedarf.sum()
        cooling_demand_stat[config_index, scenario_index] = Gebaeude_static.monthly_cooling_demand.sum()

        # annual_self_consumption_ratios_dyn[config_index, scenario_index] = dp.calculate_self_consumption(Gebaeude_dyn.electricity_demand, pv_yield_hourly)
        # annual_electricity_consumption_dyn[config_index, scenario_index] = Gebaeude_dyn.electricity_demand.sum()

        # This means that Scenario 0 needs to be the reference (design) scenario.
        if scenario_index == 0:
            Gebaeude_static.run_heating_sizing_384_201(weatherfile_path)
            nominal_heating_power_stat[config_index] = Gebaeude_static.nominal_heating_power  # in W

            Gebaeude_static.run_cooling_sizing()
            nominal_cooling_power_stat[config_index] = Gebaeude_static.nominal_cooling_power # in W


            Gebaeude_dyn.run_heating_sizing()
            Gebaeude_dyn.run_cooling_sizing()

            nominal_heating_power_dyn[config_index] = Gebaeude_dyn.nominal_heating_power  # in W
            nominal_cooling_power_dyn[config_index] = abs(Gebaeude_dyn.nominal_cooling_power)  # in W


        else:
            pass

        print("end")
        end = time.time()
        print(end-start)

pd.DataFrame(emission_performance_matrix_dyn, index=configurations.index, columns=scenarios.index).to_excel(
         performance_matrix_path_hourly)
pd.DataFrame(emission_performance_matrix_stat, index=configurations.index, columns=scenarios.index).to_excel(
         performance_matrix_path_monthly)

# pd.DataFrame(annual_self_consumption_ratios_dyn, index=configurations.index, columns=scenarios.index).to_excel(sc_ratio_path)
# pd.DataFrame(annual_electricity_consumption_dyn, index=configurations.index, columns=scenarios.index).to_excel(econ_dyn_path)
pd.DataFrame(heating_demand_dyn, index=configurations.index, columns=scenarios.index).to_excel(dyn_heat_path)
pd.DataFrame(cooling_demand_dyn, index=configurations.index, columns=scenarios.index).to_excel(dyn_cold_path)

pd.DataFrame(heating_demand_stat, index=configurations.index, columns=scenarios.index).to_excel(stat_heat_path)
pd.DataFrame(cooling_demand_stat, index=configurations.index, columns=scenarios.index).to_excel(stat_cold_path)




###################################### EMBODIED EMISSIONS ##############################################################
""" The embodied emissions only need to be calculated per Configuration. They are assumed to only come into the calculation
at the beginning of the life cycle. This means, that for now, they are not dependent on the scenarios."""

embodied_systems_emissions_performance_matrix_stat = np.empty(len(configurations.index))
embodied_systems_emissions_performance_matrix_dyn = np.empty(len(configurations.index))
embodied_envelope_emissions_performance_matrix = np.empty(len(configurations.index))

for config_index, config in configurations.iterrows():

    energiebezugsflache = config['energy reference area']  # m2

    ## Systeme
    """
    Choice: Oil, Natural Gas, Wood, Pellets, GSHP, ASHP, electric
    Thes ystem choice is translated to a similar system available in the RC Simulator
    """

    embodied_systems_emissions_performance_matrix_stat[config_index] = \
        eec.calculate_system_related_embodied_emissions(ee_database_path=sys_ee_database_path,
                                                        gebaeudekategorie=config['building category'],
                                                        energy_reference_area=config['energy reference area'],
                                                        heizsystem=config['heating system'],
                                                        heat_emission_system=config['heat emission system'],
                                                        heat_distribution=config['heat distribution'],
                                                        nominal_heating_power=nominal_heating_power_stat[config_index],
                                                        dhw_heizsystem=None,
                                                        cooling_system = config['cooling system'],
                                                        cold_emission_system = config['cold emission'],
                                                        nominal_cooling_power=nominal_cooling_power_stat[config_index],
                                                        pv_area=config['PV area'],
                                                        pv_type=config['PV type'],
                                                        pv_efficiency=config['PV efficiency'])/energiebezugsflache

    embodied_systems_emissions_performance_matrix_dyn[config_index] = annualized_embodied_system_emissions = \
        eec.calculate_system_related_embodied_emissions(ee_database_path=sys_ee_database_path,
                                                        gebaeudekategorie=config['building category'],
                                                        energy_reference_area=config['energy reference area'],
                                                        heizsystem=config['heating system'],
                                                        heat_emission_system=config['heat emission system'],
                                                        heat_distribution=config['heat distribution'],
                                                        nominal_heating_power=nominal_heating_power_dyn[config_index],
                                                        dhw_heizsystem=None,
                                                        cooling_system=config['cooling system'],
                                                        cold_emission_system=config['cold emission'],
                                                        nominal_cooling_power=nominal_cooling_power_dyn[config_index],
                                                        pv_area=config['PV area'],
                                                        pv_type=config['PV type'],
                                                        pv_efficiency=config['PV efficiency'])/energiebezugsflache


    total_wall_area = np.array(config['wall areas'].split(" "), dtype=float).sum()
    total_window_area = np.array(config['window areas'].split(" "), dtype=float).sum()
    total_roof_area = np.array(config["roof area"]).sum()

    wall_type = config['wall type']
    window_type = config["window type"]
    roof_type = config["roof type"]

    annualized_embodied_emsissions_envelope = \
        eec.calculate_envelope_emissions(database_path=env_ee_database_path,
                                         total_wall_area=total_wall_area,
                                         wall_type=config['wall type'],
                                         total_window_area=total_window_area,
                                         window_type=config['window type'],
                                         total_roof_area=total_roof_area,
                                         roof_type=config['roof type'],
                                         energy_reference_area=energiebezugsflache,
                                         floor_type=config['ceiling type'])/energiebezugsflache


    embodied_envelope_emissions_performance_matrix[config_index] = annualized_embodied_emsissions_envelope


pd.DataFrame(embodied_systems_emissions_performance_matrix_stat, index=configurations.index).to_excel(
    embodied_systems_stat_performance_path)
pd.DataFrame(embodied_systems_emissions_performance_matrix_dyn, index=configurations.index).to_excel(
    embodied_systems_dyn_performance_path)
pd.DataFrame(embodied_envelope_emissions_performance_matrix, index=configurations.index).to_excel(
    embodied_envelope_performance_path)

