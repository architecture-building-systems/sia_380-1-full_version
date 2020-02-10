import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import plotly.graph_objects as go

import simulation_engine as se

from SALib.sample import saltelli
from SALib.analyze import sobol


### Erforderliche Nutzereingaben:
gebaeudekategorie_sia = 1.1
regelung = "andere"  # oder "Referenzraum" oder "andere"
hohe_uber_meer = 435.0 # Eingabe
energiebezugsflache = 2275.0  # m2
# anlagennutzungsgrad_wrg = 0.0 ## SIA 380-1 Tab 23
# warmespeicherfahigkeit_pro_EBF = 0.08 ## Wert noch nicht klar, bestimmen gemäss SN EN ISO 13786 oder Tab25
# korrekturfaktor_luftungs_eff_f_v = 1.0  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24
infiltration_volume_flow = 0.15  # Gemäss SIA 380-1 2016 3.5.5 soll 0.15m3/(hm2) verwendet werden. Korrigenda anschauen





### Generate Samples
problem = {
    'num_vars':10,
    'names':['u_walls', 'u_windows', 'g_windows', 'u_floor', 'b_floor', 'u_roof', 'thermal_mass', 'f_v', 'eta_g', 'infiltration_volume_flow'],
    'bounds':[[0.12, 0.4],  # u_walls
              [0.75, 1.3],  # u_windows
              [0.3, 0.6],  # g_windows
              [0.08, 0.25],  # u_floor
              [0.1, 1.0],  # b_floor
              [0.08, 0.25],  # u_roof
              [0.03, 0.15],  # waermespeicherfaehigkeit pro EBF
              [0.8, 1.2],  # f_v
              [0.0, 0.70],  # eta g, heat recovery efficiency
              [0.05, 0.25]  # infiltration volume flow
              ]}
param_values = saltelli.sample(problem, 500)


### Run Model

Y = np.zeros([param_values.shape[0]])
for i, X in enumerate(param_values):

    # print(i)  # Take this out for long simulations as it takes a lot of time. Otherwise, this is an indicator on the
              # progress of the simulation.

    u_walls = X[0]
    u_windows = X[1]
    g_windows = X[2]
    u_floor = X[3]
    b_floor = X[4]
    u_roof = X[5]
    warmespeicherfahigkeit_pro_EBF = X[6]
    korrekturfaktor_luftungs_eff_f_v = X[7]  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24
    anlagennutzungsgrad_wrg = X[8]
    infiltration_volume_flow = X[9]


    ## Systeme
    heizsystem = "HP"
    dhw_heizsystem = "HP"


    ### Bauteile:
    ## Windows: [[Orientation],[Areas],[U-value],[g-value]]
    windows = np.array([["N", "E", "S", "W"],
                        [131.5, 131.5, 131.5, 131.5],
                        [u_windows, u_windows, u_windows, u_windows],
                        [g_windows, g_windows, g_windows, g_windows]],
                       dtype=object)  # dtype=object is necessary because there are different data types

    ## walls: [[Areas], [U-values]]
    walls = np.array([[412.5, 412.5, 412.5, 412.5],
                      [u_walls, u_walls, u_walls, u_walls]])

    ## roof: [[Areas], [U-values]]
    roof = np.array([[506.0], [u_roof]])

    ## floor to ground (for now) [[Areas],[U-values],[b-values]]
    floor = np.array([[506.0],[u_floor],[b_floor]])






    Gebaeude_1 = se.Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor, energiebezugsflache,
                             anlagennutzungsgrad_wrg, infiltration_volume_flow, warmespeicherfahigkeit_pro_EBF,
                             korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer)



    Gebaeude_1.run_SIA_380_1()

    Y[i] = Gebaeude_1.heizwarmebedarf.sum()  #kWh/m2a

print("sobol analysis...")
Si = sobol.analyze(problem, Y)  #, parallel=True, n_processors=6 )

print(Si['S1'])
print(Si['S2'])
print(Si['ST'])

# print("x1-x2:", Si['S2'][0,1])
# print("x1-x3:", Si['S2'][0,2])
# print("x2-x3:", Si['S2'][1,2])
#


plt.bar(problem['names'], Si['ST'])
plt.show()

plt.pcolormesh(Si['S2'], cmap='binary')
plt.colorbar()
plt.xticks(np.arange(0.5,11.5,1.0), problem['names'])
plt.yticks(np.arange(0.5,11.5,1.0), problem['names'])
plt.show()

quit()
