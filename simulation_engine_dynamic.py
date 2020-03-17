import sys
sys.path.insert(1, r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator")
from building_physics import Building
import numpy as np
import pandas as pd
import data_prep as dp
import supply_system
import emission_system
from radiation import Location
from radiation import Window




class Sim_Building(object):
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
                 thermal_storage_capacity_per_floor_area,
                 korrekturfaktor_luftungs_eff_f_v,
                 height_above_sea,
                 heating_system,
                 cooling_system,
                 dhw_heating_system):

        print(heating_system)

        ### Similar to SIA some are unecessary.
        self.gebaeudekategorie_sia = gebaeudekategorie_sia
        self.regelung = regelung
        self.windows = windows  # np.array of windows with |area|u-value|g-value|orientation|shading_f1|shading_f2|
        self.walls = walls  # np.array of walls with |area|u-value| so far, b-values are not possible
        self.roof = roof  # np.array of roofs with |area|u-value|
        self.floor = floor  # np.array of floowrs with |area|u-value|b-value|
        self.energy_reference_area = energy_reference_area  # One value, float
        self.anlagennutzungsgrad_wrg = heat_recovery_nutzungsgrad  # One value, float
        self.q_inf = infiltration_volume_flow
        self.warmespeicherfahigkeit_pro_ebf = thermal_storage_capacity_per_floor_area
        self.korrekturfaktor_luftungs_eff_f_v = korrekturfaktor_luftungs_eff_f_v
        self.hohe_uber_meer = height_above_sea
        self.heating_system = heating_system
        self.cooling_system = cooling_system

        ### RC Simulator inputs (derive from other inputs as much as possible)
        ## So far the lighting load is still hard coded because it is not looked at and I don't know the source.
        lighting_load = 11.7  # [W/m2] (source?)
        lighting_control = 300.0  # lux threshold at which the lights turn on.
        lighting_utilisation_factor = 0.45
        lighting_maintenance_factor = 0.9

        self.window_area = self.windows[1].sum()  # sums up all window area
        self.external_envelope_area = self.walls[0].sum() + self.windows[1].sum()  # so far includes vertical envelope
        self.room_depth = np.sqrt(self.energy_reference_area)  # assumption: quadratic foot print, one story
        self.room_width = np.sqrt(self.energy_reference_area)  # assumption: quadratic foot print, one story
        self.room_height = 3 #m (for now a fixed value)
        self.lighting_load = lighting_load
        self.lighting_control = lighting_control
        self.lighting_utilisation_factor = lighting_utilisation_factor
        self.lighting_maintenance_factor = lighting_maintenance_factor
        self.u_walls = (self.walls[0]*self.walls[1]).sum() /self.walls[0].sum()  # weighted average of walls u-values
        self.u_windows = (self.windows[1]*self.windows[2]).sum() /self.windows[1].sum() # weighted average of window u-values
        self.g_windows = (self.windows[1]*self.windows[3]).sum() /self.windows[1].sum() # weighted average of window g-values
        self.ach_vent = None
        self.ach_infl = self.q_inf / self.room_height  # Umrechnung von m3/(h*m2) in 1/h
        self.ventilation_efficiency = self.anlagennutzungsgrad_wrg
        self.thermal_capacitance_per_floor_area = self.warmespeicherfahigkeit_pro_ebf
        self.t_set_heating = None
        self.t_set_cooling = None
        self.max_cooling_energy_per_floor_area = -np.inf
        self.max_heating_energy_per_floor_area = np.inf
        self.dhw_supply_temperature = 60  # deg C fixed and hard coded

        self.dhw_heating_system = dhw_heating_system
        self.pv_production = None


    def run_rc_simulation(self, weatherfile_path, occupancy_path, cooling_setpoint):
        """
        ACHTUNG. Im Vergleich zum SIA Modul sind hier im Moment noch Wh als output zu finden.
        :param weatherfile_path:
        :param occupancy_path:
        :return:
        """
        standard_raumtemperaturen = {1: 20., 2: 20., 3: 20., 4: 20., 5: 20., 6: 20, 7: 20, 8: 22, 9: 18, 10: 18, 11: 18,
                                     12: 28}  # 380-1 Tab7
        warmeabgabe_p_p = {1: 70., 2: 70., 3: 80., 4: 70., 5: 90., 6: 100., 7: 80., 8: 80., 9: 100., 10: 100., 11: 100.,
                           12: 60.}  # 380-1 Tab10 (W)

        elektrizitatsbedarf = {1: 28., 2: 22., 3: 22., 4: 11., 5: 33., 6: 33., 7: 17., 8: 28., 9: 17., 10: 6., 11: 6.,
                               12: 56.}  # 380-1 Tab12 (kWh/m2a)

        personenflachen = {1: 40., 2: 60., 3: 20., 4: 10., 5: 10., 6: 5, 7: 5., 8: 30., 9: 20., 10: 100., 11: 20.,
                           12: 20.}  # 380-1 Tab9

        aussenluft_strome = {1: 0.7, 2: 0.7, 3: 0.7, 4: 0.7, 5: 0.7, 6: 1.2, 7: 1.0, 8: 1.0, 9: 0.7, 10: 0.3, 11: 0.7,
                             12: 0.7}  # 380-1 Tab14
        # aussenluft_strome = {1:2.1}

        annual_dhw_demand = {1.1: 19.8, 1.2: 13.5, 2.1: 39.5, 2.2: 0., 3.1: 3.6, 3.2: 3.6, 3.3: 0.0, 3.4: 0.0, 4.1: 5.3,
                             4.2: 0.0,
                             4.3: 0.0, 4.4: 7.9, 5.1: 2.7, 5.2: 2.7, 5.3: 1.5, 6.1: 108.9, 7.1: 7.3, 7.2: 7.3,
                             8.1: 67.7,
                             8.2: 0.0, 8.3: 0.0, 9.1: 2.4, 9.2: 2.4, 9.3: 2.4, 10.1: 0.9, 11.1: 52.9, 11.2: 87.1,
                             12: None}
        # in kWh/m2a according to SIA2024 possbily needs to be changed to SIA 385/2


        self.t_set_heating = standard_raumtemperaturen[int(self.gebaeudekategorie_sia)]
        Loc = Location(epwfile_path=weatherfile_path)
        gain_per_person = warmeabgabe_p_p[int(self.gebaeudekategorie_sia)]  # W/m2
        appliance_gains = elektrizitatsbedarf[int(self.gebaeudekategorie_sia)]/365/24  # W per sqm (constant over the year)
        max_occupancy = self.energy_reference_area / personenflachen[int(self.gebaeudekategorie_sia)]
        self.ach_vent = aussenluft_strome[int(self.gebaeudekategorie_sia)]/self.room_height  # here we switch from SIA m3/hm2 to air change rate /h
        heating_supply_system = dp.translate_system_sia_to_rc(self.heating_system)
        cooling_supply_system = dp.translate_system_sia_to_rc(self.cooling_system)
        self.annual_dhw_demand = annual_dhw_demand[self.gebaeudekategorie_sia] * 1000  # Sia calculates in kWh, RC Simulator in Wh

        Office = Building(window_area=self.window_area,
                          external_envelope_area=self.external_envelope_area,
                          room_depth=self.room_depth,
                          room_width=self.room_width,
                          room_height=self.room_height,
                          lighting_load=self.lighting_load,
                          lighting_control=self.lighting_control,
                          lighting_utilisation_factor=self.lighting_utilisation_factor,
                          lighting_maintenance_factor=self.lighting_maintenance_factor,
                          u_walls=self.u_walls,
                          u_windows=self.u_windows,
                          ach_vent=self.ach_vent,
                          ach_infl=self.ach_infl,
                          ventilation_efficiency=self.ventilation_efficiency,
                          thermal_capacitance_per_floor_area=self.thermal_capacitance_per_floor_area * 3600 * 1000,  # Comes as kWh/m2K and needs to be J/m2K
                          t_set_heating=self.t_set_heating,
                          t_set_cooling=cooling_setpoint,  # maybe this can be added to the simulation object as well
                          max_cooling_energy_per_floor_area=self.max_cooling_energy_per_floor_area,
                          max_heating_energy_per_floor_area=self.max_heating_energy_per_floor_area,
                          heating_supply_system=heating_supply_system,
                          cooling_supply_system=cooling_supply_system,
                          heating_emission_system=emission_system.FloorHeating,  # define this!
                          cooling_emission_system=emission_system.AirConditioning,  # define this!
                          dhw_supply_temperature=self.dhw_supply_temperature, )

        SouthWindow = Window(azimuth_tilt=0., alititude_tilt=90.0, glass_solar_transmittance=self.g_windows,
                             glass_light_transmittance=0.5, area=self.window_area)  # az and alt are hardcoded because
                                # they are assumed to be vertical south facing windows (IMPROVE!)

        # RoofPV = PhotovoltaicSurface(azimuth_tilt=pv_azimuth, alititude_tilt=pv_tilt, stc_efficiency=pv_efficiency,
        #                              performance_ratio=0.8, area=pv_area)  # Performance ratio is still hard coded.
        # Temporarily disabled. Add again later

        ## Define occupancy
        occupancyProfile = pd.read_csv(occupancy_path)

        t_m_prev = 20.0  # This is only for the very first step in therefore is hard coded.

        self.electricity_demand = np.empty(8760)
        self.total_heat_demand = np.empty(8760)
        self.heating_electricity_demand = np.empty(8760)
        self.heating_fossil_demand = np.empty(8760)
        self.heating_demand = np.empty(8760)
        self.cooling_electricity_demand = np.empty(8760)
        self.cooling_fossil_demand = np.empty(8760)
        self.cooling_demand = np.empty(8760)
        self.dhw_electricity_demand = np.empty(8760)
        self.dhw_fossil_demand = np.empty(8760)
        self.dhw_demand = np.empty(8760)
        self.solar_gains = np.empty(8760)
        self.indoor_temperature = np.empty(8760)

        for hour in range(8760):
            # Occupancy for the time step
            occupancy = occupancyProfile.loc[hour, 'People'] * max_occupancy
            # Gains from occupancy and appliances
            internal_gains = occupancy * gain_per_person + appliance_gains * Office.floor_area

            # Domestic hot water schedule  ### add this in a later stage
            dhw_demand = self.annual_dhw_demand / occupancyProfile['People'].sum()\
                         * occupancyProfile.loc[hour, 'People'] * self.energy_reference_area # Wh

            # Extract the outdoor temperature in Zurich for that hour
            t_out = Loc.weather_data['drybulb_C'][hour]

            Altitude, Azimuth = Loc.calc_sun_position(latitude_deg=47.480, longitude_deg=8.536, year=2015, hoy=hour)

            SouthWindow.calc_solar_gains(sun_altitude=Altitude, sun_azimuth=Azimuth,
                                         normal_direct_radiation=Loc.weather_data['dirnorrad_Whm2'][hour],
                                         horizontal_diffuse_radiation=Loc.weather_data['difhorrad_Whm2'][hour])

            SouthWindow.calc_illuminance(sun_altitude=Altitude, sun_azimuth=Azimuth,
                                         normal_direct_illuminance=Loc.weather_data['dirnorillum_lux'][hour],
                                         horizontal_diffuse_illuminance=Loc.weather_data['difhorillum_lux'][hour])

            Office.solve_building_energy(internal_gains=internal_gains, solar_gains=SouthWindow.solar_gains,
                                         t_out=t_out,
                                         t_m_prev=t_m_prev, dhw_demand=dhw_demand)

            Office.solve_building_lighting(illuminance=SouthWindow.transmitted_illuminance, occupancy=occupancy)

            # Set the previous temperature for the next time step

            t_m_prev = Office.t_m_next


            self.heating_electricity_demand[hour] = Office.heating_sys_electricity  # unit? heating electricity demand
            self.heating_fossil_demand[hour] = Office.heating_sys_fossils
            self.cooling_electricity_demand[hour] = Office.cooling_sys_electricity  # unit?
            self.cooling_fossil_demand[hour] = Office.cooling_sys_fossils
            self.solar_gains[hour] = SouthWindow.solar_gains
            self.electricity_demand[
                hour] = Office.heating_sys_electricity + Office.dhw_sys_electricity + Office.cooling_sys_electricity  # in Wh
            self.heating_demand[hour] = Office.heating_demand  # this is the actual heat emitted, unit?
            self.cooling_demand[hour] = Office.cooling_demand
            self.dhw_electricity_demand[hour] = Office.dhw_sys_electricity
            self.dhw_fossil_demand[hour] = Office.dhw_sys_fossils
            self.dhw_demand[hour] = dhw_demand
            self.indoor_temperature[hour] = Office.t_air

            # self.total_heat_demand[hour] = Office.heating_demand + Office.dhw_demand  ## add again when dhw is solved


    def run_SIA_electricity_demand(self, occupancy_path):
        self.app_light_other_electricity_monthly_demand = dp.sia_electricity_per_erf_hourly(occupancy_path,
                                                                                            self.gebaeudekategorie_sia)


    def run_dynamic_emissions(self, emission_factor_type, grid_export_assumption='c'):
        """

        :return:
        """

        if not hasattr(self, 'heating_demand'):
            print(
                "Before you can calculate the dynamic emissions, you first have to run the dynamic heating simulation")
            quit()




        ### Too many ifs. TODO: simplify by adding into a single function or table.
        if emission_factor_type == 'annual':
            grid_emission_factors = dp.build_yearly_emission_factors(export_assumption=grid_export_assumption)
        elif emission_factor_type == 'monthly':
            grid_emission_factors = dp.build_monthly_emission_factors(export_assumption=grid_export_assumption)
        elif emission_factor_type == 'hourly':
            grid_emission_factors = dp.build_grid_emission_hourly(export_assumption=grid_export_assumption)
        elif emission_factor_type == 'SIA_380':
            grid_emission_factors = dp.build_yearly_emission_factors_sia()
        elif emission_factor_type == 'EU':
            grid_emission_factors = dp.build_yearly_emission_factors_eu()
        else:
            print("Type of emission factor was not sufficiently specified")
            exit(1)

        if self.heating_fossil_demand.any()>0:
            fossil_heating_emission_factors = dp.fossil_emission_factors(self.heating_system)
        else:
            fossil_heating_emission_factors = np.repeat(0, 8760)

        if self.cooling_fossil_demand.any()>0: # TODO: Check if cooling fossil demand is given in - or +
            fossil_cooling_emission_factors = dp.fossil_emission_factors(self.cooling_system)
        else:
            fossil_cooling_emission_factors = np.repeat(0, 8760)

        if self.dhw_fossil_demand.any() > 0:
            fossil_dhw_emission_factors = dp.fossil_emission_factors(self.dhw_heating_system)
        else:
            fossil_dhw_emission_factors = np.repeat(0,8760)

        # self.app_light_other_electricity_monthly_demand is per energy reference area in kWh
        # the dynamic model runs in not normalized energy and Wh
        self.electricity_demand = self.app_light_other_electricity_monthly_demand * self.energy_reference_area * 1000 +\
                                  self.heating_electricity_demand + self.dhw_electricity_demand +\
                                  self.cooling_electricity_demand

        net_electricity_demand = self.electricity_demand-self.pv_production
        net_electricity_demand[net_electricity_demand < 0.0] = 0.0
        self.net_electricity_demand = net_electricity_demand



        self.fossil_emissions = np.empty(8760)
        self.electricity_emissions = np.empty(8760)

        for hour in range(8760):
            self.fossil_emissions[hour] = (self.heating_fossil_demand[hour] * fossil_heating_emission_factors[hour]) + (
                        self.cooling_fossil_demand[hour] * fossil_cooling_emission_factors[hour]) + (
                                                      self.dhw_fossil_demand[hour] * fossil_dhw_emission_factors[hour])

            self.electricity_emissions[hour] = self.net_electricity_demand[hour] * grid_emission_factors[hour]


        self.operational_emissions = self.fossil_emissions + self.electricity_emissions




















