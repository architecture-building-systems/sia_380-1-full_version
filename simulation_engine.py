import numpy as np

class Building(object):

    def __init__(self,
                 gebaeudekategorie_sia,
                 regelung,
                 windows,
                 walls,
                 roof,
                 energy_reference_area,
                 heat_recovery_nutzungsgrad,
                 thermal_storage_capacity_per_floor_area,
                 korrekturfaktor_luftungs_eff_f_v,
                 height_above_sea):

        self.gebaeudekategorie_sia = gebaeudekategorie_sia
        self.regelung = regelung
        self.windows = windows  # np.array of windows with |area|u-value|g-value|orientation|shading_f1|shading_f2|
        self.walls = walls  # np.array of walls with |area|u-value| so far b-values not possible
        self.roof = roof  # np.array of roofs with |area|u-value|
        self.energy_reference_area = energy_reference_area  # One value, float
        self.anlagennutzungsgrad_wrg = heat_recovery_nutzungsgrad  # One value, float
        self.warmespeicherfahigkeit_pro_ebf = thermal_storage_capacity_per_floor_area # One value, float
        self.korrekturfaktor_luftungs_eff_f_v = korrekturfaktor_luftungs_eff_f_v
        self.hohe_uber_meer = height_above_sea








    def run_SIA_380_1(self):

        ### "Datenbanken"
        standard_raumtemperaturen = {1:20., 2:20., 3:20., 4:20., 5:20., 6:20, 7:20, 8:22, 9:18, 10:18, 11:18, 12:28}  #380-1 Tab7
        regelzuschlaege = {"Einzelraum":0., "Referenzraum":1., "andere":2.}  #380-1 Tab8
        personenflachen = {1:40., 2:60., 3:20., 4:10., 5:10., 6:5, 7:5., 8:30., 9:20., 10:100., 11:20., 12:20.}  # 380-1 Tab9
        warmeabgabe_p_p = {1:70., 2:70., 3:80., 4:70., 5:90., 6:100., 7:80., 8:80., 9:100., 10:100., 11:100., 12:60.}  # 380-1 Tab10
        prasenzzeiten = {1:12., 2:12., 3:6., 4:4., 5:4., 6:3., 7:3., 8:16., 9:6., 10:6., 11:6., 12:4.}  # 380-1 Tab11
        elektrizitatsbedarf = {1:28., 2:22., 3:22., 4:11., 5:33., 6:33., 7:17., 8:28., 9:17., 10:6., 11:6., 12:56.}  # 380-1 Tab12
        reduktion_elektrizitat = {1:0.7, 2:0.7, 3:0.9, 4:0.9, 5:0.8, 6:0.7, 7:0.8, 8:0.7, 9:0.9, 10:0.9, 11:0.9, 12:0.7}  # 380-1 Tab13
        aussenluft_strome = {1:0.7, 2:0.7, 3:0.7, 4:0.7, 5:0.7, 6:1.2, 7:1.0, 8:1.0, 9:0.7, 10:0.3, 11:0.7, 12:0.7}  # 380-1 Tab14


        ## Klimadaten aus SIA2028 (Zürich-Kloten)

        mj_to_kwh_factor = 1.0/3.6

        globalstrahlung_horizontal_monatlich = np.array([102, 167, 313, 425, 546, 583, 603, 525, 355, 209, 106, 80]) * mj_to_kwh_factor  # kWh/m2
        globalstrahlung_ost_monatlich = np.array([67, 109, 190, 244, 303, 321, 335, 297, 194, 107, 60, 48]) * mj_to_kwh_factor # kWh/m2
        globalstrahlung_sud_monatlich = np.array([163, 235, 316, 298, 295, 277, 303, 337, 311, 244, 148, 123]) * mj_to_kwh_factor # kWh/m2
        globalstrahlung_west_monatlich = np.array([78, 123, 196, 236, 297, 311, 332, 297, 218, 142, 73, 56]) * mj_to_kwh_factor # kWh/m2
        globalstrahlung_nord_monatlich = np.array([43, 65, 96, 119, 163, 184, 182, 142, 98, 67, 39, 32]) * mj_to_kwh_factor # kWh/m2
        temperatur_mittelwert = [0.2, 1.3, 5.4, 8.5, 13.6, 16.5, 18.7, 18.5, 14.0, 9.7, 4.1, 1.7]  # degC

        t_c = [31,28,31,30,31,30,31,31,30,31,30,31]  # Tage pro Monat.

        ### Nutzungsdaten: (gemäss SIA 380-1, Messwerte können verwendet werden.)
        theta_i_001 = standard_raumtemperaturen[self.gebaeudekategorie_sia] # Raumtemperatur in °C Gemäss SIA380-1 2016 Tab7 (grundsätzlich 20°C)
        delta_phi_i_002 = regelzuschlaege[self.regelung] # Regelungszuschlag für die Raumtemperatur [K] gemäss SIA380-1 2016 Tab8
        a_p_003 = personenflachen[self.gebaeudekategorie_sia]  # Personenfläche m2/P
        q_p_004 = warmeabgabe_p_p[self.gebaeudekategorie_sia] # Wärmeabgabe pro Person W/P
        t_p_005 = prasenzzeiten[self.gebaeudekategorie_sia]  # Präsenzzeit pro Tag h/d
        e_f_el_006 = elektrizitatsbedarf[self.gebaeudekategorie_sia]  # Elektrizitätsbedarf pro Jahr kWh/m2
        f_el_007 = reduktion_elektrizitat[self.gebaeudekategorie_sia]  # Reduktionsfaktor Elektrizität [-]
        q_th_008 = aussenluft_strome[self.gebaeudekategorie_sia]  # thermisch wirksamer Aussenluftvolumenstrom gem 3.5.5 m3/(hm2)

        h_010 = self.hohe_uber_meer  # Höhge über Meer [m]


        transmissionsverluste = np.empty(12)
        luftungsverluste = np.empty(12)
        gesamtwarmeverluste = np.empty(12)
        interne_eintrage = np.empty(12)
        solare_eintrage = np.empty(12)
        totale_warmeeintrage = np.empty(12)
        genutzte_warmeeintrage = np.empty(12)
        heizwarmebedarf = np.empty(12)



        for month in range(12):  ## Zähler von 0-11
            ### Klimadaten: (gemäss SIA 2028 oder Messwerte falls vorhanden)
            t_c_009 = t_c[month]  # Länge Berechnungsschritt [d]
            theta_e_011 = temperatur_mittelwert[month] # Aussenlufttemperatur [degC]
            g_sh_012 = globalstrahlung_horizontal_monatlich[month]  # globale Sonnenstrahlung horizontal [kWh/m2]
            g_ss_013 = globalstrahlung_sud_monatlich[month]  # hemisphärische Sonnenstrahlung Süd [kWh/m2]
            g_se_014 = globalstrahlung_ost_monatlich[month]  # hemisphärische Sonnenstrahlung Ost [kWh/m2]
            g_sw_015 = globalstrahlung_west_monatlich[month] # hemisphärische Sonnenstrahlung West [kWh/m2]
            g_sn_016 = globalstrahlung_nord_monatlich[month]  # hemisphärische Sonnenstrahlung Nord [kWh/m2]

            g_s_windows = window_irradiation(self.windows, g_sh_012, g_ss_013, g_se_014, g_sw_015, g_sn_016)

            ### Flächen, Längen und Anzahl
            a_e_017 = self.energy_reference_area  # Energiebezugsfläche [m2]
            a_re_018 = self.roof[0]  # Dach gegen Aussenluft [m2]
            a_ru_019 = np.array([0])  # Decke gegen unbeheizte Räume [m2]
            a_we_020 = self.walls[0]  # Wand gegen Aussenluft [m2]
            a_wu_021 = np.array([0])  # Wand gegen unbeheizte Räume [m2]
            a_wg_022 = np.array([0]) # Wand gegen Erdreich [m2]
            a_wn_023 = np.array([0])  # Wand gegen benachbarten beheizten Raum im Bilanzperimeter [m2]
            a_fe_024 = np.array([0])  # Boden gegen Aussenluft [m2]
            a_fu_025 = np.array([506])  # Boden gegen unbeheizte Räume (und gegen Erdreich?) [m2]
            a_fg_026 = np.array([0])  # Boden gegen Erdreich mit Bauteilheizung [m2]
            a_fu_027 = np.array([0])  # Boden gegen unbeheizte Räume mit Bauteilheizung[m2]
            a_fn_028 = np.array([0])  # Boden gegen beheizte Räume mit Bauteilheizung im Bilanzperimeter [m2]
            a_rn_029 = np.array([0])  # Decke gegen beheizte Räume mit Bauteilheizung im Bilanzparameter [m2]
            a_wh_030 = np.array([0])  # Fenster horizontal [m2]
            a_ws_031 = np.array([131.5])  # Fenster Süed [m2]
            a_we_032 = np.array([131.5])  # Fenster Ost [m2]
            a_ww_033 = np.array([131.5])  # Fenster West [m2]
            a_wn_034 = np.array([131.5])  # Fenster Nord [m2]

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
            u_fu_052 = np.array([0.09])  # Boden gegen unbeheizte Räume [W/(m2K)]
            u_fu_053 = np.array([0])  # Boden gegen unbeheizte Räume mit Bauteilheizung [W/(m2K)]
            b_uf_054 = np.array([0.4])  # Reduktionsfaktor Boden gegen unbeheizte Räume [-]
            u_fg0_055 = np.array([0])  # Boden gegen Erdreich mit Bauteilheizung [W/(m2K)]
            b_gf_056 = np.array([0])  # Reduktionsfaktro Boden gegen Erdreich [-]
            u_fn_057 = np.array([0])  # Boden gegen beheizte Räume mit Bauteilheizung [W/(m2K)]
            u_rn_058 = np.array([0])  # Decke gegen beheizte Räume mit Bauteilheizung [W/(m2K)]
            delta_theta_059 = 0.0  # Temperaturzuschlag für Bauteilheizung [K], dies anpassen nach Tab16 SIA380-1 3.5.4.5
            u_wh_060 = np.array([0.6])  # Fenster horizontal [W/(m2K)]
            u_ws_061 = np.array([0.6])   # Fenster süd [W/(m2K)]
            u_we_062 = np.array([0.6])   # Fenster ost [W/(m2K)]
            u_ww_063 = np.array([0.6])   # Fenster west [W/(m2K)]
            u_wn_064 = np.array([0.6])   # Fenster nord [W/(m2K)]
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
            f_f_072 = 0.95# Abminderungsfaktor für Fensterrahmen [-]
            f_sh_073 = 1.0  # Verschattungsfaktor horizontal [-]
            f_ss_074 = 1.0  # Verschattungsfaktor Süd [-]
            f_se_075 = 1.0  # Verschattungsfaktor ost [-]
            f_sw_076 = 1.0  # Verschattungsfaktor West [-]
            f_sn_077 = 1.0  # Verschattungsfaktor nord [-]

            ### spezielle Eingabedaten
            cr_ae_078 = self.warmespeicherfahigkeit_pro_ebf  # Wärmespeicherfähigkeit pro EBF [kWh/(m2K)]
            a_0_079 = 1.0  # numerischer Parameter für Ausnutzungsgrad [-] wird immer als 1 angenommen SIA 380-1 3.5.6.2
            tau_0_080 = 15.0  # Referenzzeitkonstante für Ausnutzungsgrad [h] wird immer als 15 angenommen SIA 380-1 3.5.6.2
            eta_v_081 = self.anlagennutzungsgrad_wrg  # anlagennutzungsgrad der wärmerückgewinnung [-]
            f_v_082 = self.korrekturfaktor_luftungs_eff_f_v  # Korrekturfaktor für die Lüftungseffektivität [-]



            ### Berechnung

            theta_ic_083 = theta_i_001 + delta_phi_i_002

            q_re_084 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_re_018 * u_re_041 * 24 / (a_e_017*1000)) # Dach geg Aussenluft [kWh/m2]
            q_ru_085 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_ru_019 * u_ru_042 * b_ur_043 * 24 / (a_e_017*1000))  # Decke gegen unbeheizte Räume [kWh/m2]
            q_we_086 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_we_020 * u_we_044 * 24 / (a_e_017*1000))  # Wand gegen Aussenluft
            q_wu_087 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_wu_021 * u_wu_045 * b_uw_046 * 24 / (a_e_017*1000))  # Wand gegen unbeheizte Räume
            q_wg_088 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_wg_022 * u_wg0_047 * b_gw_048 * 24 / (a_e_017*1000))  # Wand gegen Erdreich
            q_wn_089 = np.sum((theta_ic_083-theta_in_050) * t_c_009 * a_wn_023 * u_wn_049 * 24 / (a_e_017 * 1000))  # Wand gegen benachbarte Räume
            q_fe_090 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_fe_024 * u_fe_051 * 24 / (a_e_017 * 1000))  # Boden gegen Aussenluft
            q_fu_091 = np.sum((theta_ic_083-theta_e_011) * t_c_009 * a_fu_025 * u_fu_052 * b_uf_054 * 24 / (a_e_017 * 1000))  # Boden gegen unbeheizte Räume
            q_fg_092 = np.sum((theta_ic_083-theta_e_011 + delta_theta_059) * t_c_009 * a_fg_026 * u_fg0_055 * b_gf_056 * 24 / (a_e_017 * 1000))
            q_fu_093 = np.sum((theta_ic_083-theta_e_011 + delta_theta_059) * t_c_009 * a_fu_027 * u_fu_053 * b_uf_054 * 24 / (a_e_017 * 1000))
            q_fn_094 = np.sum((theta_ic_083 - theta_in_050 + delta_theta_059) * t_c_009 * a_fn_028 * u_fn_057 * 24 / (a_e_017 * 1000))
            q_rn_095 = np.sum((theta_ic_083 - theta_in_050 + delta_theta_059) * t_c_009 * a_rn_029 * u_rn_058 * 24 / (a_e_017 * 1000))
            q_wh_096 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * a_wh_030 * u_wh_060 * 24 / (a_e_017 * 1000))
            q_ws_097 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * a_ws_031 * u_ws_061 * 24 / (a_e_017 * 1000))
            q_we_098 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * a_we_032 * u_we_062 * 24 / (a_e_017 * 1000))
            q_ww_099 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * a_ww_033 * u_ww_063 * 24 / (a_e_017 * 1000))
            q_wn_100 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * a_wn_034 * u_wn_064 * 24 / (a_e_017 * 1000))
            q_lrw_101 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * i_rw_035 * psi_rw_065 * 24 / (a_e_017 * 1000))
            q_lwf_102 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * i_wf_036 * psi_wf_066 * 24 / (a_e_017 * 1000))
            q_ib_103 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * i_b_037 * psi_b_067 * 24 / (a_e_017 * 1000))
            q_lw_104 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * i_w_038 * psi_w_068 *24 / (a_e_017 * 1000))
            q_lf_105 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * i_f_039 * b_uf_054 * psi_f_069 * 24 /(a_e_017 * 1000))
            q_p106 = np.sum((theta_ic_083 - theta_e_011) * t_c_009 * z_040 * chi_070 * 24 / (a_e_017 * 1000))

            q_t_107_temporary = q_re_084 + q_ru_085 + q_we_086 + q_wu_087 + q_wg_088 + q_wn_089 + q_fe_090 + q_fu_091 + q_fg_092 + q_fu_093\
                    + q_fn_094 + q_rn_095 + q_wh_096 + q_ws_097 + q_we_098 + q_ww_099 + q_wn_100 + q_lrw_101 + q_lwf_102 + q_ib_103\
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
                    + np.sum(a_fn_028 * u_fn_057) + np.sum(a_rn_029 * u_rn_058) + np.sum(a_wh_030 * u_wh_060) + np.sum(a_ws_031 * u_ws_061)\
                    + np.sum(a_we_032 * u_we_062) + np.sum(a_ww_033 * u_ww_063) + np.sum(a_wn_034 * u_wn_064) + np.sum(i_rw_035 * psi_rw_065)\
                    + np.sum(i_wf_036 * psi_wf_066) + np.sum(i_b_037 * psi_b_067) + np.sum(i_w_038 * psi_w_068) + np.sum(i_f_039 * b_uf_054 * psi_f_069)\
                    + np.sum(z_040 * chi_070) + np.sum(a_e_017 * rhoa_ca_108 * q_th_109)  # Diese Gleichung überprüfen lassen.

            ### Wärmeeinträge
            q_i_el_113 = e_f_el_006 * f_el_007 * t_c_009 / 365
            q_l_p_114 = q_p_004 * t_p_005 * t_c_009/(a_p_003 * 1000)
            q_i_115 = q_i_el_113 + q_l_p_114


            q_sh_116 = np.sum(g_sh_012 * a_wh_030 * 0.9 * g_071 * f_f_072 * f_sh_073 / a_e_017)

            ## Those are part of SIA380-1 and are now included in the direct, vector based calculation of q_g_122
            # q_ss_117 = np.sum(g_ss_013 * a_ws_031 * 0.9 * g_071 * f_f_072 * f_ss_074 / a_e_017)
            # q_se_118 = np.sum(g_se_014 * a_we_032 * 0.9 * g_071 * f_f_072 * f_se_075 / a_e_017)
            # q_sw_119 = np.sum(g_sw_015 * a_ww_033 * 0.9 * g_071 * f_f_072 * f_sw_076 / a_e_017)
            # q_sn_120 = np.sum(g_sn_016 * a_wn_034 * 0.9 * g_071 * f_f_072 * f_sn_077 / a_e_017)
            # q_s_121 = q_sh_116 + q_ss_117 + q_se_118 + q_sw_119 + q_sn_120
            q_s_121 = np.sum(g_s_windows * self.windows[1] * self.windows[3] * 0.9 * f_f_072 * f_sh_073 / a_e_017)

            q_g_122 = q_i_115 + q_s_121  # Interne Wärmegewinne
            gamma_123 = q_g_122/q_tot_111
            tau_124 = cr_ae_078 * a_e_017 * 1000/h_112
            a_125 = a_0_079 + (tau_124/tau_0_080)

            # print(q_g_122)
            # print(tau_124)


            if gamma_123 ==1:
                eta_g_126 = a_125/(a_125+1)
            else:
                eta_g_126 = (1-gamma_123**a_125)/(1-gamma_123**(a_125 + 1))  # Hier weicht die Formel unter 3.5.6.2 von der Zusammenstellung im Anhang D ab

            q_ug_127 = q_g_122 * eta_g_126
            f_ug_128 = q_ug_127 / q_tot_111

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
        return(transmissionsverluste, luftungsverluste, gesamtwarmeverluste, interne_eintrage, solare_eintrage,
               totale_warmeeintrage, genutzte_warmeeintrage, heizwarmebedarf)


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