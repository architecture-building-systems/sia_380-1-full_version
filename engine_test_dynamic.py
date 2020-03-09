import unittest
import numpy as np
import simulation_engine_dynamic as sime


# class MyTestCase(unittest.TestCase):
#     def test_something(self):
#         self.assertEqual(True, False)

class TestRCRun(unittest.TestCase):
    def test_demand_calculations(self):
        ### Pfade zu weiteren Daten
        weatherfile_path = r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator\auxiliary\Zurich-Kloten_2013.epw"
        occupancy_path = r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator\auxiliary\occupancy_office.csv"

        ### Erforderliche Nutzereingaben:
        gebaeudekategorie_sia = 1.1
        regelung = "andere"  # oder "Referenzraum" oder "andere"
        hohe_uber_meer = 435.0  # Eingabe
        energiebezugsflache = 2275.0  # m2
        anlagennutzungsgrad_wrg = 0.0  ## SIA 380-1 Tab 23
        warmespeicherfahigkeit_pro_EBF = 0.08  ## gemäss SN EN ISO 13786 oder Tab25 [kWh/m2K]
        korrekturfaktor_luftungs_eff_f_v = 1.0  # zwischen 0.8 und 1.2 gemäss SIA380-1 Tab 24
        infiltration_volume_flow = 0.15  # Gemäss SIA 380-1 2016 3.5.5 soll 0.15m3/(hm2) verwendet werden. Korrigenda anschauen
        cooling_setpoint = 27  # deg C

        ## Gebäudehülle
        u_windows = 1.30
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
        cooling_system = "electric"
        dhw_heizsystem = heizsystem  ## This is currently a limitation of the RC Model. Automatically the same!

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
        floor = np.array([[506.0], [u_floor], [b_floor]])

        Gebaeude_1 = sime.Sim_Building(gebaeudekategorie_sia, regelung, windows, walls, roof, floor,
                                       energiebezugsflache,
                                       anlagennutzungsgrad_wrg, infiltration_volume_flow,
                                       warmespeicherfahigkeit_pro_EBF,
                                       korrekturfaktor_luftungs_eff_f_v, hohe_uber_meer, heizsystem, cooling_system,
                                       dhw_heizsystem)

        Gebaeude_1.run_rc_simulation(weatherfile_path=weatherfile_path,
                                     occupancy_path=occupancy_path, cooling_setpoint=cooling_setpoint)

        self.assertAlmostEqual(25.3, np.round(Gebaeude_1.heating_demand.sum()/1000.0/energiebezugsflache,1))
        self.assertAlmostEqual(19.8, np.round(Gebaeude_1.dhw_demand.sum() / 1000.0 / energiebezugsflache, 1))
        self.assertAlmostEqual(-30.2, np.round(Gebaeude_1.cooling_demand.sum() / 1000.0 / energiebezugsflache, 1))



if __name__ == '__main__':
    unittest.main()
