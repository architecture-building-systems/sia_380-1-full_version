import os
import numpy as np
import simulation_engine as se
import simulation_engine_dynamic as sime
import data_prep as dp
import embodied_emissions_calculation as eec
import investment_cost_calculation as icc
import pandas as pd
import time


"""
###################################### SYSTEM DEFINITION ###############################################################
In this first part, all the input files are located, Output filepaths are given and empty arrays are prepared to store
the outputs.
"""

main_path = os.path.abspath(os.path.dirname(__file__))
results_folder = os.path.join(main_path, 'data', 'results')
# Filepaths for input files
scenarios_path = os.path.join(main_path, 'data', 'scenarios.xlsx')
configurations_path = os.path.join(main_path, 'data', 'configurations.xlsx')
translation_path = os.path.join(main_path, 'data', 'translation_file.xlsx')

# Filepaths to databases:
sys_ee_database_path = os.path.join(main_path, 'data', 'embodied_emissions_systems.xlsx')
env_ee_database_path = os.path.join(main_path, 'data', 'embodied_emissions_envelope.xlsx')

# Filepaths for result files:
performance_matrix_path_monthly = os.path.join(main_path, results_folder, 'operational_emissions_monthly.xlsx')
performance_matrix_path_monthly_UBP = os.path.join(main_path, results_folder, 'operational_emissions_monthly_UBP.xlsx')
energy_costs_path_monthly = os.path.join(main_path, results_folder, 'energy_costs_monthly.xlsx')
operation_maintenance_costs_path = os.path.join(main_path, results_folder, 'operation_maintenance_costs.xlsx')
embodied_systems_stat_performance_path = os.path.join(main_path, results_folder, 'embodied_systems_monthly.xlsx')
embodied_systems_stat_performance_path_UBP = os.path.join(main_path, results_folder, 'embodied_systems_monthly_UBP.xlsx')
embodied_envelope_performance_path = os.path.join(main_path, results_folder, 'embodied_envelope.xlsx')
embodied_envelope_performance_path_UBP = os.path.join(main_path, results_folder, 'embodied_envelope_UBP.xlsx')
embodied_envelope_performance_detailed_path = os.path.join(main_path, results_folder, 'embodied_envelope_detailed')
investment_costs_systems_path_monthly = os.path.join(main_path, results_folder, 'investment_costs_systems_monthly.xlsx')
investment_costs_envelope_path = os.path.join(main_path, results_folder, 'investment_costs_envelope.xlsx')

stat_heat_path = os.path.join(main_path, results_folder, 'heat_demand_monthly.xlsx')
stat_cold_path = os.path.join(main_path, results_folder, 'cooling_demand_monthly.xlsx')
stat_dhw_path = os.path.join(main_path, results_folder, 'dhw_demand_monthly.xlsx')

pv_prod_path = os.path.join(main_path, results_folder, 'pv_yield.xlsx')

sc_ratio_monthly_path = os.path.join(main_path, results_folder, 'sc_ratio_monthly.xlsx')
el_autarky_stat_path = os.path.join(main_path, results_folder, 'el_autarky_monthly.xlsx')

econ_stat_path = os.path.join(main_path, results_folder, 'gross_electricity_consumption_monthly_calculation.xlsx')

heat_cop_stat_path = os.path.join(main_path, results_folder, 'weighted_heating_cop_monthly.xlsx')
dhw_cop_stat_path = os.path.join(main_path, results_folder, 'weighted_dhw_cop_monthly.xlsx')
cold_cop_stat_path = os.path.join(main_path, results_folder, 'weighted_cooling_cop_monthly.xlsx')

heating_power_monthly_path = os.path.join(main_path, results_folder, 'heating_power_monthly.xlsx')
cooling_power_monthly_path = os.path.join(main_path, results_folder, 'cooling_power_monthly.xlsx')


scenarios = pd.read_excel(scenarios_path)
configurations = pd.read_excel(configurations_path, index_col="Configuration", skiprows=[1])
translations = pd.read_excel(translation_path)
emission_performance_matrix_stat = np.empty((len(configurations.index), len(scenarios.index)))
emission_performance_matrix_stat_UBP = np.empty((len(configurations.index), len(scenarios.index)))
energy_costs_matrix_stat = np.empty((len(configurations.index), len(scenarios.index)))
operation_maintenance_costs = np.empty(len(configurations.index))
heating_demand_stat = np.empty((len(configurations.index), len(scenarios.index)))
dhw_demand_stat = np.empty((len(configurations.index), len(scenarios.index)))
cooling_demand_stat = np.empty((len(configurations.index), len(scenarios.index)))

