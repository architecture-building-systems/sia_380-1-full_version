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

## Pfade zu weiteren Daten
weatherfile_path = r"C:\Users\walkerl\Documents\Zuerich-Kloten-hour.epw"
weather_data_sia = dp.epw_to_sia_irrad(weatherfile_path)
occupancy_path = r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator\auxiliary\occupancy_office.csv"

## Erforderliche Nutzereingaben:
gebaeudekategorie_sia = 1.1
regelung = "andere"  # oder "Referenzraum" oder "andere"
hohe_uber_meer = 435.0 # Eingabe
energiebezugsflache = 2275.0  # m2
anlagennutzungsgrad_wrg = 0.0 ## SIA 380-1 Tab 23
warmespeicherfahigkeit_pro_EBF = 2.2 ## Wert noch nicht klar, bestimmen gemäss SN EN ISO 13786 oder Tab25 Einheiten?
korrekturfaktor_luftungs_eff_f_v = 1.0  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24
infiltration_volume_flow = 0.15  # Gemäss SIA 380-1 2016 3.5.5 soll 0.15m3/(hm2) verwendet werden. Korrigenda anschauen
ventilation_volume_flow = 2.1 # give a number in m3/(hm2) or select "SIA" to follow SIA380-1 code
cooling_setpoint = 26  # degC (?)

## Gebäudehülle
u_windows = 1.3
u_walls = 0.25
u_roof = 0.19
u_floor = 0.23
b_floor = 0.4

## Systeme
"""
Choice: Oil, Natural Gas, Wood, Pellets, GSHP, ASHP, electric
Thes ystem choice is translated to a similar system available in the RC Simulator
"""
heizsystem = "ASHP"
dhw_heizsystem = heizsystem ## This is currently a limitation of the RC Model. Automatically the same!
cooling_system = "GSHP"  # Only affects dynamic calculation. Static does not include cooling
pv_efficiency = 0.18
pv_performance_ratio = 0.8
pv_area = 506.0  # m2, can be directly linked with roof size
pv_tilt = 30  # in degrees
pv_azimuth = 0  # IMPORTANT: The south convention applies. Sout = 0, North = -180 or + 180


## Bauteile:
# Windows: [[Orientation],[Areas],[U-value],[g-value]]
windows = np.array([["N", "E", "S", "W"],
                    [131.5, 131.5, 131.5, 131.5],
                    [u_windows, u_windows, u_windows, u_windows],
                    [0.6, 0.6, 0.6, 0.6]],
                   dtype=object)  # dtype=object is necessary because there are different data types

# walls: [[Areas], [U-values]] zuvor waren es 4 x 412.5
walls = np.array([[281., 281., 281., 281.],
                  [u_walls, u_walls, u_walls, u_walls]])


# roof: [[Areas], [U-values]]
roof = np.array([[506.0], [u_roof]])

# floor to ground (for now) [[Areas],[U-values],[b-values]]
floor = np.array([[506.0],[u_floor],[b_floor]])

simulation_type = "dynamic"  # Choose between static and dynamic


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

Loc = pv.Location(epwfile_path=weatherfile_path)
PvSurface = pv.PhotovoltaicSurface(azimuth_tilt=pv_azimuth, altitude_tilt=pv_tilt, stc_efficiency=pv_efficiency,
                                   performance_ratio=pv_performance_ratio, area=pv_area)
PvSurface.pv_simulation_hourly(Loc)
pv_yield_hourly = PvSurface.solar_yield  # in Wh consistent with RC but inconsistent with SIA


## heating demand and emission calculation

# if simulation_type == "static":

Gebaeude_static = se.Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor, energiebezugsflache,
                         anlagennutzungsgrad_wrg, infiltration_volume_flow, ventilation_volume_flow,
                         warmespeicherfahigkeit_pro_EBF, korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer)

Gebaeude_static.pv_production = pv_yield_hourly


Gebaeude_static.run_SIA_380_1(weather_data_sia)
Gebaeude_static.run_ISO_52016_monthly(weather_data_sia)


## Gebäudedimensionen
Gebaeude_static.heating_system = heizsystem
Gebaeude_static.dhw_heating_system = dhw_heizsystem  ## Achtung, momentan ist der COP für DHW und für Heizung gleich.
Gebaeude_static.cooling_system = cooling_system  # Diese Definitionens sollten verschoben werden zur definition des Objekts
Gebaeude_static.run_dhw_demand()