""" hier unten ist eine veraltete Version, von der ich einige sniplets noch verwenden werde. Kann demnächst
gelöscht werden.
"""



def run_rc_asdfsimulation(external_envelope_area, window_area, room_width, room_depth, room_height,
                   thermal_capacitance_per_floor_area, u_walls, u_windows, ach_vent, ach_infl, ventilation_efficiency,
                   max_heating_energy_per_floor_area, max_cooling_energy_per_floor_area, pv_area, pv_efficiency,
                   pv_tilt, pv_azimuth, lifetime, strom_mix, weatherfile_path, grid_decarbonization_factors,
                   t_set_heating, t_set_cooling, annual_dhw_p_person, dhw_supply_temperature, use_type):


    Loc = Location(epwfile_path=weatherfile_path)




    ## Define constants

    gain_per_person = 100 # W per sqm (why is that per sqm when it says per person?)
    appliance_gains= 14 #W per sqm
    max_occupancy=50  # number of occupants (could be simplified by using area per person values)
    floor_area = room_width * room_depth


    Office = Building(window_area=window_area,
                    external_envelope_area=external_envelope_area,
                    room_depth=room_depth,
                    room_width=room_width,
                    room_height=room_height,
                    lighting_load=lighting_load,
                    lighting_control = lighting_control,
                    lighting_utilisation_factor=lighting_utilisation_factor,
                    lighting_maintenance_factor=lighting_maintenance_factor,
                    u_walls = u_walls,
                    u_windows = u_windows,
                    ach_vent=ach_vent,
                    ach_infl=ach_infl,
                    ventilation_efficiency=ventilation_efficiency,
                    thermal_capacitance_per_floor_area = thermal_capacitance_per_floor_area,
                    t_set_heating = t_set_heating,
                    t_set_cooling = t_set_cooling,
                    max_cooling_energy_per_floor_area=max_cooling_energy_per_floor_area[0],
                    max_heating_energy_per_floor_area=max_heating_energy_per_floor_area[0],
                    heating_supply_system=supply_system.ElectricHeating,
                    cooling_supply_system=supply_system.DirectCooler, # What can we choose here for purely electric case?
                    heating_emission_system=emission_system.FloorHeating,
                    cooling_emission_system=emission_system.AirConditioning,
                    dhw_supply_temperature=dhw_supply_temperature,)


    SouthWindow = Window(azimuth_tilt=0., alititude_tilt = 90.0, glass_solar_transmittance=0.5,
                         glass_light_transmittance=0.5, area =window_area)

    ## Define PV to this building

    RoofPV = PhotovoltaicSurface(azimuth_tilt=pv_azimuth, alititude_tilt = pv_tilt, stc_efficiency=pv_efficiency,
                         performance_ratio=0.8, area = pv_area)  # Performance ratio is still hard coded.


    ## Define occupancy
    occupancyProfile=pd.read_csv(r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator\auxiliary\occupancy_office.csv")




    ## Define embodied emissions: # In a later stage this could be included in the RC model "supply_system.py file"
    coeq_gshp = dp.embodied_emissions_heat_generation_kbob_per_kW("gshp")  # kgCO2/kW ## zusätzlich automatisieren
    coeq_borehole = dp.embodied_emissions_borehole_per_m() #kg/m
    coeq_ashp = dp.embodied_emissions_heat_generation_kbob_per_kW("ashp")  # kgCO2/kW ## zusätzlich automatisieren
    coeq_underfloor_heating = dp.embodied_emissions_heat_emission_system_per_m2("underfloor heating") #kg/m2
    coeq_pv = dp.embodied_emissions_pv_per_kW()  # kg/kWp
    coeq_el_heater = dp.embodied_emissions_heat_generation_kbob_per_kW("electric heater")  #kg/kW


    #electricity demand from appliances

    electric_appliances = dp.electric_appliances_sia(energy_reference_area=room_depth*room_width, type=use_type, value="ziel")


    #Starting temperature of the builidng:
    t_m_prev=20.0 # This is only for the very first step in therefore is hard coded.


    # hourly_emission_factors = dp.build_yearly_emission_factors(strom_mix)
    # hourly_emission_factors = dp.build_monthly_emission_factors(strom_mix)
    hourly_emission_factors = dp.build_yearly_emission_factors(strom_mix)
    hourly_emission_factors = hourly_emission_factors*grid_decarbonization_factors.mean()




    electricity_demand = np.empty(8760)
    pv_yield = np.empty(8760)
    total_heat_demand = np.empty(8760)
    heating_electricity_demand = np.empty(8760)
    heating_demand = np.empty(8760)
    cooling_electricity_demand = np.empty(8760)
    cooling_demand = np.empty(8760)
    solar_gains = np.empty(8760)
    indoor_temperature = np.empty(8760)


    for hour in range(8760):

        #Occupancy for the time step
        occupancy = occupancyProfile.loc[hour,'People'] * max_occupancy
        #Gains from occupancy and appliances
        internal_gains = occupancy*gain_per_person + appliance_gains*Office.floor_area

        # Domestic hot water schedule
        dhw_demand = annual_dhw_p_person/ occupancyProfile['People'].sum() * occupancy  # Wh

        #Extract the outdoor temperature in Zurich for that hour
        t_out = Loc.weather_data['drybulb_C'][hour]

        Altitude, Azimuth = Loc.calc_sun_position(latitude_deg=47.480, longitude_deg=8.536, year=2015, hoy=hour)

        SouthWindow.calc_solar_gains(sun_altitude = Altitude, sun_azimuth = Azimuth,
                                     normal_direct_radiation= Loc.weather_data['dirnorrad_Whm2'][hour],
                                     horizontal_diffuse_radiation = Loc.weather_data['difhorrad_Whm2'][hour])

        SouthWindow.calc_illuminance(sun_altitude = Altitude, sun_azimuth = Azimuth,
                                     normal_direct_illuminance = Loc.weather_data['dirnorillum_lux'][hour],
                                     horizontal_diffuse_illuminance = Loc.weather_data['difhorillum_lux'][hour])

        RoofPV.calc_solar_yield(sun_altitude = Altitude, sun_azimuth=Azimuth,
                               normal_direct_radiation=Loc.weather_data['dirnorrad_Whm2'][hour],
                               horizontal_diffuse_radiation=Loc.weather_data['difhorrad_Whm2'][hour])


        Office.solve_building_energy(internal_gains=internal_gains, solar_gains=SouthWindow.solar_gains,t_out=t_out,
                                     t_m_prev=t_m_prev, dhw_demand=dhw_demand)

        Office.solve_building_lighting(illuminance=SouthWindow.transmitted_illuminance, occupancy=occupancy)

        #Set the previous temperature for the next time step

        t_m_prev=Office.t_m_next



        heating_electricity_demand[hour] =Office.heating_sys_electricity  # unit? heating electricity demand
        cooling_electricity_demand[hour] = Office.cooling_sys_electricity  # unit?
        solar_gains[hour] = SouthWindow.solar_gains
        electricity_demand[hour] = Office.heating_sys_electricity + Office.dhw_sys_electricity + Office.cooling_sys_electricity  # in Wh
        pv_yield[hour]=RoofPV.solar_yield  # in Wh
        heating_demand[hour] = Office.heating_demand  # this is the actual heat emitted, unit?
        cooling_demand[hour] = Office.cooling_demand
        indoor_temperature[hour] = Office.t_air

        total_heat_demand[hour] = Office.heating_demand + Office.dhw_demand



    electricity_demand = electricity_demand + electric_appliances




    max_required_heating_per_floor_area = max(heating_demand)/floor_area  # W/m2
    max_required_cooling_per_floor_area = min(cooling_demand)/floor_area  # W/m2


    net_electricity_demand = np.subtract(electricity_demand, pv_yield)

    net_self_consumption = np.empty(8760)
    for hour in range(8760):
        net_self_consumption[hour] = min(pv_yield[hour], electricity_demand[hour])


    # this is the ratio of electricity used to electricity produced and thus the emissions that are allocated to the building.
    # This is highly questionable, meaning, it is discussed a lot
    embodied_pv_ratio = net_self_consumption.sum()/pv_yield.sum()



    net_operational_emissions = np.multiply(net_electricity_demand / 1000., hourly_emission_factors)
    operational_emissions = np.copy(net_operational_emissions)
    operational_emissions[operational_emissions < 0] = 0.00


    ## heat calculations:
    annual_normalized_heat_demand = heating_demand.sum()/1000 / floor_area

    print("Annual_normalized_heat_demand:")
    print(annual_normalized_heat_demand)


    ## embodied emissions:    DO NOT YET USE THIS PART OF THE SIMULATION!!!!!
    #
    # #PV
    # kwp_pv = RoofPV.area * RoofPV.efficiency # = kWp
    # pv_embodied = kwp_pv*coeq_pv
    #
    #
    # # direct electrical
    # embodied_direct = coeq_el_heater * np.percentile(heating_electricity_demand, 97.5)/1000. \
    #                   + pv_embodied * embodied_pv_ratio #_embodied emissions of the electrical heating system
    #
    # # ASHP
    # ashp_power = np.percentile(heating_el_demands_list[1],97.5)/1000. #kW
    # ashp_embodied = coeq_ashp*ashp_power # kgCO2eq
    # underfloor_heating_embodied = coeq_underfloor_heating * Office_2X.floor_area # kgCO2eq
    # embodied_ashp = ashp_embodied + underfloor_heating_embodied + pv_embodied*embodied_pv_ratio[1]
    #
    # # GSHP
    # borehole_depth = 20 #m/kW - entspricht einer spezifischen Entzugsleistung von 50W/m
    # gshp_power = np.percentile(heating_el_demands_list[2],97.5)/1000 #kW
    # gshp_embodied = coeq_gshp * gshp_power # kgCO2eq
    # # underfloor_heating_embodied = coeq_underfloor_heating * Office_2X.floor_area # kgCO2eq
    # borehole_embodied = coeq_borehole * borehole_depth * gshp_power
    # embodied_gshp = gshp_embodied + underfloor_heating_embodied + borehole_embodied + pv_embodied * embodied_pv_ratio[2]
    # embodied_emissions = np.array([embodied_direct, embodied_ashp, embodied_gshp])
    #
    #
    # # Annual for 25years lifetime
    # annual_embodied_emissions = embodied_emissions/lifetime
    # normalized_annual_embodied_emissions = annual_embodied_emissions/(room_width*room_depth)

    #### Total emissions
    annual_operational_emissions = operational_emissions.sum()
    normalized_annual_operational_emissions = annual_operational_emissions/(room_width*room_depth)

    # normalized_total_emissions = normalized_annual_embodied_emissions+normalized_annual_operational_emissions

    normalized_total_emissions = 0  # placeholder
    normalized_annual_embodied_emissions = 0  # placeholder




    return normalized_total_emissions, normalized_annual_operational_emissions, normalized_annual_embodied_emissions,\
           u_windows, u_walls, thermal_capacitance_per_floor_area, max_required_heating_per_floor_area,\
           max_required_cooling_per_floor_area, indoor_temperature




def comfort_assessment(indoor_temperature_time_series, comfort_range=[19.0, 25.0], discomfort_type="integrated"):
    """
    :param indoor_temperature_time_series: np.array or list of hourly indoor temperature values
    :param comfort_range: list or numpy array with lower and upper limit of comfort range for room temperature
    :return: Number of hours where Temperature is outside comfort zone
    """

    time_series = np.array(indoor_temperature_time_series)
    comfort_range[0]-=0.01 # This will eliminate stupid 19.9999999995 to be too cold for 20
    comfort_range[1]+=0.01
    hours_of_discomfort = []
    degree_hours_of_discomfort = []
    for j in range(time_series.shape[0]):
        low_temp = time_series[j][time_series[j]<comfort_range[0]]
        high_temp = time_series[j][time_series[j]>comfort_range[1]]

        # hours of discomfort
        if discomfort_type == "hod":
            hours_of_discomfort.append(len(low_temp) + len(high_temp))


        elif discomfort_type == "integrated":
            degree_hours_of_discomfort.append(sum(comfort_range[0] - low_temp) + sum(high_temp - comfort_range[1]))

    if discomfort_type == "hod":
        return hours_of_discomfort
    elif discomfort_type == "integrated":
        return degree_hours_of_discomfort

if __name__ == '__main__':
    pass