nominal_heating_power_stat = np.empty(len(configurations.index))
nominal_cooling_power_stat = np.empty(len(configurations.index))

annual_heating_cop_stat = np.empty((len(configurations.index), len(scenarios.index)))
annual_dhw_cop_stat = np.empty((len(configurations.index), len(scenarios.index)))
annual_cooling_cop_stat = np.empty((len(configurations.index), len(scenarios.index)))

annual_pv_yield = np.empty((len(configurations.index), len(scenarios.index)))
annual_self_consumption_ratios_stat = np.empty((len(configurations.index), len(scenarios.index)))
electrical_annual_autarky_stat = np.empty((len(configurations.index), len(scenarios.index)))
annual_electricity_consumption_stat = np.empty((len(configurations.index), len(scenarios.index)))

# LCA angaben
electricity_factor_type = "annual"  # Can be "annual", "monthly", "hourly" (Hourly will only work for hourly model and
                                     # source: empa_ac )

# Here all the weatherfiles are imported to omit file opening in every loop (time savings)
unique_weather_paths = scenarios['weatherfile'].unique()

epw_labels = ['year', 'month', 'day', 'hour', 'minute', 'datasource', 'drybulb_C', 'dewpoint_C', 'relhum_percent',
                  'atmos_Pa', 'exthorrad_Whm2', 'extdirrad_Whm2', 'horirsky_Whm2', 'glohorrad_Whm2',
                  'dirnorrad_Whm2', 'difhorrad_Whm2', 'glohorillum_lux', 'dirnorillum_lux', 'difhorillum_lux',
                  'zenlum_lux', 'winddir_deg', 'windspd_ms', 'totskycvr_tenths', 'opaqskycvr_tenths', 'visibility_km',
                  'ceiling_hgt_m', 'presweathobs', 'presweathcodes', 'precip_wtr_mm', 'aerosol_opt_thousandths',
                  'snowdepth_cm', 'days_last_snow', 'Albedo', 'liq_precip_depth_mm', 'liq_precip_rate_Hour']
weather_file_dict_headers = {}
weather_file_dict_bodies = {}
weather_sia_dict = {}
for unique_path in unique_weather_paths:
    weather_file_dict_headers[unique_path] = pd.read_csv(unique_path, header=None, nrows=1)
    weather_file_dict_bodies[unique_path] = pd.read_csv(unique_path, skiprows=8, header=None, names=epw_labels)
    weather_sia_dict[unique_path] = dp.epw_to_sia_irrad(weather_file_dict_headers[unique_path],
                                                        weather_file_dict_bodies[unique_path])

## sun paths are precalculated
solar_zenith_dict = {}
solar_azimuth_dict = {}
for unique_path in unique_weather_paths:
    latitude = weather_file_dict_headers[unique_path].iloc[0,6]
    longitude = weather_file_dict_headers[unique_path].iloc[0, 7]
    solar_zenith_dict[unique_path], solar_azimuth_dict[unique_path] = dp.calc_sun_position(latitude, longitude)

# Here, all the occupancy profiles are imported to omit file opening in every loop:
unique_use_types = scenarios['building use type'].unique()
occupancy_schedules_dic = {}
for use_type in unique_use_types:
    occupancy_path = translations[translations['building use type'] == use_type]['occupancy schedule'].to_numpy()[0]
    occupancy_schedules_dic[use_type] = pd.read_csv(occupancy_path)

