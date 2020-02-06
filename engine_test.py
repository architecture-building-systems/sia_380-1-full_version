import unittest
import numpy as np
import simulation_engine as se


class TestBuildingInitialization(unittest.TestCase):
    def test_initialization(self):
        """

        :return:
        """
        u_windows = 0.6
        u_walls = 0.08
        u_roof = 0.06
        u_floor = 0.09
        b_floor = 0.4

        gebaeudekategorie_sia = 1.1
        regelung = "einzelraum"
        windows = np.array([["N", "E", "S", "W"],
                            [131.5, 131.5, 131.5, 131.5],
                            [u_windows, u_windows, u_windows, u_windows],
                            [0.6, 0.6, 0.6, 0.6]],
                           dtype=object)  # dtype=object is necessary because there are different data types
        walls = np.array([[412.5, 412.5, 412.5, 412.5],
                          [u_walls, u_walls, u_walls, u_walls]])
        roof = np.array([[506], [u_roof]])
        floor = np.array([[506.0], [u_floor], [b_floor]])
        energy_reference_area = 2275
        heat_recovery_nutzungsgrad = 0.0
        thermal_storage_capacity_per_floor_area = 0.08
        korrekturfaktor_luftungs_eff_f_v = 1.0
        height_above_sea = 435.0
        infiltration_volume_flow = 0

        Test_building = se.Building(gebaeudekategorie_sia,
                                    regelung,
                                    windows,
                                    walls,
                                    roof,
                                    floor,
                                    energy_reference_area,
                                    heat_recovery_nutzungsgrad,
                                    infiltration_volume_flow,
                                    thermal_storage_capacity_per_floor_area,
                                    korrekturfaktor_luftungs_eff_f_v,
                                    height_above_sea)

        self.assertEqual(gebaeudekategorie_sia, Test_building.gebaeudekategorie_sia)
        self.assertEqual("einzelraum", Test_building.regelung)
        self.assertEqual(435.0, Test_building.hohe_uber_meer)
        self.assertEqual(2275, Test_building.energy_reference_area)
        self.assertEqual(0.6, Test_building.windows[2][0])
        self.assertEqual(0.08, Test_building.walls[1][0])
        self.assertEqual(0.06, Test_building.roof[1][0])
        self.assertEqual(0.09, Test_building.floor[1][0])
        self.assertEqual(0.4, Test_building.floor[2][0])
        self.assertEqual(0.0, Test_building.anlagennutzungsgrad_wrg)


class TestSia380_1(unittest.TestCase):
    def test_heating_demand(self):
        """
        This test runs comparisons to calculations made with the SIA380-1 2016 Excel tool for the given inputs.
        A more complex test with additional inputs and more complex "Bauteile" such as thermal bridges needs
        to be implemented later.
        :return:
        """
        u_windows = 0.6
        u_walls = 0.08
        u_roof = 0.06
        u_floor = 0.09
        b_floor = 0.4

        gebaeudekategorie_sia =1
        regelung = "andere"
        windows = np.array([["N", "E", "S", "W"],
                            [131.5, 131.5, 131.5, 131.5],
                            [u_windows, u_windows, u_windows, u_windows],
                            [0.6, 0.6, 0.6, 0.6]],
                            dtype=object)  # dtype=object is necessary because there are different data types
        walls = np.array([[412.5, 412.5, 412.5, 412.5],
                          [u_walls, u_walls, u_walls, u_walls]])
        roof = np.array([[506], [u_roof]])
        floor = np.array([[506.0],[u_floor],[b_floor]])
        energy_reference_area = 2275
        heat_recovery_nutzungsgrad = 0.0
        thermal_storage_capacity_per_floor_area = 0.08
        korrekturfaktor_luftungs_eff_f_v = 1.0
        height_above_sea = 435.0
        infiltration_volume_flow = 0.0

        Test_building = se.Building(gebaeudekategorie_sia,
                 regelung,
                 windows,
                 walls,
                 roof,
                 floor,
                 energy_reference_area,
                 heat_recovery_nutzungsgrad,
                 infiltration_volume_flow,
                 thermal_storage_capacity_per_floor_area,
                 korrekturfaktor_luftungs_eff_f_v,
                 height_above_sea)

        Test_building.run_SIA_380_1()

        self.assertAlmostEqual(np.sum(Test_building.heizwarmebedarf), 5.5, places=1,
                               msg="Heizwärmebedarfsberechnung stimmt nicht mit simpler Berechnung gemäss der SIA380-1 Excel Tabelle überein")
        self.assertAlmostEqual(np.sum(Test_building.solare_eintrage), 73.4, places=1,
                               msg="Solareinträge stimmt nicht mit simpler Berechnung gemäss der SIA380-1 Excel Tabelle überein")
        self.assertAlmostEqual(np.sum(Test_building.transmissionsverluste), 24.1, places=1,
                               msg="Transmissionswärmeverluste stimmen nicht mit simpler Berechnung gemäss der SIA380-1 Excel Tabelle überein")
        self.assertAlmostEqual(np.sum(Test_building.luftungsverlust), 24.9, places=1,
                               msg="Lüftungswärmeverluste stimmen nicht mit simpler Berechnung gemäss der SIA380-1 Excel Tabelle überein")
        self.assertAlmostEqual(np.sum(Test_building.genutzte_warmeeintrage), 43.4, places=1,
                               msg="Genutzter Wärmeeintrag stimmt nicht mit simpler Berechnung gemäss der SIA380-1 Excel Tabelle überein")

    def test_window_irradiation(self):
        """
        Testing the solar irradiation vector calculation based on two hand calculations
        :return:
        """
        windows = np.array([["SW", "NE"] , [None, None], [None, None], [None, None]], dtype=object) # U-values are not important
        horizontal_irradiance = 100.0
        north_irradiance = 25.0
        east_irradiance = 36.0
        south_irradiance = 81.0
        west_irradiance = 49.0

        irradiance_vector = se.window_irradiation(windows, horizontal_irradiance, south_irradiance, east_irradiance,
                              west_irradiance, north_irradiance)

        self.assertAlmostEqual(63.0, irradiance_vector[0], places=5, msg="creating the irradiation vector does not seem to work anymore")
        self.assertAlmostEqual(30.0, irradiance_vector[1], places=5, msg="creating the irradiation vector does not seem to work anymore")
        ## There would be a nicer way to do this with numpy testing





if __name__ == '__main__':
    unittest.main()
