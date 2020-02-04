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

## Gebäudedimensionen

transmissionsverluste, luftungsverluste, \
gesamtwarmeverluste, interne_eintrage,\
solare_eintrage, totale_warmeeintrage,\
genutzte_warmeeintrage, heizwarmebedarf = se.run_SIA_380_1(gebaeudekategorie_sia, regelung, hohe_uber_meer,
                                                           energiebezugsflache, anlagennutzungsgrad_wrg,
                                                           warmespeicherfahigkeit_pro_EBF,
                                                           korrekturfaktor_luftungs_eff_f_v)







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