for config_index, config in configurations.iterrows():



    """
    Here the building parameters are extracted for each configuration and stored an the respective simulation variables.
    Currently some values that are not being used as input factors are defined in hard code.
    TODO: Remove hard coded variables when needed in system definition (e.g anlagenutzungsgrad_wrg)
    
    The building envelope is defined according to a single zone simulation model and the systems are specified according
    to the input file. The iteration object "config" represents one line of the configuration file.
    """
    ## Erforderliche Nutzereingaben:
    regelung = "andere"  # oder "Referenzraum" oder "andere"
    hohe_uber_meer = config['altitude']# Eingabe
    energiebezugsflache = config['energy reference area']  # m2
    anlagennutzungsgrad_wrg = 0.0  # SIA 380-1 Tab 23
    warmespeicherfahigkeit_pro_EBF = config['thermal mass per erf']  # Wert noch nicht klar, bestimmen gemäss SN EN ISO 13786 oder Tab25 Einheiten?
    korrekturfaktor_luftungs_eff_f_v = 1.0  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24
    infiltration_volume_flow_planned = config['infiltration volume flow']  # Gemäss SIA 380-1 2016 3.5.5 soll 0.15m3/(hm2) verwendet werden. Korrigenda anschauen
    ventilation_volume_flow = config['ventilation volume flow'] # give a number in m3/(hm2) or select "SIA" to follow SIA380-1 code
    increased_ventilation_volume_flow = config['increased ventilation volume flow'] # give a number in m3/hm2, this volume flow is used when cooling with outside air is possible
    area_per_person = config['area per person']  # give a number or select "SIA" to follow the SIA380-1 code (typical for MFH 40)

    ## Gebäudehülle
    u_windows_raw = config['u-value window']
    g_windows = config['g-value window']
    u_walls_raw = config['u-value wall']
    u_roof_raw = config['u-value roof']
    u_floor_raw = config['u-value floor']
    b_floor = 0.4 # lasse ich so, weil nicht direkt beeinflussbar

    ## Systeme
    """
    Choice: Oil, Natural Gas, Wood, Pellets, GSHP, ASHP, electric
    Thes system choice is translated to a similar system available in the RC Simulator
    """
    heizsystem = config['heating system']  # zb"ASHP"
    dhw_heizsystem = config['dhw heating system'] ## This is currently a limitation of the RC Model. Automatically the same!
    if dhw_heizsystem == 'same':
        dhw_heizsystem = heizsystem
    cooling_system = config['cooling system']
    heat_emission_system = config['heat emission system']
    cold_emission_system = config['cold emission system']
    pv_efficiency = config['PV efficiency']
    pv_performance_ratio = config['PV performance ratio']
    has_mechanical_ventilation = config['mechanical ventilation']

    pv_area = np.array(str(config['PV area']).split(" "), dtype=float)  # m2, can be directly linked with roof size
    pv_tilt = np.array(str(config['PV tilt']).split(" "), dtype=float)  # in degrees
    pv_azimuth = np.array(str(config['PV azimuth']).split(" "), dtype=float) # The north=0 convention applies

    max_electrical_storage_capacity = config['electrical storage capacity']  # in Wh !!!!

    wall_areas = np.array(config['wall areas'].split(" "), dtype=float)
    window_areas = np.array(config['window areas'].split(" "), dtype=float)
    window_orientations = np.array(config['window orientations'].split(" "), dtype=str)

    #operation and maintenance costs are calculated here, as they are only dependent on heating/cooling type (config)
    if cooling_system == heizsystem:
        operation_maintenance_costs[config_index] = dp.operation_maintenance_yearly_costs(heizsystem) / energiebezugsflache
    else:
        operation_maintenance_costs[config_index] = (dp.operation_maintenance_yearly_costs(heizsystem) +
                                                     dp.operation_maintenance_yearly_costs(cooling_system)) / \
                                                    energiebezugsflache

    #This print helps keeping track of the simulation progress.
    print("Configuration %s prepared" %config_index)
    start = time.time()
    for scenario_index, scenario in scenarios.iterrows():
        """
        This loop goes through all the scenarios which are defined in the scenario file. (Each scenario is one line)
        Here, further, scenario-dependent, system variables are defined. Basically, if one definition should be 
        considered as a scenario rather than a configuration, it can simply be moved here and the input files can be 
        adapted accordingly.
        """
        # print("Scenario", scenario_index)
        # start = time.time()

        weatherfile_path = scenario["weatherfile"]
        gebaeudekategorie_sia = scenario["building use type"]
        occupancy_path = \
        translations[translations['building use type'] == gebaeudekategorie_sia]['occupancy schedule'].to_numpy()[0]
        heating_setpoint = scenario['heating setpoint']  # number in deC or select "SIA" to follow the SIA380-1 code
        cooling_setpoint = scenario['cooling setpoint']  # number in deC or select "SIA" to follow the SIA380-1 code
        heat_pump_efficiency = scenario['heat pump efficiency']
        combustion_efficiency_factor = scenario['combustion efficiency factor']
        electricity_decarbonization_factor = scenario['electricity decarbonization factor']

        shading_factor_season = np.array(str(scenario['shading factor']).split(" "), dtype=float)
        # array with shading factors (per season: winter, spring, summer, fall)
        electricity_factor_source = scenario['emission source']
        electricity_factor_source_UBP = scenario['emission source UBP']
        energy_cost_source = scenario['energy cost source']
        shading_factor_monthly = dp.factor_season_to_month(shading_factor_season)

        # print("prep bef weather", time.time()-start)
        # start = time.time()
        weather_data_sia = weather_sia_dict[weatherfile_path]
        # weather_data_sia = dp.epw_to_sia_irrad(weather_file_dict_headers[weatherfile_path],weather_file_dict_bodies[weatherfile_path])

        # print("weather time", time.time()-start)
        # start = time.time()


        infiltration_volume_flow = infiltration_volume_flow_planned * scenario['infiltration volume flow factor']
        # This accounts for improper construction/tightness
        thermal_bridge_add_on = scenario['thermal bridge add on']  # in %
        thermal_bridge_factor = 1.0 + (thermal_bridge_add_on / 100.0)

        # the thermal bridge factor leads to an overall increase in transmittance losses. It is implemented here
        # because that is the easiest way. For result analysis the input file u-values need to be used.
        u_windows = u_windows_raw * thermal_bridge_factor
        u_walls = u_walls_raw * thermal_bridge_factor
        u_roof = u_roof_raw * thermal_bridge_factor
        u_floor = u_floor_raw * thermal_bridge_factor

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

        # print("preparation", time.time()-start)
        # start = time.time()
        """
        ###################################### SYSTEM SIMULATION #######################################################
        In this part the performance simulation is happening in three steps:
            1. An hourly time series for PV yield ist calculated
            2. The building objects are defined according to SIA for static and according to RC simulator for dynamic
            3. room heating and cooling demand is calculated
            4. dhw demand is calculated
            5. Electricity demand is calculated
            5. Operational emissions based on final electricity demand and other heat sources is calculated in the
               respective model time resolution.
            6. In scenario 0 which is the base/design scenario, the heating and cooling system are sized.
        
        This simulation is carried out in a monthly and an hourly time resolution.    
        """

        ## PV calculation
        # pv yield in Wh for each hour
        pv_yield_hourly = np.zeros(8760)
        for pv_number in range(len(pv_area)):
            pv_yield_hourly += dp.photovoltaic_yield_hourly(pv_azimuth[pv_number], pv_tilt[pv_number], pv_efficiency,
                                                           pv_performance_ratio, pv_area[pv_number],
                                                            weather_file_dict_headers[weatherfile_path],
                                                            weather_file_dict_bodies[weatherfile_path],
                                                            solar_zenith_dict[weatherfile_path],
                                                            solar_azimuth_dict[weatherfile_path])
        ## heating demand and emission calculation


        Gebaeude_static = se.Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor, energiebezugsflache,
                                      anlagennutzungsgrad_wrg, infiltration_volume_flow, ventilation_volume_flow,
                                      increased_ventilation_volume_flow, warmespeicherfahigkeit_pro_EBF,
                                      heat_pump_efficiency, combustion_efficiency_factor, electricity_decarbonization_factor,
                                      korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer, shading_factor_monthly, heizsystem, dhw_heizsystem,
                                      cooling_system, heat_emission_system, cold_emission_system, heating_setpoint,
                                      cooling_setpoint, area_per_person, has_mechanical_ventilation)

        # print("Object initialization", time.time() - start)
        # start = time.time()

        Gebaeude_static.pv_production = pv_yield_hourly

        Gebaeude_static.run_SIA_380_1(weather_data_sia)

        Gebaeude_static.run_ISO_52016_monthly(weather_data_sia)

        Gebaeude_static.run_dhw_demand()

        Gebaeude_static.run_SIA_electricity_demand(occupancy_schedules_dic[gebaeudekategorie_sia])

        # print("BES", time.time()-start)
        # start = time.time()


        Gebaeude_static.pv_peak_power = pv_area.sum() * pv_efficiency  # in kW (required for simplified Eigenverbrauchsabschätzung)

        Gebaeude_static.run_SIA_380_emissions(emission_factor_source=electricity_factor_source,
                                              emission_factor_source_UBP=electricity_factor_source_UBP,
                                              emission_factor_type=electricity_factor_type,
                                              weather_data_sia=weather_data_sia,
                                              energy_cost_source=energy_cost_source)




        emission_performance_matrix_stat[config_index, scenario_index] = Gebaeude_static.operational_emissions.sum()
        emission_performance_matrix_stat_UBP[config_index, scenario_index] = Gebaeude_static.operational_emissions_UBP.sum()
        energy_costs_matrix_stat[config_index, scenario_index] = Gebaeude_static.energy_costs.sum()

        heating_demand_stat[config_index, scenario_index] = Gebaeude_static.heizwarmebedarf.sum()
        cooling_demand_stat[config_index, scenario_index] = Gebaeude_static.monthly_cooling_demand.sum()
        dhw_demand_stat[config_index, scenario_index] = Gebaeude_static.dhw_demand.sum()

        annual_self_consumption_ratios_stat[config_index, scenario_index] = Gebaeude_static.annual_self_consumption

        annual_pv_yield[config_index, scenario_index] = pv_yield_hourly.sum()


        # This is the consumptio before PV!! The multiplication is necessary because the montly model does calculations
        # with normalised values [kWh]
        annual_electricity_consumption_stat[config_index, scenario_index] = Gebaeude_static.electricity_demand.sum()

        electrical_annual_autarky_stat[config_index, scenario_index] = (Gebaeude_static.electricity_demand.sum()-
                                           Gebaeude_static.net_electricity_demand.sum())/\
                                          Gebaeude_static.electricity_demand.sum()


        # COPs for heating systems without a HP are =1
        if heizsystem == "ASHP" or heizsystem == "GSHP":
            annual_heating_cop_stat[config_index, scenario_index] = Gebaeude_static.heizwarmebedarf.sum()/ Gebaeude_static.heating_elec.sum()

        else:
            annual_heating_cop_stat[config_index, scenario_index] = 1.0


        if dhw_heizsystem == "ASHP" or dhw_heizsystem == "GSHP":
            annual_dhw_cop_stat[config_index, scenario_index] = Gebaeude_static.dhw_demand.sum() / Gebaeude_static.dhw_elec.sum()

        else:
            annual_dhw_cop_stat[config_index, scenario_index] = 1.0


        if cooling_system == "ASHP" or cooling_system == "GSHP":
            annual_cooling_cop_stat[config_index, scenario_index] = Gebaeude_static.monthly_cooling_demand.sum() / Gebaeude_static.cooling_elec.sum()

        else:
            annual_cooling_cop_stat[config_index, scenario_index] = 1.0


        # This means that Scenario 0 needs to be the reference (design) scenario.
        if scenario_index == 0:
            Gebaeude_static.run_heating_sizing_384_201(weatherfile_path)
            nominal_heating_power_stat[config_index] = Gebaeude_static.nominal_heating_power  # in W

            Gebaeude_static.run_cooling_sizing()
            nominal_cooling_power_stat[config_index] = Gebaeude_static.nominal_cooling_power # in W


        else:
            pass

        # print("post proc", time.time()-start)
        # start = time.time()

    print("end")
    end = time.time()
    print(end-start)

