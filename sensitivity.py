import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import data_prep as dp

import simulation_engine as se
import simulation_engine_dynamic as sime
import embodied_emissions_calculation as eec

from SALib.sample import saltelli
from SALib.analyze import sobol


if __name__=='__main__':

    """
    ###################################### SYSTEM DEFINITION ###############################################################
    Im this first part of the code, building, its location and all the related systems are defined.
    """
    # scenarios_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\scenarios.xlsx"
    # configurations_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\configurations.xlsx"
    # performance_matrix_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\performance_matrix.xlsx"
    #
    # scenarios = pd.read_excel(scenarios_path)
    # configurations = pd.read_excel(configurations_path, index_col="Configuration", skiprows=[1])

    ## LCA angaben
    electricity_factor_source = "SIA"  # Can be "SIA", "eu", "empa_ac"
    electricity_factor_type = "annual"  # Can be "annual", "monthly", "hourly" (Hourly will only work for hourly model and
    # source: empa_ac )

    u_wall_values = {"SIA_ziel":0.10, "EnEV":0.25, "KfW55":0.14, "alt":0.4 }
    u_window_values = {"SIA_ziel":0.90, "EnEV":1.3, "KfW55":0.9, "alt":1.5 }

    wall_materialisation = {1:"UBA_EnEV_wall_stb", 2:"UBA_EnEV_wall_wood", 3:"UBA_KfW_55_wall_stb",
                            4:"UBA_KfW_55_wall_wood"}
    window_materialisation = {1:"UBA_EnEV_window", 2:"UBA_KfW_55_window"}


    ### Generate Samples
    problem = {
        'num_vars':8,
        'names':['envelope type', 'g_windows', 'PV area', 'thermal_mass',
                 'heat recovery', 'heating system', "wall material", "window  material"],
        'bounds':[[0.5, 4.5],  # envelope
                  [0.2, 0.8],  # g_windows
                  [0.0, 506.0],  # PV area from 0 to full roof
                  [0.03, 0.15],  # waermespeicherfaehigkeit pro EBF
                  [0.0, 0.70],  # eta g, heat recovery efficiency
                  [0.5, 4.5],   # Heating system ## Abklären, ob dies so gemacht werden kann für diskretisierte Variablen.
                  [0.5, 4.5],  # wall_materialisation (at the moment stb/eps and holz/zellulose
                  [0.5, 2.5]]}  # window materialisation (at the moment, Kunststoff, 2 oder 3fach Verglasung)


    # "Natural Gas":0.249, "Wood":0.020, "Pellets":0.048, "GSHP_CH_mix":0.055, "ASHP_CH_mix":0.076, "GSHP_EU_mix":0.207, "ASHP_EU_mix":0.285
    param_values = saltelli.sample(problem, 150)
    gebaeudekategorie_sia = 1.1
    regelung = "andere"  # oder "Referenzraum" oder "andere"
    hohe_uber_meer = 435.0  # Eingabe
    energiebezugsflache = 2275.0  # m2
    ventilation_volume_flow = 2.1  # give a number in m3/(hm2) or select "SIA" to follow SIA380-1 code
    infiltration_volume_flow = 0.15  # SIA
    area_per_person = "SIA"  # give a number or select "SIA" to follow the SIA380-1 code (typical for MFH 40)
    korrekturfaktor_luftungs_eff_f_v = 1.0
    heat_emission_system = "floor heating"
    heat_distribution_system = "hydronic"
    b_floor = 0.4
    heating_setpoint = "SIA"
    cooling_setpoint = "SIA"
    pv_efficiency = 0.2
    pv_azimuth = 180.0 # south
    pv_type = "m-Si"
    pv_performance_ratio = 0.8
    pv_tilt = 30  # in degrees

    # window_type = "UBA_KfW_55_window"
    # roof_type = "UBA_KfW_55_roof_stb"

    weatherfile_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zürich-hour_historic.epw"
    weather_data_sia = dp.epw_to_sia_irrad(weatherfile_path)
    occupancy_path = r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator\auxiliary\occupancy_office.csv"
    sys_ee_database_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\embodied_emissions_systems.xlsx"
    env_ee_database_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\embodied_emissions_envelope.xlsx"

    ### Run Model
    Y = np.zeros([param_values.shape[0]])
    Z = np.zeros([param_values.shape[0]])
    emb_stat = np.zeros([param_values.shape[0]])
    emb_dyn = np.zeros([param_values.shape[0]])
    for i, X in enumerate(param_values):

        envelope_number = np.round(X[0],0)
        number_to_envelope = {1:"SIA_ziel", 2:"EnEV", 3:"KfW55", 4:"alt"}
        u_floor = u_roof = u_walls = u_wall_values[number_to_envelope[envelope_number]]
        u_windows = u_window_values[number_to_envelope[envelope_number]]
        g_windows = X[1]
        pv_area = X[2]
        warmespeicherfahigkeit_pro_EBF = X[3]
        anlagennutzungsgrad_wrg = X[4]
        heating_system_number = np.round(X[5], 0)
        number_to_system = {1:"ASHP", 2:"electric", 3:"Pellets", 4:"GSHP"}
        heizsystem = number_to_system[heating_system_number]
        dhw_heizsystem = heizsystem  ## This is currently a limitation of the RC Model. Automatically the same!

        cooling_system = "GSHP"

        materialisation_no = np.round(X[6], 0)
        wall_type = wall_materialisation[materialisation_no]
        roof_type = wall_materialisation[materialisation_no]

        window_type_no = np.round(X[7], 0)
        window_type = window_materialisation[window_type_no]


        ## Bauteile:
        # Windows: [[Orientation],[Areas],[U-value],[g-value]]
        windows = np.array([["N", "E", "S", "W"],
                            [131.5, 131.5, 131.5, 131.5],
                            [u_windows, u_windows, u_windows, u_windows],
                            [g_windows, g_windows, g_windows, g_windows]],
                           dtype=object)  # dtype=object is necessary because there are different data types

        total_window_area =windows[1].sum()

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
        Gebaeude_static.pv_peak_power = pv_area * pv_efficiency  # kW
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
        #
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

        # Y[i] = Gebaeude_1.heizwarmebedarf.sum()  #kWh/m2a
        # Y[i] = Gebaeude_static.heizwarmebedarf.sum()
        # Z[i] = (Gebaeude_dyn.heating_demand/energiebezugsflache/1000).sum()

        envelope_emissions = eec.calculate_envelope_emissions(database_path=env_ee_database_path,
                                         total_wall_area=total_wall_area,
                                         wall_type=wall_type,
                                         total_window_area=total_window_area,
                                         window_type=window_type,
                                         total_roof_area=total_roof_area,
                                         roof_type=roof_type)


        Y[i] = systems_emissions_stat/energiebezugsflache + envelope_emissions/energiebezugsflache + Gebaeude_static.operational_emissions.sum()
        emb_stat[i] = systems_emissions_stat/energiebezugsflache + envelope_emissions/energiebezugsflache

        Z[i] = (Gebaeude_dyn.operational_emissions/energiebezugsflache/1000).sum() + envelope_emissions/energiebezugsflache +systems_emissions_dyn/energiebezugsflache
        emb_dyn[i] = envelope_emissions/energiebezugsflache +systems_emissions_dyn/energiebezugsflache


    pd.DataFrame(param_values).to_excel(r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\sensitivity\param_values.xlsx")
    pd.DataFrame(Y).to_excel(r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\sensitivity\Y.xlsx")
    pd.DataFrame(Z).to_excel(r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\sensitivity\Z.xlsx")
    pd.DataFrame(emb_stat).to_excel(r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\sensitivity\emb_stat.xlsx")
    pd.DataFrame(emb_dyn).to_excel(r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\sensitivity\emb_dyn.xlsx")


    print("sobol analysis...")
    Si = sobol.analyze(problem, Y, parallel=True, n_processors=6 )

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
    plt.xticks(np.arange(0.5,9.5,1.0), problem['names'])
    plt.yticks(np.arange(0.5,9.5,1.0), problem['names'])
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
    plt.title("Stündliche Berechnung")
    plt.ylabel("Sobol coefficient")
    plt.show()

    plt.pcolormesh(Si['S2'], cmap='binary')
    plt.colorbar()
    plt.xticks(np.arange(0.5,9.5,1.0), problem['names'])
    plt.yticks(np.arange(0.5,9.5,1.0), problem['names'])
    plt.title("Stündliche Berechnung")
    plt.show()

