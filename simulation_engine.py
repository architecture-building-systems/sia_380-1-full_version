import numpy as np
import pandas as pd
import data_prep as dp
import matplotlib.pyplot as plt

class Building(object):

    def __init__(self,
                 gebaeudekategorie_sia,
                 regelung,
                 windows,
                 walls,
                 roof,
                 floor,
                 energy_reference_area,
                 heat_recovery_nutzungsgrad,
                 infiltration_volume_flow,
                 ventilation_volume_flow,
                 thermal_storage_capacity_per_floor_area,
                 korrekturfaktor_luftungs_eff_f_v,
                 height_above_sea,
                 heating_setpoint="SIA",
                 cooling_setpoint="SIA",
                 area_per_person="SIA"):

        self.gebaeudekategorie_sia = gebaeudekategorie_sia
        self.regelung = regelung
        self.windows = windows  # np.array of windows with |area|u-value|g-value|orientation|shading_f1|shading_f2|
        self.walls = walls  # np.array of walls with |area|u-value| so far, b-values are not possible
        self.roof = roof  # np.array of roofs with |area|u-value|
        self.floor = floor  # np.array of floowrs with |area|u-value|b-value|
        self.energy_reference_area = energy_reference_area  # One value, float
        self.anlagennutzungsgrad_wrg = heat_recovery_nutzungsgrad  # One value, float
        self.q_inf = infiltration_volume_flow
        self.ventilation_volume_flow = ventilation_volume_flow
        self.warmespeicherfahigkeit_pro_ebf = thermal_storage_capacity_per_floor_area # One value, float
        self.korrekturfaktor_luftungs_eff_f_v = korrekturfaktor_luftungs_eff_f_v
        self.hohe_uber_meer = height_above_sea
        self.heating_setpoint= heating_setpoint
        self.cooling_setpoint= cooling_setpoint
        self.area_per_person= area_per_person


        # Further optional attributes:
        self.heating_system = None
        self.cooling_system = None
        self.electricity_demand = None
        self.electricity_mix = None
        self.dhw_demand = None  # np.array of monthly values per energy reference area [kWh/(m2*month)]
        self.dhw_heating_system = None
        self.pv_production = None  # This input is currently implemented as Wh (!)


    def run_SIA_380_1(self, weather_data_sia):

        ## Standardnutzungswerte

        regelzuschlaege = dp.sia_standardnutzungsdaten('regelzuschaege')
        warmeabgabe_p_p = dp.sia_standardnutzungsdaten('gain_per_person')
        prasenzzeiten = dp.sia_standardnutzungsdaten('presence_time')
        # this part of elektrizitatsbedarf only goes into thermal calculations. Electricity demand is calculated
        # independently.
        elektrizitatsbedarf = dp.sia_standardnutzungsdaten('gains_from_electrical_appliances')
        reduktion_elektrizitat = dp.sia_standardnutzungsdaten('reduction_factor_for_electricity')

        if self.ventilation_volume_flow == "SIA":
            aussenluft_strome = dp.sia_standardnutzungsdaten('effective_air_flow')
        else:
            aussenluft_strome = {int(self.gebaeudekategorie_sia):self.ventilation_volume_flow+self.q_inf}

        if self.heating_setpoint == "SIA":
            standard_raumtemperaturen = dp.sia_standardnutzungsdaten('room_temperature_heating')
        else:
            standard_raumtemperaturen = {int(self.gebaeudekategorie_sia):self.heating_setpoint}

        if self.area_per_person == "SIA":
            personenflachen = dp.sia_standardnutzungsdaten('area_per_person')
        else:
            personenflachen = {int(self.gebaeudekategorie_sia):self.area_per_person}


        ## Klimadaten für verschiedene Ausrichtungen
        mj_to_kwh_factor = 1.0/3.6
        globalstrahlung_horizontal_monatlich = weather_data_sia['global_horizontal'] * mj_to_kwh_factor  # kWh/m2
        globalstrahlung_ost_monatlich = weather_data_sia['global_east'] * mj_to_kwh_factor  # kWh/m2
        globalstrahlung_sud_monatlich = weather_data_sia['global_south'] * mj_to_kwh_factor  # kWh/m2
        globalstrahlung_west_monatlich = weather_data_sia['global_west'] * mj_to_kwh_factor  # kWh/m2
        globalstrahlung_nord_monatlich = weather_data_sia['global_north'] * mj_to_kwh_factor # kWh/m2
        temperatur_mittelwert = weather_data_sia['temperature']  # degC

        t_c = [31,28,31,30,31,30,31,31,30,31,30,31]  # Tage pro Monat.

        theta_i_001 = standard_raumtemperaturen[int(self.gebaeudekategorie_sia)] # Raumtemperatur in °C Gemäss SIA380-1 2016 Tab7 (grundsätzlich 20°C)
        delta_phi_i_002 = regelzuschlaege[self.regelung] # Regelungszuschlag für die Raumtemperatur [K] gemäss SIA380-1 2016 Tab8
        a_p_003 = personenflachen[int(self.gebaeudekategorie_sia)]  # Personenfläche m2/P
        q_p_004 = warmeabgabe_p_p[int(self.gebaeudekategorie_sia)] # Wärmeabgabe pro Person W/P
        t_p_005 = prasenzzeiten[int(self.gebaeudekategorie_sia)]  # Präsenzzeit pro Tag h/d
        e_f_el_006 = elektrizitatsbedarf[int(self.gebaeudekategorie_sia)]  # Elektrizitätsbedarf pro Jahr kWh/m2
        f_el_007 = reduktion_elektrizitat[int(self.gebaeudekategorie_sia)]  # Reduktionsfaktor Elektrizität [-]

        eta_v_081 = self.anlagennutzungsgrad_wrg  # anlagennutzungsgrad der wärmerückgewinnung [-]
        f_v_082 = self.korrekturfaktor_luftungs_eff_f_v  # Korrekturfaktor für die Lüftungseffektivität [-]

        q_th_008 = ((aussenluft_strome[int(self.gebaeudekategorie_sia)]-self.q_inf)*(1-eta_v_081)/f_v_082) + self.q_inf
        # thermisch wirksamer Aussenluftvolumenstrom gem 3.5.5 m3/(hm2)

        h_010 = self.hohe_uber_meer  # Höhge über Meer [m]

        transmissionsverluste = np.empty(12)
        luftungsverluste = np.empty(12)
        gesamtwarmeverluste = np.empty(12)
        interne_eintrage = np.empty(12)
        solare_eintrage = np.empty(12)
        totale_warmeeintrage = np.empty(12)
        genutzte_warmeeintrage = np.empty(12)
        heizwarmebedarf = np.empty(12)


        ## Berchnung nach SIA380-1 Anhang D

        for month in range(12):
            t_c_009 = t_c[month]  # Länge Berechnungsschritt [d]
            theta_e_011 = temperatur_mittelwert[month] # Aussenlufttemperatur [degC]
            g_sh_012 = globalstrahlung_horizontal_monatlich[month]  # globale Sonnenstrahlung horizontal [kWh/m2]
            g_ss_013 = globalstrahlung_sud_monatlich[month]  # hemisphärische Sonnenstrahlung Süd [kWh/m2]
            g_se_014 = globalstrahlung_ost_monatlich[month]  # hemisphärische Sonnenstrahlung Ost [kWh/m2]
            g_sw_015 = globalstrahlung_west_monatlich[month] # hemisphärische Sonnenstrahlung West [kWh/m2]
            g_sn_016 = globalstrahlung_nord_monatlich[month]  # hemisphärische Sonnenstrahlung Nord [kWh/m2]

            g_s_windows = window_irradiation(self.windows, g_sh_012, g_ss_013, g_se_014, g_sw_015, g_sn_016)

            # Flächen, Längen und Anzahl
            # Es gibt hier viele Nullen, die könnten später nützlich werden, falls der Code erweitert werden soll.
            a_e_017 = self.energy_reference_area  # Energiebezugsfläche [m2]
            a_re_018 = self.roof[0]  # Dach gegen Aussenluft [m2]
            a_ru_019 = np.array([0])  # Decke gegen unbeheizte Räume [m2]
            a_we_020 = self.walls[0]  # Wand gegen Aussenluft [m2]
            a_wu_021 = np.array([0])  # Wand gegen unbeheizte Räume [m2]
            a_wg_022 = np.array([0]) # Wand gegen Erdreich [m2]
            a_wn_023 = np.array([0])  # Wand gegen benachbarten beheizten Raum im Bilanzperimeter [m2]
            a_fe_024 = np.array([0])  # Boden gegen Aussenluft [m2]
            a_fu_025 = self.floor[0]  # Boden gegen unbeheizte Räume [m2]
            a_fg_026 = np.array([0])  # Boden gegen Erdreich mit Bauteilheizung [m2]
            a_fu_027 = np.array([0])  # Boden gegen unbeheizte Räume mit Bauteilheizung[m2]
            a_fn_028 = np.array([0])  # Boden gegen beheizte Räume mit Bauteilheizung im Bilanzperimeter [m2]
            a_rn_029 = np.array([0])  # Decke gegen beheizte Räume mit Bauteilheizung im Bilanzparameter [m2]
            a_wh_030 = np.array([0])  # Fenster horizontal [m2]

            i_rw_035 = np.array([0.]) # Wärmebrücke Decke/Wand [m]
            i_wf_036 = np.array([0.])  # Wärmebrücke Gebäudesockel [m]
            i_b_037 = np.array([0.])  # Wärmebrücke Balkon [m]
            i_w_038 = np.array([0.])  # Wärmebrücke Fensteranschlag  [m]
            i_f_039 = np.array([0.])  # Wärmebrücke Boden/Keller-Innenwand [m]
            z_040 = np.array([0.]) # Wärmebrücke Stützen, Träger, Konsolen [-]

            ### Diverses / Thermische Angaben
            u_re_041 = self.roof[1]  # Dach gegen Aussenluft [W/(m2K)]
            u_ru_042 = np.array([0]) # Decke gegen unbeheizte Räume  [W/(m2K)]
            b_ur_043 = np.array([0])  # Reduktionsfaktor Decke gegen unbeheizte Räume [-]
            u_we_044 = self.walls[1]  # Wand gegen Aussenluft  [W/(m2K)]
            u_wu_045 = np.array([0])  # Wand gegen unbeheizte Räume  [W/(m2K)]
            b_uw_046 = np.array([0])  # Reduktionsfaktor Wand gegen unbeheizte Räume [-]
            u_wg0_047 = np.array([0])  # Wand gegen Erdreich  [W/(m2K)]
            b_gw_048 = np.array([0])  # Reduktionsfaktro Wand gegen Erdreich [-]
            u_wn_049 = np.array([0])  # Wand gegen benachbarten konditionierten Raum im Bilanzperimeter [W/(m2K)]
            theta_in_050 = np.array([0])  # korrigierte Raumtemperatur des benachbarten konditionierten Raumes [degC]
            u_fe_051 = np.array([0])  # Boden gegen Aussenluft [W/(m2K)]
            u_fu_052 = self.floor[1]  # Boden gegen unbeheizte Räume [W/(m2K)]
            u_fu_053 = np.array([0])  # Boden gegen unbeheizte Räume mit Bauteilheizung [W/(m2K)]
            b_uf_054 = self.floor[2]  # Reduktionsfaktor Boden gegen unbeheizte Räume [-]
            u_fg0_055 = np.array([0])  # Boden gegen Erdreich mit Bauteilheizung [W/(m2K)]
            b_gf_056 = np.array([0])  # Reduktionsfaktro Boden gegen Erdreich [-]
            u_fn_057 = np.array([0])  # Boden gegen beheizte Räume mit Bauteilheizung [W/(m2K)]
            u_rn_058 = np.array([0])  # Decke gegen beheizte Räume mit Bauteilheizung [W/(m2K)]
            delta_theta_059 = 0.0  # Temperaturzuschlag für Bauteilheizung [K], dies anpassen nach Tab16 SIA380-1 3.5.4.5
            u_wh_060 = np.array([0])  # Fenster horizontal [W/(m2K)]

            psi_rw_065 = np.array([0])  # Wärmebrücke Decke/Wand [W/(mK)]
            psi_wf_066 = np.array([0])  # Wärmebrücke Fensteranschlag [W/(mK)]
            psi_b_067 = np.array([0])  # Wärmebrücke Balkon [W/(mK)]
            psi_w_068 = np.array([0])  # Wärmebrücke Fensteranschlag [W/(mK)]
            psi_f_069 = np.array([0])  # Wärmebrücken Boden/Keller-Innenwand [W/(mK)]
            chi_070 = np.array([0])  # Wärmebrückeen Stützen, Träger, Konsolen [W/K]
            g_071 = 0.6  # Gesamtenergiedurchlassgrad Fenster [-], anpassen: momentan gibt es nur einen g-Wert für alle Fenster
            ## Dies muss insbesondere angeschaut werden, da die Fenster ansonsten pro Himmelsrichtung getrennt sind. Dies sollte
            ## bei zusätzlicher Vektorisierung aufgehoben werden.
            ## Gleiches gilt für die unten angegebenen Verschattungsfaktoren!
            f_f_072 = 0.95# Abminderungsfaktor für Fensterrahmen [-] Ebenfalls im Hardcode bei cooling nach ISO52016-1
            f_sh_073 = 1.0  # Verschattungsfaktor horizontal [-]

            ### spezielle Eingabedaten
            cr_ae_078 = self.warmespeicherfahigkeit_pro_ebf  # Wärmespeicherfähigkeit pro EBF [kWh/(m2K)]
            a_0_079 = 1.0  # numerischer Parameter für Ausnutzungsgrad [-] wird immer als 1 angenommen SIA 380-1 3.5.6.2
            tau_0_080 = 15.0  # Referenzzeitkonstante für Ausnutzungsgrad [h] wird immer als 15 angenommen SIA 380-1 3.5.6.2

            theta_ic_083 = theta_i_001 + delta_phi_i_002


            q_re_084 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_re_018 * u_re_041 * 24 / (a_e_017*1000)) # Dach geg Aussenluft [kWh/m2]
            q_ru_085 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_ru_019 * u_ru_042 * b_ur_043 * 24 / (a_e_017*1000))  # Decke gegen unbeheizte Räume [kWh/m2]
            q_we_086 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_we_020 * u_we_044 * 24 / (a_e_017*1000))  # Wand gegen Aussenluft
            q_wu_087 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_wu_021 * u_wu_045 * b_uw_046 * 24 / (a_e_017*1000))  # Wand gegen unbeheizte Räume
            q_wg_088 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_wg_022 * u_wg0_047 * b_gw_048 * 24 / (a_e_017*1000))  # Wand gegen Erdreich
            q_wn_089 = np.sum((theta_ic_083-theta_in_050) * t_c_009 * a_wn_023 * u_wn_049 * 24 / (a_e_017 * 1000))  # Wand gegen benachbarte Räume
            q_fe_090 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_fe_024 * u_fe_051 * 24 / (a_e_017 * 1000))  # Boden gegen Aussenluft
            q_fu_091 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_fu_025 * u_fu_052 * b_uf_054 * 24 / (a_e_017 * 1000))  # Boden gegen unbeheizte Räume
            q_fg_092 = np.sum((theta_ic_083-theta_e_011 + delta_theta_059) * t_c_009 * a_fg_026 * u_fg0_055 * b_gf_056 * 24 / (a_e_017 * 1000))  # Boden gegen Erdreich mit Bauteilheizung
            q_fu_093 = np.sum((theta_ic_083-theta_e_011 + delta_theta_059) * t_c_009 * a_fu_027 * u_fu_053 * b_uf_054 * 24 / (a_e_017 * 1000))  # Boden gegen unbeheizte Räume mit Bauteilheizung
            q_fn_094 = np.sum((theta_ic_083 - theta_in_050 + delta_theta_059) * t_c_009 * a_fn_028 * u_fn_057 * 24 / (a_e_017 * 1000))  # Boden gegen beheizte Räume mit Bauteilheizung
            q_rn_095 = np.sum((theta_ic_083 - theta_in_050 + delta_theta_059) * t_c_009 * a_rn_029 * u_rn_058 * 24 / (a_e_017 * 1000))  # Decke gegen beheizte Räume mit Bauteilheizung
            q_wh_096 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * a_wh_030 * u_wh_060 * 24 / (a_e_017 * 1000))  # Fenster horizontal


            q_w_097_to_100 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * self.windows[1] * self.windows[2] * 24 / (a_e_017 * 1000))

            q_lrw_101 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * i_rw_035 * psi_rw_065 * 24 / (a_e_017 * 1000))
            q_lwf_102 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * i_wf_036 * psi_wf_066 * 24 / (a_e_017 * 1000))
            q_ib_103 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * i_b_037 * psi_b_067 * 24 / (a_e_017 * 1000))
            q_lw_104 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * i_w_038 * psi_w_068 *24 / (a_e_017 * 1000))
            q_lf_105 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * i_f_039 * b_uf_054 * psi_f_069 * 24 /(a_e_017 * 1000))
            q_p106 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * z_040 * chi_070 * 24 / (a_e_017 * 1000))

            q_t_107_temporary = q_re_084 + q_ru_085 + q_we_086 + q_wu_087 + q_wg_088 + q_wn_089 + q_fe_090 + q_fu_091 + q_fg_092 + q_fu_093\
                    + q_fn_094 + q_rn_095 + q_wh_096 + q_w_097_to_100 + q_lrw_101 + q_lwf_102 + q_ib_103\
                    + q_lw_104 + q_lf_105 + q_p106  ## Tansmissionswärmeverluste

            rhoa_ca_108 = (1220-0.14 * h_010)/3600

            q_th_109 = q_th_008  # Hier müsste eine Schnittstelle zwischen Nachweis und Optimierung angepasst werden.

            if (q_t_107_temporary + ((theta_ic_083 - theta_e_011) * q_th_008 * t_c_009 * rhoa_ca_108 * 24)/1000) <= 0:
                q_t_107 = 0
                print("Keine Transmissionswärmeverluste q_t_107")
            else:
                q_t_107 = q_t_107_temporary


            if  q_t_107_temporary + (theta_ic_083-theta_e_011) * q_th_109 * t_c_009 * rhoa_ca_108 *24/1000 <= 0:
                q_v_110 = 0
                print("Kein Lüftungswärmeverlust")
            else:
                q_v_110 = (theta_ic_083-theta_e_011) * q_th_109 * t_c_009 * rhoa_ca_108 * 24 / 1000


            q_tot_111 = q_t_107 + q_v_110
            h_112 = np.sum(a_re_018*u_re_041) + np.sum(a_ru_019 * u_ru_042 * b_ur_043) + np.sum(a_we_020 * u_we_044) \
                    + np.sum(a_wu_021 * u_wu_045 * b_uw_046) + np.sum(a_wg_022 * u_wg0_047 * b_gw_048) + np.sum(a_fe_024 * u_fe_051) \
                    + np.sum(a_fu_025 * u_fu_052 * b_uf_054) + np.sum(a_fg_026 * u_fg0_055 * b_gf_056) + np.sum(a_fu_027 * u_fu_053 * b_uf_054)\
                    + np.sum(a_fn_028 * u_fn_057) + np.sum(a_rn_029 * u_rn_058) + np.sum(a_wh_030 * u_wh_060) \
                    + np.sum(self.windows[1]*self.windows[2]) + np.sum(i_rw_035 * psi_rw_065)\
                    + np.sum(i_wf_036 * psi_wf_066) + np.sum(i_b_037 * psi_b_067) + np.sum(i_w_038 * psi_w_068)\
                    + np.sum(i_f_039 * b_uf_054 * psi_f_069) + np.sum(z_040 * chi_070)\
                    + np.sum(a_e_017 * rhoa_ca_108 * q_th_109)  # Diese Gleichung überprüfen lassen.

            ### Wärmeeinträge
            q_i_el_113 = e_f_el_006 * f_el_007 * t_c_009 / 365
            q_l_p_114 = q_p_004 * t_p_005 * t_c_009/(a_p_003 * 1000)
            q_i_115 = q_i_el_113 + q_l_p_114

            q_s_121 = np.sum(g_s_windows * self.windows[1] * self.windows[3] * 0.9 * f_f_072 * f_sh_073 / a_e_017)

            q_g_122 = q_i_115 + q_s_121  # Interne Wärmegewinne
            if q_tot_111 == 0:  # This is not part of SIA380 but needs to be specified for months with no heating demand
                gamma_123 = None
            else:
                gamma_123 = q_g_122/q_tot_111

            tau_124 = cr_ae_078 * a_e_017 * 1000/h_112
            a_125 = a_0_079 + (tau_124/tau_0_080)

            # print(q_g_122)
            # print(tau_124)

            if gamma_123 == None:
                eta_g_126 = 0  # This is not part of SIA380-1 but needs to be specified for months with no heating demand

            elif gamma_123 ==1:
                eta_g_126 = a_125/(a_125+1)
            else:
                eta_g_126 = (1-gamma_123**a_125)/(1-gamma_123**(a_125 + 1))  # Hier weicht die Formel unter 3.5.6.2 von der Zusammenstellung im Anhang D ab

            q_ug_127 = q_g_122 * eta_g_126
            # f_ug_128 = q_ug_127 / q_tot_111

            ### Heizwärmebedarf:
            q_h_129 = q_tot_111 - q_ug_127

            transmissionsverluste[month] = q_t_107
            luftungsverluste[month] = q_v_110
            gesamtwarmeverluste[month] = q_tot_111
            interne_eintrage[month] = q_i_115
            solare_eintrage[month] = q_s_121
            totale_warmeeintrage[month] = q_g_122
            genutzte_warmeeintrage[month] = q_ug_127
            heizwarmebedarf[month] = q_h_129


        self.transmissionsverluste = transmissionsverluste
        self.luftungsverlust=luftungsverluste
        self.gesamtwarmeverluste = gesamtwarmeverluste
        self.interne_eintrage = interne_eintrage
        self.solare_eintrage = solare_eintrage
        self.totale_warmeeintrage = totale_warmeeintrage
        self.genutzte_warmeeintrage = genutzte_warmeeintrage
        self.heizwarmebedarf = heizwarmebedarf


    def run_ISO_52016_monthly(self, weather_data_sia, cooling_setpoint=None):

        """
        This function calculates monthly cooling energy demand per energy reference area in kWh/m2a. The output of
        this function is positive for cooling demand.
        """
        if cooling_setpoint != None:
            print("You use cooling setpoint as an input into ISO instead of the object definition. This version does no longer work.")
            quit()
        else:
            pass

        # cooling_temperature = dp.sia_standardnutzungsdaten('room_temperature_cooling')
        personenflachen = dp.sia_standardnutzungsdaten('area_per_person')
        warmeabgabe_p_p = dp.sia_standardnutzungsdaten('gain_per_person')
        prasenzzeiten = dp.sia_standardnutzungsdaten('presence_time')
        # this part of elektrizitatsbedarf only goes into thermal calculations. Electricity demand is calculated
        # independently.
        elektrizitatsbedarf = dp.sia_standardnutzungsdaten('gains_from_electrical_appliances')
        reduktion_elektrizitat = dp.sia_standardnutzungsdaten('reduction_factor_for_electricity')
        aussenluft_strome = dp.sia_standardnutzungsdaten('effective_air_flow')
        # aussenluft_strome = {1: 2.1}  # UBA-Vergleichsstudie

        if self.cooling_setpoint == "SIA":
            cooling_temperature = dp.sia_standardnutzungsdaten('room_temperature_cooling')
        else:
            cooling_temperature = self.cooling_setpoint

        # Gesamtwärmeübergangskoeffizient für Elemente, die mit der äusseren Umgebung verbunden sind. Dieser Wert wird
        # zeitlich konstant angenommen. [W/K]
        h_hc_el = np.sum(self.roof[0] * self.roof[1]) + np.sum(self.walls[0] * self.walls[1]) +\
        np.sum(self.windows[1] * self.windows[2])

        # Gesamtwärmeübergangskoeffizient für Wärmebrücken in der thermisch konditionierten Zone (6.6.5.3)[W/K]
        # Für den Moment nehme ich an, dass es keine Wärmebrücken gibt
        h_tr_tb_ztc = 0.0

        # 6.6.5.2 Gesamtwärmeübergangskoeffizient durch Transmission für die Kühlung für alle Gebäudeelemente
        # ausser mit dem Erdreich verbunden in [W/K]
        h_c_tr_excl_gf_m_ztc_m = h_hc_el + h_tr_tb_ztc

        # 6.6.11 Berechnungstemperatur der Zone für die Kühlung in [degC]
        theta_int_calc_c_ztc_m = cooling_temperature

        # mittlere monatliche Temperaturen der Aussenluft gemäss relevanten Normen [degC]
        theta_e_a_m = np.array(weather_data_sia['temperature'])

        # ISO 13789 Wärmeübergangskoeffizient des Erdreichs in [W/K] (evtl auch aus SIA380?)
        # Für den Moment so wie bei SIA380/1 gelöst. Noch genauer anschauen, ob dies so gemeint ist.
        h_gr_an_ztc_m =np.sum(self.floor[2] * self.floor[1] * self.floor[0])

        # mittlere Jahresaussentemperatur in [decC] gemäss relevanten Normen
        theta_e_a_an = theta_e_a_m.mean()

        # Dauer des Monats in Stunden
        delta_t_m = np.array([31,28,31,30,31,30,31,31,30,31,30,31])*24.0

        # 6.6.5 Gesamtwärmeübertragung durch Transmission für die Kühlung
        q_c_tr_ztc_m = (h_c_tr_excl_gf_m_ztc_m * (theta_int_calc_c_ztc_m - theta_e_a_m) + h_gr_an_ztc_m *(theta_int_calc_c_ztc_m - theta_e_a_an)) * 0.001 * delta_t_m
        # -> array mit 12 Positionen

        # 6.3.6 in [J/m3K] Aus Konsistenzgründen habe ich hier vorerst die Berechnungsvariante gemäss SIA380
        # verwendet. Überprüfen
        rho_a_c_a = (1220 - 0.14 * self.hohe_uber_meer)

        # 6.6.6.2 Dieser Faktor ist gleich 1 unter der Annahme, dass mit Aussenlufttemperatur gelüftet wird
        # Überprüfen, inwiefern dies mit SIA380 kompatibel ist bzw. WRG/KRG möglich wäre.
        b_ve_c_m = 1

        # 6.6.6.2 gemittelter Luftvolumenstrom in [m3/s] nach relevanten Normen
        # das Objekt hat aussenluft strome in m3 pro stunde und EBF angegeben, deshalb hier die Korrekturen
        q_v_hc_m = aussenluft_strome[int(self.gebaeudekategorie_sia)] * self.energy_reference_area /3600
        # -> float

        # 6.6.6.2 Dieser Wert kann als 1.0 angenommen werden, sofern nicht anders definiert
        # Diese Annahme überprüfen. In Tabelle A.28 und B.28
        f_ve_dyn_m = 1.0


        # 6.6.6.2 Gesamtwärmeübergangskoeffizient durch Lüftung für Heizung/Kühlung [W/K]
        # Ich gehe nur von einer Lüftung aus, deshalb fehlen die indices k
        h_hc_ve_ztc_m = rho_a_c_a * b_ve_c_m * q_v_hc_m * f_ve_dyn_m


        # 6.6.6.1 Gesamtwärmeübertragung durch Lüftung für die Kühlung. Es scheint, dass in Gleichung (113) q statt
        # theta steht
        ## Hier evtl Fehler in Norm. Meiner Meinung nach, muss hier durch 1000 dividiert werden um kWh zu erhalten.
        q_c_ve_ztc_m = h_hc_ve_ztc_m * (theta_int_calc_c_ztc_m - theta_e_a_m) * delta_t_m /1000.0

        #Allenfalls wie bei Heizwärme nach SIA sieh unten:
        #q_th_008 = ((aussenluft_strome[int(self.gebaeudekategorie_sia)]-self.q_inf)*(1-eta_v_081)/f_v_082) + self.q_inf

        # Addition von transmissions und Lüftungsverluste 6.6.4.4
        q_c_ht_ztc_m = q_c_tr_ztc_m + q_c_ve_ztc_m

        # 6.6.7.2 interne Wärmegewinne für die Zone in [kWh]
        # Diese werden hier der Konsistenz wegen wie in SIA 380/1 berechnet
        q_elektrische_anlagen = elektrizitatsbedarf[int(self.gebaeudekategorie_sia)] * self.energy_reference_area *\
                                reduktion_elektrizitat[int(self.gebaeudekategorie_sia)] * delta_t_m / 8760

        q_personen = warmeabgabe_p_p[int(self.gebaeudekategorie_sia)] / 1000.0 * \
                     prasenzzeiten[int(self.gebaeudekategorie_sia)] * (delta_t_m/24.0) / \
                     (personenflachen[int(self.gebaeudekategorie_sia)]) * self.energy_reference_area

        q_hc_int_dir_ztc_m = q_elektrische_anlagen + q_personen

        # 6.6.7 Summe interner Wärmegewinne: Hier gilt folgende Gleichung, weil ich nur von einer
        # Zone ausgehe:
        q_c_int_ztc_m = q_hc_int_dir_ztc_m

        # Solare Wärmegewinne durch Fenster: Hier greife ich auf die Implementierung gemäss SIA 380/1 zurück
        # damit es konsistent mit dem heating demand ist.

        mj_to_kwh_factor = 1.0 / 3.6
        globalstrahlung_horizontal_monatlich = weather_data_sia['global_horizontal'] * mj_to_kwh_factor  # kWh/m2
        globalstrahlung_ost_monatlich = weather_data_sia['global_east'] * mj_to_kwh_factor  # kWh/m2
        globalstrahlung_sud_monatlich = weather_data_sia['global_south'] * mj_to_kwh_factor  # kWh/m2
        globalstrahlung_west_monatlich = weather_data_sia['global_west'] * mj_to_kwh_factor  # kWh/m2
        globalstrahlung_nord_monatlich = weather_data_sia['global_north'] * mj_to_kwh_factor  # kWh/m2
        temperatur_mittelwert = weather_data_sia['temperature']  # degC

        q_hc_sol_wi = np.empty(12)
        f_glass_rahmen = 0.95  # zu verwendender Wert gemäss SIA 380/1
        f_shading = 1  # anpassen, falls Verschattung diskutiert werden soll. Im Moment in SIA heating demand gleich.
        for month in range(12):

            g_sh_012 = globalstrahlung_horizontal_monatlich[month]  # globale Sonnenstrahlung horizontal [kWh/m2]
            g_ss_013 = globalstrahlung_sud_monatlich[month]  # hemisphärische Sonnenstrahlung Süd [kWh/m2]
            g_se_014 = globalstrahlung_ost_monatlich[month]  # hemisphärische Sonnenstrahlung Ost [kWh/m2]
            g_sw_015 = globalstrahlung_west_monatlich[month]  # hemisphärische Sonnenstrahlung West [kWh/m2]
            g_sn_016 = globalstrahlung_nord_monatlich[month]  # hemisphärische Sonnenstrahlung Nord [kWh/m2]

            g_s_windows = window_irradiation(self.windows, g_sh_012, g_ss_013, g_se_014, g_sw_015, g_sn_016)


            q_hc_sol_wi[month] = np.sum(g_s_windows * self.windows[1] * self.windows[3] * 0.9 *
                                        f_glass_rahmen * f_shading)


        # Solare Wärmegewinne durch opake Wände:
        # !!!!! ACHTUNG anschauen, ob dies nicht noch implementiert werden sollte. Vielleicht beim cooling
        # noch wichtig. Vorerst scheint es nicht nötig zu sein.
        q_hc_sol_op = np.repeat(0.0, 12)

        # 6.6.8 Summe der solaren Wärmegewinne für die Kühlung
        q_c_sol_ztc_m = q_hc_sol_wi + q_hc_sol_op


        # Addition interner und solarer Gewinne 6.6.4.4
        q_c_gn_ztc_m = q_c_int_ztc_m + q_c_sol_ztc_m
        gamma_c_ztc_m = q_c_gn_ztc_m/q_c_ht_ztc_m


        # 6.6.9 die effektive interne Wärmekapiztät in J/K Tab 21
        ## self. warmespeicherfahigkeit_pro_ebf ist aber in kWh/m2K (compatible with SIA380-1)
        c_m_eff_ztc = self.warmespeicherfahigkeit_pro_ebf * self.energy_reference_area


        # !!!! Achtung, dies ist nicht bestätigt!!!! Muss mit ISO13789 oder SIA380 angepasst weren
        h_c_gr_adj_ztc = 0.0

        # 6.6.10.4 Zeitkonstante: Factor of 1000 because c_m_eff_ztc comes in kWh/K while h is in W/K
        tau_c_ztc_m = c_m_eff_ztc * 1000 / (h_c_tr_excl_gf_m_ztc_m + h_c_gr_adj_ztc + h_hc_ve_ztc_m)

        # Tabelle B.35 (informative Standardwerte) ebenfalls so in SIA380-1 zu finden
        tau_c_0 = 15. # h
        a_c_0 =1.0 # no dimension

        # Where does this equation come from?
        a_c_ztc_m = a_c_0 + tau_c_ztc_m/tau_c_0

        # 6.6.11.4 This value is assumed. Should be changed for intermittent cooling.
        a_c_red_ztc_m = 1.0

        # 6.6.10.2
        eta_c_ht_ztc_m = np.empty(12)

        for month in range(12):
            if gamma_c_ztc_m[month] == 1.0:
                eta_c_ht_ztc_m[month] = (a_c_ztc_m)/(a_c_ztc_m+1)

            elif gamma_c_ztc_m[month] <= 0:
                eta_c_ht_ztc_m[month] = 1.0

            else:
                eta_c_ht_ztc_m[month] = (1-(gamma_c_ztc_m[month])**-a_c_ztc_m)/(1-(gamma_c_ztc_m[month])**-(a_c_ztc_m+1))

        # Monthly cooling demand summation
        q_c_nd_ztc_m = np.empty(12)
        for month in range(12):
            if 1.0/gamma_c_ztc_m[month] >2.0:
                q_c_nd_ztc_m[month] = 0

            else:
                q_c_nd_ztc_m[month] = a_c_red_ztc_m * (q_c_gn_ztc_m[month] - eta_c_ht_ztc_m[month] * q_c_ht_ztc_m[month])


        self.iso_transmission_losses = q_c_tr_ztc_m/self.energy_reference_area
        self.iso_solar_gains = q_hc_sol_wi/self.energy_reference_area
        self.iso_internal_gains =  q_hc_int_dir_ztc_m / self.energy_reference_area
        self.monthly_cooling_demand = q_c_nd_ztc_m/self.energy_reference_area


    def run_dhw_demand(self):
        """
        Add dhw demand to the building. Retract data from Data prep file
        :return:
        """
        ## Werte aus Datenbanken auslesen:
        self.dhw_demand = np.repeat(dp.sia_annaul_dhw_demand(self.gebaeudekategorie_sia) / 12.0, 12)
        # monthly kWh/energy_reference area --> this way is simplified and needs to be done according to 384/2

    def run_SIA_380_emissions(self, emission_factor_type, avg_gshp_cop=3.8, avg_ashp_cop=2.8):
        """
        Beachte: Die SIA Norm kennt keinen flexiblen Strommix. Soll das Stromprodukt ausgewählt werden können,
        müssten hiere noch weitere Anpassungen durchgeführt werden.

        - Man beachte, dass die Berechnungen in der SIA 380-1 normiert auf die Energiebezugsfläche sind. Die PV
        Produktion wird innerhalb dieser Funktion entsprechend normalisiert. Ebenfalls kommt der PV input in Wh und
        muss noch durch 1000 dividiert werden.
        :return:
        """
        if not hasattr(self, 'heizwarmebedarf'):
            print("Before you can calculate the emissions, you first have to run the heating demand simulation")
            quit()

        # self.pv_production is total PV production in Wh and has to be normalized and divided by 1000 for the SIA
        # framework because it comes in Wh
        pv_prod_month = dp.hourly_to_monthly(self.pv_production)/self.energy_reference_area/1000.0


        ### Bestimmung Elektrizitätsbedarf pro EBF:
        self.electricity_demand = self.app_light_other_electricity_monthly_demand
        if self.heating_system == "GSHP":
            self.heating_elec = self.heizwarmebedarf/avg_gshp_cop
            self.dhw_elec = self.dhw_demand/avg_gshp_cop

        elif self.heating_system == "ASHP":
            self.heating_elec = self.heizwarmebedarf/avg_ashp_cop
            self.dhw_elec = self.dhw_demand / avg_ashp_cop

        elif self.heating_system == "electric":
            self.heating_elec = self.heizwarmebedarf
            self.dhw_elec = self.dhw_demand

        else:
            self.heating_elec = 0.0
            self.dhw_elec = 0.0

        # same for cooling
        if self.cooling_system == "GSHP":
            # The COP cooling is generally one lower than for heating.
            self.cooling_elec = self.monthly_cooling_demand/(avg_gshp_cop-1.0)

        elif self.cooling_system == "ASHP":
            self.cooling_elec = self.monthly_cooling_demand/(avg_ashp_cop-1.0)

        elif self.cooling_system == "electric":
            print("Pure electric cooling is not a possible choice, simulation terminated")
            quit()

        else:
            self.cooling_elec = 0.0

        self.electricity_demand += (self.heating_elec + self.dhw_elec + self.cooling_elec)

        # This way of net metering is a very agregated and propably not suitable way to do it.
        self.net_electricity_demand = self.electricity_demand - pv_prod_month


        ## Calculate operational impact:
        self.fossil_heating_emissions = np.empty(12)
        self.fossil_dhw_emissions = np.empty(12)
        self.electricity_emissions = np.empty(12)


        # account for fossil heating emissions
        if self.heating_system in ["Oil", "Natural Gas", "Wood", "Pellets"]:
            self.fossil_heating_emissions = self.heizwarmebedarf * dp.fossil_emission_factors(self.heating_system).mean()

        else:
            self.fossil_heating_emissions = 0.0

        # account for fossil dhw emissions
        if self.dhw_heating_system in ["Oil", "Natural Gas", "Wood", "Pellets"]:
            self.fossil_dhw_emissions = self.dhw_demand * dp.fossil_emission_factors(self.dhw_heating_system).mean()

        else:
            self.fossil_dhw_emissions = 0.0


        # acount for net grid import emissions
        self.grid_electricity_emissions = self.net_electricity_demand * dp.build_yearly_emission_factors_sia().mean()
        self.grid_electricity_emissions[self.grid_electricity_emissions < 0.0] = 0.0

        self.operational_emissions = self.fossil_heating_emissions + self.fossil_dhw_emissions + \
                                     self.grid_electricity_emissions ## always make sure to be clear what these emissions include (see SIA 380)


    def run_SIA_electricity_demand(self, occupancy_path):
        self.app_light_other_electricity_monthly_demand = dp.hourly_to_monthly(
            dp.sia_electricity_per_erf_hourly(occupancy_path, self.gebaeudekategorie_sia))