# Store operational emissions
pd.DataFrame(emission_performance_matrix_stat, index=configurations.index, columns=scenarios.index).to_excel(
         performance_matrix_path_monthly)
pd.DataFrame(emission_performance_matrix_stat_UBP, index=configurations.index, columns=scenarios.index).to_excel(
         performance_matrix_path_monthly_UBP)

# store energy costs and operational and maintenance costs
pd.DataFrame(energy_costs_matrix_stat, index=configurations.index, columns=scenarios.index).to_excel(
         energy_costs_path_monthly)
pd.DataFrame(operation_maintenance_costs, index=configurations.index).to_excel(operation_maintenance_costs_path)

# store self consumption ratio
pd.DataFrame(annual_self_consumption_ratios_stat, index=configurations.index, columns=scenarios.index).to_excel(sc_ratio_monthly_path)

# store electrical_autarky
pd.DataFrame(electrical_annual_autarky_stat, index=configurations.index, columns=scenarios.index).to_excel(el_autarky_stat_path)

# store total electricity demand before PV
pd.DataFrame(annual_electricity_consumption_stat, index=configurations.index, columns=scenarios.index).to_excel(econ_stat_path)

# store room heat demand
pd.DataFrame(heating_demand_stat, index=configurations.index, columns=scenarios.index).to_excel(stat_heat_path)

