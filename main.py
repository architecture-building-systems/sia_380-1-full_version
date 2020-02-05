import numpy as np
import matplotlib.pyplot as plt
import simulation_engine as se

### Erforderliche Nutzereingaben:
gebaeudekategorie_sia = 1.1
regelung = "andere"  # oder "Referenzraum" oder "andere"
hohe_uber_meer = 435.0 # Eingabe
energiebezugsflache = 2275.0  # m2
anlagennutzungsgrad_wrg = 0.0 ## SIA 380-1 Tab 23
warmespeicherfahigkeit_pro_EBF = 0.08 ## Wert noch nicht klar, bestimmen gemäss SN EN ISO 13786 oder Tab25
korrekturfaktor_luftungs_eff_f_v = 1.0  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24


## Gebäudehülle
u_windows = 0.6
u_walls = 0.08
u_roof = 0.06
u_floor = 0.09
b_floor = 0.4


## Systeme
heizsystem = "GSHP_CH_mix"
dhw_heizsystem = "GSHP_CH_mix"




### Bauteile:
## Windows: [[Orientation],[Areas],[U-value],[g-value]]
windows = np.array([["N", "E", "S", "W"],
                    [131.5, 131.5, 131.5, 131.5],
                    [u_windows, u_windows, u_windows, u_windows],
                    [0.6, 0.6, 0.6, 0.6]],
                   dtype=object)  # dtype=object is necessary because there are different data types

## walls: [[Areas], [U-values]]
walls = np.array([[412.5, 412.5, 412.5, 412.5],
                  [u_walls, u_walls, u_walls, u_walls]])

## roof: [[Areas], [U-values]]
roof = np.array([[506.0], [u_roof]])

## floor to ground (for now) [[Areas],[U-values],[b-values]]
floor = np.array([[506.0],[u_floor],[b_floor]])


Gebaeude_1 = se.Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor, energiebezugsflache,
                         anlagennutzungsgrad_wrg, warmespeicherfahigkeit_pro_EBF, korrekturfaktor_luftungs_eff_f_v,
                         hohe_uber_meer)

Gebaeude_1.run_SIA_380_1()
print(Gebaeude_1.heizwarmebedarf.sum())  #kWh/m2a



## Gebäudedimensionen
Gebaeude_1.heating_system = heizsystem
Gebaeude_1.electricity_mix = dhw_heizsystem
Gebaeude_1.dhw_heating_system = "GSHP_CH_mix"  ## Achtung, momentan ist der COP für DHW und für Heizung gleich.


Gebaeude_1.run_SIA_380_emissions()
print(Gebaeude_1.emissions.sum())  # CO2eq/m2a
print(Gebaeude_1.non_renewable_primary_energy.sum())  # kWh/m2a

quit()
##### Plots:

# plt.plot(transmissionsverluste, label="Transmissionswärmeverluste")
# plt.plot(luftungsverluste, label="Lüftungsverlust")
plt.plot(gesamtwarmeverluste, label="Gesamtwärmeverluste")
# plt.plot(interne_eintrage, label="Interne Wärmegewinne")
# plt.plot(solare_eintrage, label="Solare Wärmegewinne")
plt.plot(totale_warmeeintrage, label="Totale Wärmegewinne")
# plt.plot(genutzte_warmeeintrage, label="Genutzte Wärmegewinne")
plt.plot(heizwarmebedarf, label="Heizwärmebedarf")
plt.legend()
plt.ylabel("kWh/(m2a)")
plt.title("SIA 380-1 monatliche Bilanz")
plt.show()

print("Annual Heizwärmebedarf", sum(heizwarmebedarf))