def window_irradiation(windows, g_sh_012, g_ss_013, g_se_014, g_sw_015, g_sn_016):
    """
    Diese Funktion rechnet die ausrichtungsspezifischen Einstrahlungswerte aus und bereitet den Einstrahlungsvektor
    für die Berechnung der run Funktion vor.
    [Horizontale Ausrichtung noch nicht möglich]
    :param windows: np.array [[Orientation],[Areas],[U-values],[g-values]]
    :param g_sh_012: float monthly horizontal irradiation
    :param g_ss_013: float monthly south irradiation
    :param g_se_014: float monthly east irradiation
    :param g_sw_015: float monthly west irradiation
    :param g_sn_016: float monthly north irradiation
    :return:
    """

    g_s_windows = np.empty(len(windows[0]))

    for i in range(len(windows[0])):
        if windows[0][i] == "S":
            g_s_windows[i] = g_ss_013
        elif windows[0][i] == "E":
            g_s_windows[i] = g_se_014
        elif windows[0][i] == "W":
            g_s_windows[i] = g_sw_015
        elif windows[0][i] == "N":
            g_s_windows[i] = g_sn_016
        elif windows[0][i] == "SE":
            g_s_windows[i] = (g_ss_013*g_se_014)**0.5
        elif windows[0][i] == "SW":
            g_s_windows[i] = (g_ss_013*g_sw_015)**0.5
        elif windows[0][i] == "NW":
            g_s_windows[i] = (g_sn_016*g_sw_015)**0.5
        elif windows[0][i] == "NE":
            g_s_windows[i] = (g_sn_016*g_se_014)**0.5
        else:
            "Himmelsrichtungen bei den Fenstern nicht korrekt eingegeben. Bitte beachte, dass vorerst nur ein oder " \
            "zweistellige Richtungen erlaubt sind (N, E, S, W, NE, SE, SW, NW)"

    return g_s_windows




if __name__=='__main__':
    pass