# store dhw heat demand
pd.DataFrame(dhw_demand_stat, index=configurations.index, columns=scenarios.index).to_excel(stat_dhw_path)

#store room cooling demand
pd.DataFrame(cooling_demand_stat, index=configurations.index, columns=scenarios.index).to_excel(stat_cold_path)

# store annual pv yield
pd.DataFrame(annual_pv_yield, index=configurations.index, columns=scenarios.index).to_excel(pv_prod_path)

# store calculated cops
pd.DataFrame(annual_heating_cop_stat, index=configurations.index, columns=scenarios.index).to_excel(heat_cop_stat_path)
pd.DataFrame(annual_dhw_cop_stat, index=configurations.index, columns=scenarios.index).to_excel(dhw_cop_stat_path)
pd.DataFrame(annual_cooling_cop_stat, index=configurations.index, columns=scenarios.index).to_excel(cold_cop_stat_path)

# store heating sizing
pd.DataFrame(nominal_heating_power_stat , index=configurations.index).to_excel(heating_power_monthly_path)
pd.DataFrame(nominal_cooling_power_stat, index=configurations.index).to_excel(cooling_power_monthly_path)





"""
Here the dynamic simulation is completed. 
TODO: At some point it makes would probably make sense to separate the code here or at least store the heating/cooling
dimensioning into a file and read it back. Sometimes the simulation crashes here after 99% of the simulation time. This
sucks...
"""


