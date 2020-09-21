import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import data_prep as dp

import simulation_engine as se
import simulation_engine_dynamic as sime
import embodied_emissions_calculation as eec

from SALib.sample import saltelli
from SALib.analyze import sobol

if __name__ == '__main__':

    """
    ###################################### SYSTEM DEFINITION ###############################################################
    Im this first part of the code, building, its location and all the related systems are defined.
    """

    sys_ee_database_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\embodied_emissions_systems.xlsx"
    env_ee_database_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\embodied_emissions_envelope.xlsx"

    gebaeudekategorie_sia = 1.1
    regelung = "andere"  # oder "Referenzraum" oder "andere"
    hohe_uber_meer = 435.0  # Eingabe
    energiebezugsflache = 2275.0  # m2
    ventilation_volume_flow = 2.1  # give a number in m3/(hm2) or select "SIA" to follow SIA380-1 code
    korrekturfaktor_luftungs_eff_f_v = 1.0
    b_floor = 0.4
    u_floor = 0.23
    u_roof = 0.14
    u_walls = 0.14
    u_windows = 0.85
    g_windows = 0.5
    heating_setpoint = "SIA"
    pv_azimuth = 180
    cooling_setpoint = "SIA"
    warmespeicherfahigkeit_pro_EBF = 0.08
    pv_efficiency = 0.18  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24
    anlagennutzungsgrad_wrg = 0.0
    infiltration_volume_flow = 0.15
    heizsystem = "ASHP"
    heat_emission_system = "floor heating"
    heat_distribution_system = "hydronic"
    dhw_heizsystem = heizsystem  ## This is currently a limitation of the RC Model. Automatically the same!
    cooling_system = "GSHP"  # Only affects dynamic calculation. Static does not include cooling
    pv_performance_ratio = 0.8
    pv_area = energiebezugsflache  # m2, can be directly linked with roof size
    pv_tilt = 30  # in degrees
    pv_type = "m-Si"

    wall_type = "UBA_EnEV_wall_stb"
    window_type = "UBA_EnEV_window"
    roof_type = "UBA_EnEV_roof_stb"



    ## LCA angaben

    electricity_factor_type = "annual"  # Can be "annual", "monthly", "hourly" (Hourly will only work for hourly model and
    # source: empa_ac )




    ### Generate Samples
    problem = {
        'num_vars': 7,
        'names': ['weather_file', 'infiltration_flow', 'occupancy_schedule', 'area_per_person', "heating_setpoint",
                  "cooling_setpoint", "grid_emission_factor"],
        'bounds': [[0.5, 4.5],
                   [0.05, 0.50],
                   [0.5, 2.5],
                   [20.0, 150.0],
                   [18.0, 25.0],
                   [20.0, 30.0],
                   [0.5, 2.5]]}  # Heating system ## Abklären, ob dies so gemacht werden kann für diskretisierte Variablen.
    # "Natural Gas":0.249, "Wood":0.020, "Pellets":0.048, "GSHP_CH_mix":0.055, "ASHP_CH_mix":0.076, "GSHP_EU_mix":0.207, "ASHP_EU_mix":0.285
    param_values = saltelli.sample(problem, 150)


    number_to_climate = {1: r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zürich-hour_historic.epw",
                         2: r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zürich-2030-A2.epw",
                         3: r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zürich-2070-A1B.epw",
                         4: r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zürich-2070-B1.epw"}

    number_to_occupancy = {1: r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator\auxiliary\occupancy_office.csv",
                           2: r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator\auxiliary\occupancy_single_res.csv"}

    number_to_grid_emission = {1:"SIA", 2:"eu"}

    ### Run Model
    Y = np.zeros([param_values.shape[0]])
    Z = np.zeros([param_values.shape[0]])
    for i, X in enumerate(param_values):


        climate_number = np.round(X[0], 0)
        weatherfile_path = number_to_climate[climate_number]
        weather_data_sia = dp.epw_to_sia_irrad(weatherfile_path)

        infiltration_volume_flow=X[1]

        occupancy_number = np.round(X[2],0)
        occupancy_path = number_to_occupancy[occupancy_number]

        area_per_person = X[3]
        heating_setpoint = X[4]
        cooling_setpoint = X[5]

        grid_emission_number = np.round(X[6],0)
        electricity_factor_source = number_to_grid_emission[grid_emission_number]  # Can be "SIA", "eu", "empa_ac"


        ## Bauteile:
        # Windows: [[Orientation],[Areas],[U-value],[g-value]]
        windows = np.array([["N", "E", "S", "W"],
                            [131.5, 131.5, 131.5, 131.5],
                            [u_windows, u_windows, u_windows, u_windows],
                            [g_windows, g_windows, g_windows, g_windows]],
                           dtype=object)  # dtype=object is necessary because there are different data types
        total_window_area = windows[1].sum()

        # walls: [[Areas], [U-values]] zuvor waren es 4 x 412.5
        walls = np.array([[281.0, 281.0, 281.0, 281.0],
                          [u_walls, u_walls, u_walls, u_walls]])
        total_wall_area = walls[0].sum()


        # roof: [[Areas], [U-values]]
        roof = np.array([[506], [u_roof]])
        total_roof_area = roof[1].sum()

        # floor to ground (for now) [[Areas],[U-values],[b-values]]
        floor = np.array([[506], [u_floor], [b_floor]])

        ### Monatliche Berechnungen
        pv_yield_hourly = dp.photovoltaic_yield_hourly(pv_azimuth, pv_tilt, pv_efficiency, pv_performance_ratio,
                                                       pv_area,
                                                       weatherfile_path)
        Gebaeude_static = se.Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor, energiebezugsflache,
                                      anlagennutzungsgrad_wrg, infiltration_volume_flow, ventilation_volume_flow,
                                      warmespeicherfahigkeit_pro_EBF, korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer,
                                      heating_setpoint, cooling_setpoint, area_per_person)
        Gebaeude_static.pv_production = pv_yield_hourly
        Gebaeude_static.run_SIA_380_1(weather_data_sia)
        Gebaeude_static.run_ISO_52016_monthly(weather_data_sia)
        Gebaeude_static.heating_system = heizsystem
        Gebaeude_static.dhw_heating_system = dhw_heizsystem  ## Achtung, momentan ist der COP für DHW und für Heizung gleich.
        Gebaeude_static.cooling_system = cooling_system  # Diese Definitionens sollten verschoben werden zur definition des Objekts
        Gebaeude_static.run_dhw_demand()
        Gebaeude_static.run_SIA_electricity_demand(occupancy_path)
        Gebaeude_static.run_SIA_380_emissions(emission_factor_source=electricity_factor_source,
                                              emission_factor_type=electricity_factor_type, avg_ashp_cop=2.8)

        Gebaeude_static.run_heating_sizing_384_201(weatherfile_path)
        Gebaeude_static.run_cooling_sizing()

        systems_emissions_stat = eec.calculate_system_related_embodied_emissions(ee_database_path=sys_ee_database_path,
                                                                                 gebaeudekategorie=gebaeudekategorie_sia,
                                                                                 energy_reference_area=energiebezugsflache,
                                                                                 heizsystem=heizsystem,
                                                                                 heat_emission_system=heat_emission_system,
                                                                                 heat_distribution=heat_distribution_system,
                                                                                 nominal_heating_power=Gebaeude_static.nominal_heating_power,
                                                                                 dhw_heizsystem=None,
                                                                                 cooling_system=cooling_system,
                                                                                 cold_emission_system=heat_emission_system,
                                                                                 nominal_cooling_power=Gebaeude_static.nominal_cooling_power,
                                                                                 pv_area=pv_area,
                                                                                 pv_type=pv_type,
                                                                                 pv_efficiency=pv_efficiency)

        ### Stündliche Berechnungen:

        Gebaeude_dyn = sime.Sim_Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor,
                                         energiebezugsflache,
                                         anlagennutzungsgrad_wrg, infiltration_volume_flow, ventilation_volume_flow,
                                         warmespeicherfahigkeit_pro_EBF,
                                         korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer, heizsystem, cooling_system,
                                         dhw_heizsystem, heating_setpoint, cooling_setpoint, area_per_person)

        Gebaeude_dyn.pv_production = pv_yield_hourly

        Gebaeude_dyn.run_rc_simulation(weatherfile_path=weatherfile_path,
                                       occupancy_path=occupancy_path)
        Gebaeude_dyn.run_SIA_electricity_demand(occupancy_path)
        Gebaeude_dyn.run_dynamic_emissions(emission_factor_source=electricity_factor_source,
                                           emission_factor_type=electricity_factor_type, grid_export_assumption="c")

        Gebaeude_dyn.run_heating_sizing()
        Gebaeude_static.run_cooling_sizing()

        systems_emissions_dyn = eec.calculate_system_related_embodied_emissions(ee_database_path=sys_ee_database_path,
                                                                                gebaeudekategorie=gebaeudekategorie_sia,
                                                                                energy_reference_area=energiebezugsflache,
                                                                                heizsystem=heizsystem,
                                                                                heat_emission_system=heat_emission_system,
                                                                                heat_distribution=heat_distribution_system,
                                                                                nominal_heating_power=Gebaeude_static.nominal_heating_power,
                                                                                dhw_heizsystem=None,
                                                                                cooling_system=cooling_system,
                                                                                cold_emission_system=heat_emission_system,
                                                                                nominal_cooling_power=Gebaeude_static.nominal_cooling_power,
                                                                                pv_area=pv_area,
                                                                                pv_type=pv_type,
                                                                                pv_efficiency=pv_efficiency)


        envelope_emissions = eec.calculate_envelope_emissions(database_path=env_ee_database_path,
                                                              total_wall_area=total_wall_area,
                                                              wall_type=wall_type,
                                                              total_window_area=total_window_area,
                                                              window_type=window_type,
                                                              total_roof_area=total_roof_area,
                                                              roof_type=roof_type)

        # Y[i] = Gebaeude_static.heizwarmebedarf.sum()
        # Z[i] = (Gebaeude_dyn.heating_demand/energiebezugsflache/1000).sum()
        Y[i] = Gebaeude_static.operational_emissions.sum()
        Z[i] = (Gebaeude_dyn.operational_emissions/energiebezugsflache/1000).sum()


    print("sobol analysis...")
    Si = sobol.analyze(problem, Y, parallel=True, n_processors=6)

    print(Si['S1'])
    print(Si['S2'])
    print(Si['ST'])

    # print("x1-x2:", Si['S2'][0,1])
    # print("x1-x3:", Si['S2'][0,2])
    # print("x2-x3:", Si['S2'][1,2])
    #

    plt.bar(problem['names'], Si['ST'])
    # plt.title('Sobol Sensitivities of Parameters for heating energy')
    plt.title("Monatliche Berechnung")
    plt.ylabel("Sobol coefficient")
    plt.show()

    plt.pcolormesh(Si['S2'], cmap='binary')
    plt.colorbar()
    plt.xticks(np.arange(0.5, 6.5, 1.0), problem['names'])
    plt.yticks(np.arange(0.5, 6.5, 1.0), problem['names'])
    plt.title("Monatliche Berechnung")
    plt.show()

    print("sobol analysis...")
    Si = sobol.analyze(problem, Z, parallel=True, n_processors=6 )

    print(Si['S1'])
    print(Si['S2'])
    print(Si['ST'])

    # print("x1-x2:", Si['S2'][0,1])
    # print("x1-x3:", Si['S2'][0,2])
    # print("x2-x3:", Si['S2'][1,2])
    #

    plt.bar(problem['names'], Si['ST'])
    # plt.title('Sobol Sensitivities of Parameters for heating energy')
    plt.title("stündliche Berechnung")
    plt.ylabel("Sobol coefficient")
    plt.show()

    plt.pcolormesh(Si['S2'], cmap='binary')
    plt.colorbar()
    plt.xticks(np.arange(0.5,6.5,1.0), problem['names'])
    plt.yticks(np.arange(0.5,6.5,1.0), problem['names'])
    plt.title("stündliche Berechnung")
    plt.show()
