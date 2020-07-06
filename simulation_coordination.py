import numpy as np
import matplotlib.pyplot as plt
import simulation_engine as se
import simulation_engine_dynamic as sime
import data_prep as dp
import simulation_pv as pv
import pandas as pd



"""
###################################### SYSTEM DEFINITION ###############################################################
Im this first part of the code, building, its location and all the related systems are defined.
"""
scenarios_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\scenarios_UBA.xlsx"
configurations_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\configurations_UBA.xlsx"
performance_matrix_path_hourly = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\performance_matrix_UBA_hourly.xlsx"
performance_matrix_path_monthly = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\performance_matrix_UBA_monthly.xlsx"

scenarios = pd.read_excel(scenarios_path)
configurations = pd.read_excel(configurations_path, index_col="Configuration", skiprows=[1])

emission_performance_matrix_dyn = np.empty((len(configurations.index), len(scenarios.index)))
emission_performance_matrix_stat = np.empty((len(configurations.index), len(scenarios.index)))

## LCA angaben

electricity_factor_type = "annual"  # Can be "annual", "monthly", "hourly" (Hourly will only work for hourly model and
                                     # source: empa_ac )



for config_index, config in configurations.iterrows():


    ## Erforderliche Nutzereingaben:
    gebaeudekategorie_sia = config["building category"]
    regelung = "andere"  # oder "Referenzraum" oder "andere"
    hohe_uber_meer = config['altitude']# Eingabe
    energiebezugsflache = config['energy reference area']  # m2
    anlagennutzungsgrad_wrg = 0.0 ## SIA 380-1 Tab 23
    warmespeicherfahigkeit_pro_EBF = config['thermal mass per erf'] ## Wert noch nicht klar, bestimmen gemäss SN EN ISO 13786 oder Tab25 Einheiten?
    korrekturfaktor_luftungs_eff_f_v = 1.0  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24
    infiltration_volume_flow_planned = config['infiltration volume flow']  # Gemäss SIA 380-1 2016 3.5.5 soll 0.15m3/(hm2) verwendet werden. Korrigenda anschauen
    ventilation_volume_flow = config['ventilation volume flow'] # give a number in m3/(hm2) or select "SIA" to follow SIA380-1 code
    cooling_setpoint = config['cooling setpoint'] # give a number in deC or select "SIA" to follow the SIA380-1 code
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
    cooling_system = config['cooling system']  # Only affects dynamic calculation. Static does not include cooling
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
    floor = np.array([[config["floor area"]], [u_floor],[b_floor]])

    print("Configuration %s prepared" %config_index)

    for scenario_index, scenario in scenarios.iterrows():

        print("Calculating Scenario %s" %(scenario_index))

        weatherfile_path = scenario["weatherfile"]
        occupancy_path = scenario['occupancy schedule']
        heating_setpoint = scenario['heating setpoint']  # give a number in deC or select "SIA" to follow the SIA380-1 code
        electricity_factor_source = scenario['emission source']

        weather_data_sia = dp.epw_to_sia_irrad(weatherfile_path)
        infiltration_volume_flow = infiltration_volume_flow_planned * scenario['infiltration volume flow factor']  # This accounts for improper construction/tightness


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
        # pv yield in kWh for each hour
        #TODO check if the further functions also use kWh
        pv_yield_hourly = dp.photovoltaic_yield_hourly(pv_azimuth, pv_tilt, pv_efficiency, pv_performance_ratio, pv_area,
                                      weatherfile_path)


        ## heating demand and emission calculation

        Gebaeude_static = se.Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor, energiebezugsflache,
                                 anlagennutzungsgrad_wrg, infiltration_volume_flow, ventilation_volume_flow,
                                 warmespeicherfahigkeit_pro_EBF, korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer,
                                      heating_setpoint, cooling_setpoint, area_per_person)

        Gebaeude_static.pv_production = pv_yield_hourly
        Gebaeude_static.run_SIA_380_1(weather_data_sia)
        Gebaeude_static.run_ISO_52016_monthly(weather_data_sia)


        ## Gebäudedimensionen
        Gebaeude_static.heating_system = heizsystem
        Gebaeude_static.dhw_heating_system = dhw_heizsystem  ## Achtung, momentan ist der COP für DHW und für Heizung gleich.
        Gebaeude_static.cooling_system = cooling_system  # Diese Definitionens sollten verschoben werden zur definition des Objekts
        Gebaeude_static.run_dhw_demand()

        Gebaeude_static.run_SIA_electricity_demand(occupancy_path)


        # Gebaeude_dyn = sime.Sim_Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor, energiebezugsflache,
        #                                anlagennutzungsgrad_wrg, infiltration_volume_flow, ventilation_volume_flow,
        #                                warmespeicherfahigkeit_pro_EBF,
        #                                korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer, heizsystem, cooling_system,
        #                                dhw_heizsystem, heating_setpoint, cooling_setpoint, area_per_person)
        #
        # Gebaeude_dyn.pv_production = pv_yield_hourly
        #
        # Gebaeude_dyn.run_rc_simulation(weatherfile_path=weatherfile_path,
        #                              occupancy_path=occupancy_path)
        #
        #
        # Gebaeude_dyn.run_SIA_electricity_demand(occupancy_path)
        #






        #### OPERATIONAL IMPACT SIMULATION ####

        # Gebaeude_dyn.run_dynamic_emissions(emission_factor_source=electricity_factor_source,
        #                                    emission_factor_type=electricity_factor_type, grid_export_assumption="c")


        Gebaeude_static.run_SIA_380_emissions(emission_factor_source=electricity_factor_source,
                                              emission_factor_type=electricity_factor_type, avg_ashp_cop=2.8)


        # emission_performance_matrix_dyn[config_index, scenario_index] = Gebaeude_dyn.operational_emissions.sum()/1000.0
        emission_performance_matrix_stat[config_index, scenario_index] = Gebaeude_static.operational_emissions.sum()



    

        """

        ajajaj = zip(dp.hourly_to_monthly(Gebaeude_dyn.heating_demand) / 1000.0 / energiebezugsflache,
                      dp.hourly_to_monthly(Gebaeude_dyn.dhw_demand)/1000.0 / energiebezugsflache,
                      dp.hourly_to_monthly(Gebaeude_dyn.cooling_demand)/ 1000.0 / energiebezugsflache,
                      Gebaeude_static.heizwarmebedarf,
                      Gebaeude_static.dhw_demand,
                      -Gebaeude_static.monthly_cooling_demand,
                     Gebaeude_static.operational_emissions,
                     dp.hourly_to_monthly(Gebaeude_dyn.operational_emissions)/energiebezugsflache)


        results = pd.DataFrame(ajajaj, columns=["RC heating", "RC DHW", "RC cooling", "380 heating", "380 DHW", "ISO cooling", "static_emissions", "dynamic emissions"])
        # results["ISO2RC"] = results['ISO cooling']/results['RC cooling']
        results["RC_solar_gains"] = dp.hourly_to_monthly(Gebaeude_dyn.solar_gains)/1000.0 / energiebezugsflache
        results["ISO_solar_gains"] = Gebaeude_static.iso_solar_gains
        results["SIA_solar_gains"] = Gebaeude_static.solare_eintrage

        results["transmission_losses_ISO"] = Gebaeude_static.iso_transmission_losses
        results["transmission_losses_SIA"] = Gebaeude_static.transmissionsverluste

        results["internal_gains_RC"] = dp.hourly_to_monthly(Gebaeude_dyn.internal_gains)/1000.0 /energiebezugsflache
        results["internal_gains_SIA"] = Gebaeude_static.interne_eintrage
        results["internal_gains_ISO"] = Gebaeude_static.iso_internal_gains


        results[["RC_solar_gains", "ISO_solar_gains", "SIA_solar_gains"]].plot(kind='bar', title="Monthly Solar Gains")
        plt.ylabel("Solar Gains [kWh/m2M]")
        plt.show()


        results[["internal_gains_RC", "internal_gains_SIA", "internal_gains_ISO"]].plot(kind='bar', title="Internal Gains")
        plt.ylabel("Internal Gains [kWh/m2M]")
        plt.show()

        plt.plot(Gebaeude_dyn.cooling_demand/1000.0/energiebezugsflache, label="Cooling")
        plt.plot(Gebaeude_dyn.heating_demand/1000.0/energiebezugsflache, label="Heating")
        plt.ylabel("Energy / Power [kWh/m2h]")
        plt.legend()
        plt.show()

        results[["transmission_losses_ISO", "transmission_losses_SIA"]].plot(kind='bar', title="Transmission Losses")
        plt.ylabel("Monthly Transmission Losses [kWh/m2M]")
        plt.show()

        results[["RC heating", "RC DHW", "RC cooling", "380 heating", "380 DHW", "ISO cooling"]].plot(kind="bar", title="Energy Demand")
        plt.ylabel("Energy demand for heating, cooling and DHW [kWh/m2M]")
        plt.show()

        results[["static_emissions", "dynamic emissions"]].plot(kind="bar", title="Operational Emissions")
        plt.show()



    
        ###################################### EMBODIED EMISSIONS ##############################################################
        In this part the embodied emissions of a respective system and its components are defined.
        
        """


# pd.DataFrame(emission_performance_matrix_dyn, index=configurations.index, columns=scenarios.index).to_excel(performance_matrix_path_hourly)
pd.DataFrame(emission_performance_matrix_stat, index=configurations.index, columns=scenarios.index).to_excel(performance_matrix_path_monthly)