###################################### EMBODIED EMISSIONS AND INVESTMENT COSTS #########################################
""" The embodied emissions only need to be calculated per Configuration. They are assumed to only come into 
the calculation at the beginning of the life cycle. This means, that for now, they are not dependent on the 
scenarios. (only scenario 0)

Codewise it is important to see that here it is no longer possible to call the created building objects. Data has to be
recollected from the configuration file.
"""

embodied_systems_emissions_performance_matrix_stat = np.empty((len(configurations.index), len(scenarios.index)))
embodied_envelope_emissions_performance_matrix = np.empty((len(configurations.index), len(scenarios.index)))

embodied_systems_emissions_performance_matrix_stat_UBP = np.empty((len(configurations.index), len(scenarios.index)))
embodied_envelope_emissions_performance_matrix_UBP = np.empty((len(configurations.index), len(scenarios.index)))

eee_wall = np.empty((len(configurations.index), len(scenarios.index)))
eee_wall_UBP = np.empty((len(configurations.index), len(scenarios.index)))
eee_window = np.empty((len(configurations.index), len(scenarios.index)))
eee_window_UBP = np.empty((len(configurations.index), len(scenarios.index)))
eee_roof = np.empty((len(configurations.index), len(scenarios.index)))
eee_roof_UBP = np.empty((len(configurations.index), len(scenarios.index)))
eee_floor = np.empty((len(configurations.index), len(scenarios.index)))
eee_floor_UBP = np.empty((len(configurations.index), len(scenarios.index)))

investment_costs_systems_matrix_stat = np.empty((len(configurations.index), len(scenarios.index)))
investment_costs_envelope_matrix = np.empty((len(configurations.index), len(scenarios.index)))

"""
###################################### SYSTEM SIMULATION #######################################################
In this part the embodied simulation is happening in two steps:
    1. Systems emissions are looked at depending on the sizing from above for both models
    2. The envelope (and intermal thermal mass) related embodied emissions are calculated.
    
This part of the simulation is pure data lookup and simple operations. It is therefore time-wise not relevant in the 
whole simulation process.    
"""

sys_ee_database = pd.read_excel(sys_ee_database_path, index_col="Name")  # systems embodied emissions
env_ee_database = pd.read_excel(env_ee_database_path, index_col="Name")  # envelope emobdied emissions




