import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import plotly.graph_objects as go

import simulation_engine as se
import simulation_engine_dynamic as sime

from SALib.sample import saltelli
from SALib.analyze import sobol


if __name__=='__main__':

    ### Erforderliche Nutzereingaben:
    gebaeudekategorie_sia = 1.1
    regelung = "andere"  # oder "Referenzraum" oder "andere"
    hohe_uber_meer = 435.0 # Eingabe
    energiebezugsflache = 2275.0  # m2
    # anlagennutzungsgrad_wrg = 0.0 ## SIA 380-1 Tab 23
    # warmespeicherfahigkeit_pro_EBF = 0.08 ## Wert noch nicht klar, bestimmen gemäss SN EN ISO 13786 oder Tab25
    # korrekturfaktor_luftungs_eff_f_v = 1.0  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24
    # infiltration_volume_flow = 0.15  # Gemäss SIA 380-1 2016 3.5.5 soll 0.15m3/(hm2) verwendet werden. Korrigenda anschauen





    ### Generate Samples
    problem = {
        'num_vars':11,
        'names':['u_walls', 'u_windows', 'g_windows', 'u_floor', 'b_floor', 'u_roof', 'thermal_mass', 'f_v', 'eta_g',
                 'infiltration_flow', 'heating system'],
        'bounds':[[0.12, 0.4],  # u_walls
                  [0.75, 1.3],  # u_windows
                  [0.3, 0.6],  # g_windows
                  [0.08, 0.25],  # u_floor
                  [0.1, 1.0],  # b_floor
                  [0.08, 0.25],  # u_roof
                  [0.03, 0.15],  # waermespeicherfaehigkeit pro EBF
                  [0.8, 1.2],  # f_v
                  [0.0, 0.70],  # eta g, heat recovery efficiency
                  [0.05, 0.25],  # infiltration volume flow
                  [0.5, 5.5]]}   # Heating system ## Abklären, ob dies so gemacht werden kann für diskretisierte Variablen.
    # "Natural Gas":0.249, "Wood":0.020, "Pellets":0.048, "GSHP_CH_mix":0.055, "ASHP_CH_mix":0.076, "GSHP_EU_mix":0.207, "ASHP_EU_mix":0.285
    param_values = saltelli.sample(problem, 300)


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

        heating_system_number = np.round(X[10], 0)
        number_to_system = {1:"Natural Gas", 2:"Wood", 3:"Pellets", 4:"GSHP", 5:"ASHP"}
        ## Systeme

        heizsystem = number_to_system[heating_system_number]
        dhw_heizsystem = number_to_system[heating_system_number]


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

        Gebaeude_1.heating_system = heizsystem
        Gebaeude_1.dhw_heating_system = dhw_heizsystem



        Gebaeude_1.run_SIA_380_1()
        Gebaeude_1.run_dhw_demand()
        Gebaeude_1.run_SIA_380_emissions(emission_factor_type="SIA_380", avg_ashp_cop=2.8)

        # Y[i] = Gebaeude_1.heizwarmebedarf.sum()  #kWh/m2a
        Y[i] = Gebaeude_1.heating_emissions.sum()

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
    plt.show()

    plt.pcolormesh(Si['S2'], cmap='binary')
    plt.colorbar()
    plt.xticks(np.arange(0.5,12.5,1.0), problem['names'])
    plt.yticks(np.arange(0.5,12.5,1.0), problem['names'])
    plt.show()