# print("heating")
# print(Gebaeude_static.heizwarmebedarf)
# print("dhw")
# print(Gebaeude_static.dhw_demand)
print("cooling")
print(Gebaeude_static.monthly_cooling_demand.sum())

Gebaeude_static.run_SIA_electricity_demand(occupancy_path)

Gebaeude_static.run_SIA_380_emissions(emission_factor_type="SIA_380", avg_ashp_cop=2.8)

# print(Gebaeude_static.operational_emissions.sum())  # CO2eq/m2a

# print(Gebaeude_1.non_renewable_primary_energy.sum())  # kWh/m2a

# elif simulation_type == "dynamic":

Gebaeude_dyn = sime.Sim_Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor, energiebezugsflache,
                               anlagennutzungsgrad_wrg, infiltration_volume_flow, ventilation_volume_flow,
                               warmespeicherfahigkeit_pro_EBF,
                               korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer, heizsystem, cooling_system,
                               dhw_heizsystem)

Gebaeude_dyn.pv_production = pv_yield_hourly

Gebaeude_dyn.run_rc_simulation(weatherfile_path=weatherfile_path,
                             occupancy_path=occupancy_path, cooling_setpoint=cooling_setpoint)


# print("Heating")
# print(dp.hourly_to_monthly(Gebaeude_dyn.heating_demand) / 1000.0 / energiebezugsflache)
# print("DHW")
# print(dp.hourly_to_monthly(Gebaeude_dyn.dhw_demand)/1000.0 / energiebezugsflache)
print("cooling")
print(dp.hourly_to_monthly((Gebaeude_dyn.cooling_demand)/ 1000.0 / energiebezugsflache).sum())

Gebaeude_dyn.run_SIA_electricity_demand(occupancy_path)
Gebaeude_dyn.run_dynamic_emissions("SIA_380", "c")

# print(Gebaeude_dyn.operational_emissions.sum() / 1000.0 / energiebezugsflache)
# print(dp.hourly_to_monthly((Gebaeude_1.heating_emissions + Gebaeude_1.dhw_emisions) / 1000.0 / energiebezugsflache))

# else:
#     print("simulation type not correctly specified")

"""####################################
"""



ajajaj = zip(dp.hourly_to_monthly(Gebaeude_dyn.heating_demand) / 1000.0 / energiebezugsflache,
              dp.hourly_to_monthly(Gebaeude_dyn.dhw_demand)/1000.0 / energiebezugsflache,
              dp.hourly_to_monthly(Gebaeude_dyn.cooling_demand)/ 1000.0 / energiebezugsflache,
              Gebaeude_static.heizwarmebedarf,
              Gebaeude_static.dhw_demand,
              -Gebaeude_static.monthly_cooling_demand)


results = pd.DataFrame(ajajaj, columns=["RC heating", "RC DHW", "RC cooling", "380 heating", "380 DHW", "ISO cooling"])
# results["ISO2RC"] = results['ISO cooling']/results['RC cooling']
results["RC_solar_gains"] = dp.hourly_to_monthly(Gebaeude_dyn.solar_gains)/1000.0 / energiebezugsflache
results["ISO_solar_gains"] = Gebaeude_static.iso_solar_gains
results["SIA_solar_gains"] = Gebaeude_static.solare_eintrage

results["transmission_losses_ISO"] = Gebaeude_static.iso_transmission_losses
results["transmission_losses_SIA"] = Gebaeude_static.transmissionsverluste

results["internal_gains_RC"] = dp.hourly_to_monthly(Gebaeude_dyn.internal_gains)/1000.0 /energiebezugsflache
results["internal_gains_SIA"] = Gebaeude_static.interne_eintrage
results["internal_gains_ISO"] = Gebaeude_static.iso_internal_gains

results[["RC_solar_gains", "ISO_solar_gains", "SIA_solar_gains"]].plot(kind='bar')
plt.show()


results[["internal_gains_RC", "internal_gains_SIA", "internal_gains_ISO"]].plot(kind='bar')
plt.show()

plt.plot(Gebaeude_dyn.cooling_demand)
plt.show()

results[["transmission_losses_ISO", "transmission_losses_SIA"]].plot(kind='bar')
plt.show()

results[["RC heating", "RC DHW", "RC cooling", "380 heating", "380 DHW", "ISO cooling"]].plot(kind="bar")
plt.show()

"""
###################################### EMBODIED EMISSIONS ##############################################################
In this part the embodied emissions of a respective system and its components are defined.

"""