for config_index, config in configurations.iterrows():
    """
    For the embodied emisisons a single loop through the configurations is enough.
    """

    energiebezugsflache = config['energy reference area']  # m2

    # At the moment hard coded here because embodied emissions are not yet based on scenarios
    envelope_lifetime_factor = 1.0
    system_lifetime_factor = 1.0

    ## Systeme
    """
    Choice: Oil, Natural Gas, Wood, Pellets, GSHP, ASHP, electric
    The system choice is translated to a similar system available in the RC Simulator
    """
    heating_system = config['heating system']  # zb"ASHP"
    dhw_heizsystem = config[
        'dhw heating system']  ## This is currently a limitation of the RC Model. Automatically the same!
    if dhw_heizsystem == 'same':
        dhw_heizsystem = heating_system

    # ventilation
    relevant_volume_flow = max(config['ventilation volume flow'], config['increased ventilation volume flow'])

    embodied_impact_stat = eec.calculate_system_related_embodied_emissions(ee_database=sys_ee_database,
                                                        gebaeudekategorie=scenarios.loc[0, 'building use type'],
                                                        energy_reference_area=config['energy reference area'],
                                                        heizsystem=heating_system,
                                                        heat_emission_system=config['heat emission system'],
                                                        heat_distribution=config['heat distribution'],
                                                        nominal_heating_power=nominal_heating_power_stat[config_index],
                                                        dhw_heizsystem=dhw_heizsystem,
                                                        cooling_system = config['cooling system'],
                                                        cold_emission_system = config['cold emission system'],
                                                        nominal_cooling_power=nominal_cooling_power_stat[config_index],
                                                        pv_area=np.array(str(config['PV area']).split(" "), dtype=float).sum(),
                                                        pv_type=config['PV type'],
                                                        pv_efficiency=config['PV efficiency'],
                                                        has_mechanical_ventilation=config['mechanical ventilation'],
                                                        max_aussenluft_volumenstrom=relevant_volume_flow)


    total_wall_area = np.array(config['wall areas'].split(" "), dtype=float).sum()
    total_window_area = np.array(config['window areas'].split(" "), dtype=float).sum()
    total_roof_area = np.array(config["roof area"]).sum()
    floor_area = np.array(config["floor area"]).sum()

    wall_type = config['wall type']
    window_type = config["window type"]
    roof_type = config["roof type"]

    annualized_embodied_emsissions_envelope = \
        eec.calculate_envelope_emissions(database=env_ee_database,
                                         total_wall_area=total_wall_area,
                                         wall_type=config['wall type'],
                                         total_window_area=total_window_area,
                                         window_type=config['window type'],
                                         total_roof_area=total_roof_area,
                                         roof_type=config['roof type'],
                                         floor_area=floor_area,
                                         ceiling_type=config['ceiling type'])


    for scenario_index, scenario in scenarios.iterrows():

        envelope_lifetime_factor = scenario['envelope lifetime factor']
        system_lifetime_factor = scenario['system lifetime factor']
        zinssatz = scenario['zinssatz']

        embodied_systems_emissions_performance_matrix_stat[config_index, scenario_index] = embodied_impact_stat[0] / energiebezugsflache/ system_lifetime_factor
        embodied_systems_emissions_performance_matrix_stat_UBP[config_index, scenario_index] = embodied_impact_stat[1] / energiebezugsflache/ system_lifetime_factor

        embodied_envelope_emissions_performance_matrix[config_index, scenario_index] = annualized_embodied_emsissions_envelope[0]/energiebezugsflache / envelope_lifetime_factor
        embodied_envelope_emissions_performance_matrix_UBP[config_index, scenario_index] = annualized_embodied_emsissions_envelope[1]/energiebezugsflache / envelope_lifetime_factor


        eee_wall[config_index, scenario_index] = annualized_embodied_emsissions_envelope[2]/energiebezugsflache/ envelope_lifetime_factor
        eee_wall_UBP[config_index, scenario_index] = annualized_embodied_emsissions_envelope[3]/energiebezugsflache/ envelope_lifetime_factor
        eee_window[config_index, scenario_index] = annualized_embodied_emsissions_envelope[4] / energiebezugsflache/ envelope_lifetime_factor
        eee_window_UBP[config_index, scenario_index] = annualized_embodied_emsissions_envelope[5] / energiebezugsflache/ envelope_lifetime_factor
        eee_roof[config_index, scenario_index] = annualized_embodied_emsissions_envelope[6] / energiebezugsflache/ envelope_lifetime_factor
        eee_roof_UBP[config_index, scenario_index] = annualized_embodied_emsissions_envelope[7] / energiebezugsflache/ envelope_lifetime_factor
        eee_floor[config_index, scenario_index] = annualized_embodied_emsissions_envelope[8]/energiebezugsflache/ envelope_lifetime_factor
        eee_floor_UBP[config_index, scenario_index] = annualized_embodied_emsissions_envelope[9]/energiebezugsflache/ envelope_lifetime_factor

        # As the zinssatz is dependent on scenarios, the investment calculation has to be made for each scenario
        annual_investment_costs_systems_stat = \
            icc.calculate_system_related_investment_cost(ee_database=sys_ee_database,
                                                         gebaeudekategorie=scenarios.loc[0, 'building use type'],
                                                         energy_reference_area=config['energy reference area'],
                                                         heizsystem=heating_system,
                                                         heat_emission_system=config['heat emission system'],
                                                         heat_distribution=config['heat distribution'],
                                                         nominal_heating_power=nominal_heating_power_stat[config_index],
                                                         dhw_heizsystem=dhw_heizsystem,
                                                         cooling_system=config['cooling system'],
                                                         cold_emission_system=config['cold emission system'],
                                                         nominal_cooling_power=nominal_cooling_power_stat[config_index],
                                                         pv_area=np.array(str(config['PV area']).split(" "),
                                                                          dtype=float).sum(),
                                                         pv_type=config['PV type'],
                                                         pv_efficiency=config['PV efficiency'],
                                                         has_mechanical_ventilation=config['mechanical ventilation'],
                                                         zinssatz=zinssatz)


        annual_investment_costs_envelope = \
            icc.calculate_envelope_investment_cost(database=env_ee_database,
                                             total_wall_area=total_wall_area,
                                             wall_type=config['wall type'],
                                             total_window_area=total_window_area,
                                             window_type=config['window type'],
                                             total_roof_area=total_roof_area,
                                             roof_type=config['roof type'],
                                             floor_area=floor_area,
                                             ceiling_type=config['ceiling type'],
                                             zinssatz=zinssatz)

        investment_costs_systems_matrix_stat[config_index, scenario_index] = \
            annual_investment_costs_systems_stat / energiebezugsflache / system_lifetime_factor

        investment_costs_envelope_matrix[config_index, scenario_index] = \
            annual_investment_costs_envelope / energiebezugsflache / envelope_lifetime_factor

