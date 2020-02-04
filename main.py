import numpy as np
import matplotlib.pyplot as plt
import simulation_engine as se

### Erforderliche Nutzereingaben:
gebaeudekategorie_sia = 1
regelung = "andere"  # oder "Referenzraum" oder "andere"
hohe_uber_meer = 450.0 # Eingabe
energiebezugsflache = 2275  # m2

anlagennutzungsgrad_wrg = 0.0 ## SIA 380-1 Tab 23

warmespeicherfahigkeit_pro_EBF = 0.08 ## Wert noch nicht klar, bestimmen gemäss SN EN ISO 13786 oder Tab25
korrekturfaktor_luftungs_eff_f_v = 1.0  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24

## Windows: [[Orientation],[Areas],[U-value],[g-value]]
windows = np.array([["N", "E", "S", "W"], [131.5, 131.5, 131.5, 131.5], [0.6, 0.6, 0.6, 0.6], [0.6, 0.6, 0.6, 0.6]],
                   dtype=object)  # dtype=object is necessary because there are different data types

## walls: [[Areas], [U-values]]
walls = np.array([[412.5, 412.5, 412.5, 412.5],[0.08, 0.08, 0.08, 0.08]])

## roof: [[Areas], [U-values]]
roof = np.array([[506], [0.06]])



Gebaeude_1 = se.Building(gebaeudekategorie_sia, regelung, windows, walls, roof, energiebezugsflache,
                         anlagennutzungsgrad_wrg, warmespeicherfahigkeit_pro_EBF, korrekturfaktor_luftungs_eff_f_v,
                         hohe_uber_meer)

Gebaeude_1.run_SIA_380_1()
print(Gebaeude_1.heizwarmebedarf.sum())
## Gebäudedimensionen

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
