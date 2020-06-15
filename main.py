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

weatherfile_path = r"C:\Users\walkerl\polybox\phd\Validation\ASHRAE140\140-2017-AccompanyingFiles\DRYCOLD.epw"

weather_data_sia = dp.epw_to_sia_irrad(weatherfile_path)
occupancy_path = r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator\auxiliary\occupancy_office.csv"

## Erforderliche Nutzereingaben:
gebaeudekategorie_sia = 1.1
regelung = "andere"  # oder "Referenzraum" oder "andere"
hohe_uber_meer = 435.0 # Eingabe
energiebezugsflache = 48.0  # m2
anlagennutzungsgrad_wrg = 0.0 ## SIA 380-1 Tab 23
warmespeicherfahigkeit_pro_EBF = 0.08 ## Wert noch nicht klar, bestimmen gemäss SN EN ISO 13786 oder Tab25 Einheiten?
korrekturfaktor_luftungs_eff_f_v = 1.0  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24
infiltration_volume_flow = 1.35  # Gemäss SIA 380-1 2016 3.5.5 soll 0.15m3/(hm2) verwendet werden. Korrigenda anschauen
ventilation_volume_flow = 0.0 # give a number in m3/(hm2) or select "SIA" to follow SIA380-1 code
heating_setpoint = "SIA"  # give a number in deC or select "SIA" to follow the SIA380-1 code
cooling_setpoint = "SIA" # give a number in deC or select "SIA" to follow the SIA380-1 code
area_per_person = "SIA"  # give a number or select "SIA" to follow the SIA380-1 code (typical for MFH 40)


## Gebäudehülle
u_windows = 3.0
g_windows = 0.5
u_walls = 0.514
u_roof = 0.318
u_floor = 0.039
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
pv_area = 0  # m2, can be directly linked with roof size
pv_tilt = 30  # in degrees
pv_azimuth = 180  # The north=0 convention applies


## Bauteile:
# Windows: [[Orientation],[Areas],[U-value],[g-value]]
windows = np.array([["S"],
                    [12.0],
                    [u_windows],
                    [g_windows]],
                   dtype=object)  # dtype=object is necessary because there are different data types

# walls: [[Areas], [U-values]] zuvor waren es 4 x 412.5
walls = np.array([[21.6, 21.6, 16.2, 16.2],
                  [u_walls, u_walls, u_walls, u_walls]])


# roof: [[Areas], [U-values]]
roof = np.array([[48.0], [u_roof]])

# floor to ground (for now) [[Areas],[U-values],[b-values]]
floor = np.array([[48],[u_floor],[b_floor]])


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

print("heating")
print(Gebaeude_static.heizwarmebedarf.sum())

print("cooling")
print(Gebaeude_static.monthly_cooling_demand.sum())



Gebaeude_static.run_SIA_electricity_demand(occupancy_path)

Gebaeude_static.run_SIA_380_emissions(emission_factor_type="SIA_380", avg_ashp_cop=2.8)

print("operational emissions static")
print(Gebaeude_static.operational_emissions.sum())  # CO2eq/m2a

# print(Gebaeude_static.non_renewable_primary_energy.sum())  # kWh/m2a


Gebaeude_dyn = sime.Sim_Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor, energiebezugsflache,
                               anlagennutzungsgrad_wrg, infiltration_volume_flow, ventilation_volume_flow,
                               warmespeicherfahigkeit_pro_EBF,
                               korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer, heizsystem, cooling_system,
                               dhw_heizsystem, heating_setpoint, cooling_setpoint, area_per_person)

Gebaeude_dyn.pv_production = pv_yield_hourly

Gebaeude_dyn.run_rc_simulation(weatherfile_path=weatherfile_path,
                             occupancy_path=occupancy_path)


print("Heating")
print((dp.hourly_to_monthly(Gebaeude_dyn.heating_demand) / 1000.0 / energiebezugsflache).sum())
# print("DHW")
# print(dp.hourly_to_monthly(Gebaeude_dyn.dhw_demand)/1000.0 / energiebezugsflache)
print("cooling")
print(dp.hourly_to_monthly((Gebaeude_dyn.cooling_demand)/ 1000.0 / energiebezugsflache).sum())

Gebaeude_dyn.run_SIA_electricity_demand(occupancy_path)
Gebaeude_dyn.run_dynamic_emissions("SIA_380", "c")
#
print("operational emissions dynamic")
print(Gebaeude_dyn.operational_emissions.sum() / energiebezugsflache)
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



"""
###################################### EMBODIED EMISSIONS ##############################################################
In this part the embodied emissions of a respective system and its components are defined.

"""