"""
Last but not least, all the created dataframes from the embodied part are stored in the file locations given in the 
very beginning of the code.
"""
# GWP emissions
pd.DataFrame(embodied_systems_emissions_performance_matrix_stat, index=configurations.index).to_excel(
    embodied_systems_stat_performance_path)

pd.DataFrame(embodied_envelope_emissions_performance_matrix, index=configurations.index).to_excel(
    embodied_envelope_performance_path)

# UBP emissions
pd.DataFrame(embodied_systems_emissions_performance_matrix_stat_UBP, index=configurations.index).to_excel(
    embodied_systems_stat_performance_path_UBP)

pd.DataFrame(embodied_envelope_emissions_performance_matrix_UBP, index=configurations.index).to_excel(
    embodied_envelope_performance_path_UBP)


pd.DataFrame(eee_wall).to_excel(os.path.join(embodied_envelope_performance_detailed_path, 'wall_GWP.xlsx'))
pd.DataFrame(eee_wall_UBP).to_excel(os.path.join(embodied_envelope_performance_detailed_path, 'wall_UBP.xlsx'))
pd.DataFrame(eee_window).to_excel(os.path.join(embodied_envelope_performance_detailed_path, 'window_GWP.xlsx'))
pd.DataFrame(eee_window_UBP).to_excel(os.path.join(embodied_envelope_performance_detailed_path, 'wall_UBP.xlsx'))
pd.DataFrame(eee_roof).to_excel(os.path.join(embodied_envelope_performance_detailed_path, 'roof_GWP.xlsx'))
pd.DataFrame(eee_roof_UBP).to_excel(os.path.join(embodied_envelope_performance_detailed_path, 'roof_UBP.xlsx'))
pd.DataFrame(eee_floor).to_excel(os.path.join(embodied_envelope_performance_detailed_path, 'floor_GWP.xlsx'))
pd.DataFrame(eee_floor_UBP).to_excel(os.path.join(embodied_envelope_performance_detailed_path, 'floor_UBP.xlsx'))


os.path.join(main_path, results_folder, 'embodied_envelope_detailed')

# Investment costs for systems and envelope
pd.DataFrame(investment_costs_systems_matrix_stat, index=configurations.index).to_excel(
    investment_costs_systems_path_monthly)

pd.DataFrame(investment_costs_envelope_matrix, index=configurations.index).to_excel(
    investment_costs_envelope_path)