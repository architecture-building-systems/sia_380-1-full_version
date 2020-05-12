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
                 ventilation_volume_flow,
                 thermal_storage_capacity_per_floor_area,
                 korrekturfaktor_luftungs_eff_f_v,
                 height_above_sea,
                 heating_system,
                 cooling_system,
                 dhw_heating_system):

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
        self.ventilation_volume_flow = ventilation_volume_flow
        self.warmespeicherfahigkeit_pro_ebf = thermal_storage_capacity_per_floor_area
        self.korrekturfaktor_luftungs_eff_f_v = korrekturfaktor_luftungs_eff_f_v
        self.hohe_uber_meer = height_above_sea
        self.heating_system = heating_system
        self.cooling_system = cooling_system

        self.longitude = None
        self.latitude = None


        ### RC Simulator inputs (derive from other inputs as much as possible)
        ## So far the lighting load is still hard coded because it is not looked at and I don't know the source.
        lighting_load = 11.7  # [W/m2] (source?)
        lighting_control = 300.0  # lux threshold at which the lights turn on.
        lighting_utilisation_factor = 0.45
        lighting_maintenance_factor = 0.9

        self.window_area = self.windows[1].sum()  # sums up all window area
        self.external_envelope_area = self.walls[0].sum() + self.windows[1].sum() + self.roof[0].sum() + self.floor[0].sum()  # so far includes vertical envelope
        self.room_depth = np.sqrt(self.energy_reference_area)  # assumption: quadratic foot print, one story
        self.room_width = np.sqrt(self.energy_reference_area)  # assumption: quadratic foot print, one story
        self.room_height = 3 #m (for now a fixed value)
        self.lighting_load = lighting_load
        self.lighting_control = lighting_control
        self.lighting_utilisation_factor = lighting_utilisation_factor
        self.lighting_maintenance_factor = lighting_maintenance_factor
        self.u_opaque = ((self.walls[0]*self.walls[1]).sum() + (self.roof[0]*self.roof[1]).sum() + (self.floor[0]*self.floor[1]).sum()) / (self.walls[0].sum() + self.roof[0].sum() + self.floor[0].sum())  # weighted average of walls u-values
        self.u_windows = (self.windows[1]*self.windows[2]).sum() /self.windows[1].sum() # weighted average of window u-values for thermal calculation
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
        standard_raumtemperaturen = dp.sia_standardnutzungsdaten("room_temperature_heating")  # 380-1 Tab7
        warmeabgabe_p_p = dp.sia_standardnutzungsdaten("gain_per_person") # 380-1 Tab10 (W)

        elektrizitatsbedarf = dp.sia_standardnutzungsdaten("gains_from_electrical_appliances") # 380-1 Tab12 (kWh/m2a)
        reduction_factor_electricity = dp.sia_standardnutzungsdaten("reduction_factor_for_electricity")[int(self.gebaeudekategorie_sia)]

        personenflachen = dp.sia_standardnutzungsdaten("area_per_person")  # 380-1 Tab9
        presence_time_per_day = dp.sia_standardnutzungsdaten("presence_time")[int(self.gebaeudekategorie_sia)]


        aussenluft_strome = dp.sia_standardnutzungsdaten("effective_air_flow") # 380-1 Tab14
        # aussenluft_strome = {1:2.1}

        # in kWh/m2a according to SIA2024 possbily needs to be changed to SIA 385/2


        self.t_set_heating = standard_raumtemperaturen[int(self.gebaeudekategorie_sia)]
        Loc = Location(epwfile_path=weatherfile_path)
        self.longitude, self.latitude = dp.read_location_from_epw(weatherfile_path)
        gain_per_person = warmeabgabe_p_p[int(self.gebaeudekategorie_sia)]  # W/m2
        appliance_gains = elektrizitatsbedarf[int(self.gebaeudekategorie_sia)]/365.0/24.0*1000.0  # W per sqm (constant over the year)
        max_occupancy = self.energy_reference_area / personenflachen[int(self.gebaeudekategorie_sia)]

        if self.ventilation_volume_flow == "SIA":
            self.ach_vent = aussenluft_strome[int(self.gebaeudekategorie_sia)]/self.room_height  # here we switch from SIA m3/hm2 to air change rate /h

        else:
            self.ach_vent = self.ventilation_volume_flow/self.room_height  # m3/hm2 to air change rate

        heating_supply_system = dp.translate_system_sia_to_rc(self.heating_system)
        cooling_supply_system = dp.translate_system_sia_to_rc(self.cooling_system)
        self.annual_dhw_demand = dp.sia_annaul_dhw_demand(self.gebaeudekategorie_sia) * 1000  # Sia calculates in kWh, RC Simulator in Wh

        Office = Building(window_area=self.window_area,
                          external_envelope_area=self.external_envelope_area,  # opaque and glazed surfaces
                          room_depth=self.room_depth,
                          room_width=self.room_width,
                          room_height=self.room_height,
                          lighting_load=self.lighting_load,
                          lighting_control=self.lighting_control,
                          lighting_utilisation_factor=self.lighting_utilisation_factor,
                          lighting_maintenance_factor=self.lighting_maintenance_factor,
                          u_walls=self.u_opaque,  # average u_value of opaque surfaces that make up external_envelope_area
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

        windows = []
        for window_nr in range(len(self.windows[0])):

            azimuth_tilt = dp.string_orientation_to_angle_RC(self.windows[0,window_nr])
            Window_Component = Window(azimuth_tilt=azimuth_tilt, alititude_tilt=90.0,
                                      glass_solar_transmittance=self.windows[3,window_nr],
                                      glass_light_transmittance=0.5, area=self.windows[1,window_nr])

            windows.append(Window_Component)
            # SouthWindow = Window(azimuth_tilt=0., alititude_tilt=90.0, glass_solar_transmittance=self.g_windows,
            #                  glass_light_transmittance=0.5, area=self.window_area)  # az and alt are hardcoded because
            #                     they are assumed to be vertical south facing windows (IMPROVE!)



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
        self.internal_gains = np.empty(8760)


        for hour in range(8760):
            # Occupancy for the time step
            occupancy = occupancyProfile.loc[hour, 'People'] * max_occupancy
            # Gains from occupancy and appliances
            internal_gains = gain_per_person * (presence_time_per_day/ 24) * 8760 / occupancyProfile['People'].sum() * occupancy + appliance_gains * reduction_factor_electricity * Office.floor_area

            self.internal_gains[hour] = internal_gains

            # Domestic hot water schedule  ### add this in a later stage
            dhw_demand = self.annual_dhw_demand / occupancyProfile['People'].sum()\
                         * occupancyProfile.loc[hour, 'People'] * self.energy_reference_area # Wh

            # Extract the outdoor temperature in Zurich for that hour
            t_out = Loc.weather_data['drybulb_C'][hour]

            Altitude, Azimuth = Loc.calc_sun_position(latitude_deg=self.latitude, longitude_deg=self.longitude,
                                                      year=2015, hoy=hour)

            solar_gains=0
            transmitted_illuminance=0
            for Window_object in windows:
                Window_object.calc_solar_gains(sun_altitude=Altitude, sun_azimuth=Azimuth,
                                         normal_direct_radiation=Loc.weather_data['dirnorrad_Whm2'][hour],
                                         horizontal_diffuse_radiation=Loc.weather_data['difhorrad_Whm2'][hour])
                solar_gains += Window_object.solar_gains


                Window_object.calc_illuminance(sun_altitude=Altitude, sun_azimuth=Azimuth,
                                         normal_direct_illuminance=Loc.weather_data['dirnorillum_lux'][hour],
                                         horizontal_diffuse_illuminance=Loc.weather_data['difhorillum_lux'][hour])
                transmitted_illuminance += Window_object.transmitted_illuminance


            Office.solve_building_energy(internal_gains=internal_gains, solar_gains=solar_gains,
                                         t_out=t_out,
                                         t_m_prev=t_m_prev, dhw_demand=dhw_demand)

            Office.solve_building_lighting(illuminance=transmitted_illuminance, occupancy=occupancy)

            # Set the previous temperature for the next time step

            t_m_prev = Office.t_m_next


            self.heating_electricity_demand[hour] = Office.heating_sys_electricity  # unit? heating electricity demand
            self.heating_fossil_demand[hour] = Office.heating_sys_fossils
            self.cooling_electricity_demand[hour] = Office.cooling_sys_electricity  # unit?
            self.cooling_fossil_demand[hour] = Office.cooling_sys_fossils
            self.solar_gains[hour] = solar_gains
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
