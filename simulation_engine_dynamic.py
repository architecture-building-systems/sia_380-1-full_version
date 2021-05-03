import sys
# sys.path.insert(1, r"/Users/alexandra/Dokumente/code/RC_BuildingSimulator/rc_simulator")
# sys.path.insert(1, r"C:\Users\LW_Simulation\Documents\RC_BuildingSimulator\rc_simulator")
sys.path.insert(1, r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator")
from building_physics import Building
import numpy as np
import pandas as pd
import data_prep as dp
from radiation import Location
import pvlib
import time

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
                 increased_ventilation_volume_flow,
                 thermal_storage_capacity_per_floor_area,
                 heat_pump_efficiency,
                 combustion_efficiency_factor,
                 korrekturfaktor_luftungs_eff_f_v,
                 height_above_sea,
                 shading_factor_hourly,
                 heating_system,
                 cooling_system,
                 heat_emission_system,
                 cold_emission_system,
                 dhw_heating_system,
                 heating_setpoint="SIA",
                 cooling_setpoint="SIA",
                 area_per_person="SIA",
                 has_mechanical_ventilation=False):

        ### Similar to SIA some are unecessary.
        self.gebaeudekategorie_sia = gebaeudekategorie_sia
        self.regelung = regelung
        self.windows = windows  # np.array of windows with |orientation|area|u-value|g-value|shading_f1|shading_f2|
        self.walls = walls  # np.array of walls with |area|u-value| so far, b-values are not possible
        self.roof = roof  # np.array of roofs with |area|u-value|
        self.floor = floor  # np.array of floowrs with |area|u-value|b-value|
        self.energy_reference_area = energy_reference_area  # One value, float
        self.anlagennutzungsgrad_wrg = heat_recovery_nutzungsgrad  # One value, float
        self.q_inf = infiltration_volume_flow  # m3/m2h
        self.ventilation_volume_flow = ventilation_volume_flow  # m3/m2h
        self.increased_ventilation_volume_flow = increased_ventilation_volume_flow  # m3/m2h
        self.warmespeicherfahigkeit_pro_ebf = thermal_storage_capacity_per_floor_area
        self.korrekturfaktor_luftungs_eff_f_v = korrekturfaktor_luftungs_eff_f_v
        self.hohe_uber_meer = height_above_sea
        self.shading_factor_hourly = shading_factor_hourly
        self.heating_system = heating_system
        self.cooling_system = cooling_system
        self.area_per_person = area_per_person
        self.has_mechanical_ventilation=has_mechanical_ventilation

        self.heat_emission_system = heat_emission_system
        self.cold_emission_system = cold_emission_system

        self.longitude = None
        self.latitude = None


        ### RC Simulator inputs (derive from other inputs as much as possible)
        ## So far the lighting load is still hard coded because it is not looked at and I don't know the source.
        lighting_load = 11.7  # [W/m2] (source?) This probably comes from SIA 2024: Offices (11.6)
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
        self.u_windows = (self.windows[1]*self.windows[2]).sum() /self.window_area # weighted average of window u-values for thermal calculation
        self.ach_vent = None
        self.ach_vent_high = self.increased_ventilation_volume_flow / self.room_height
        self.ach_infl = self.q_inf / self.room_height  # Umrechnung von m3/(h*m2) in 1/h
        self.ventilation_efficiency = self.anlagennutzungsgrad_wrg
        self.thermal_capacitance_per_floor_area = self.warmespeicherfahigkeit_pro_ebf
        self.t_set_heating = heating_setpoint
        self.t_set_cooling = cooling_setpoint
        self.heat_pump_efficiency = heat_pump_efficiency
        self.combustion_efficiency_factor = combustion_efficiency_factor

        self.dhw_supply_temperature = 60  # deg C fixed and hard coded

        self.dhw_heating_system = dhw_heating_system
        self.pv_production = None

        if cooling_system == 'None' or None:
            self.max_cooling_energy_per_floor_area = 0.0
        else:
            self.max_cooling_energy_per_floor_area = -np.inf

        if heating_system == 'None' or None:
            self.max_heating_energy_per_floor_area = 0.0
            self.heating_system = dhw_heating_system
        else:
            self.max_heating_energy_per_floor_area = np.inf


    def run_rc_simulation(self, weatherfile_path, occupancy_path, cooling_setpoint=None):
        """
        ACHTUNG. Im Vergleich zum SIA Modul sind hier im Moment noch Wh als output zu finden.
        :param weatherfile_path:
        :param occupancy_path:
        :return:
        """
        #TODO Remove cooling setpoint once validation is done
        if self.t_set_heating == "SIA":
            self.t_set_heating = standard_raumtemperaturen = dp.sia_standardnutzungsdaten('room_temperature_heating')[int(self.gebaeudekategorie_sia)]
        else:
            pass

        if cooling_setpoint != None:
            print("You use cooling setpoint as an input into ISO instead of the object definition. This version does no longer work.")
            quit()
        else:
            pass
        if self.t_set_cooling == "SIA":
            self.t_set_cooling = dp.sia_standardnutzungsdaten('room_temperature_cooling')
        else:
            pass

        if self.area_per_person == "SIA":
            personenflachen = dp.sia_standardnutzungsdaten('area_per_person')
        else:
            personenflachen = {int(self.gebaeudekategorie_sia):self.area_per_person}


        warmeabgabe_p_p = dp.sia_standardnutzungsdaten("gain_per_person") # 380-1 Tab10 (W)

        elektrizitatsbedarf = dp.sia_standardnutzungsdaten("gains_from_electrical_appliances") # 380-1 Tab12 (kWh/m2a)
        reduction_factor_electricity = dp.sia_standardnutzungsdaten("reduction_factor_for_electricity")[int(self.gebaeudekategorie_sia)]

        presence_time_per_day = dp.sia_standardnutzungsdaten("presence_time")[int(self.gebaeudekategorie_sia)]


        if self.ventilation_volume_flow == "SIA":
            self.ach_vent = dp.sia_standardnutzungsdaten("effective_air_flow")[int(self.gebaeudekategorie_sia)]/self.room_height  # here we switch from SIA m3/hm2 to air change rate /h
        else:
            self.ach_vent = self.ventilation_volume_flow/self.room_height  # m3/hm2 to air change rate


        Loc = Location(epwfile_path=weatherfile_path)

        self.longitude, self.latitude = dp.read_location_from_epw(weatherfile_path)
        gain_per_person = warmeabgabe_p_p[int(self.gebaeudekategorie_sia)]  # W/m2
        appliance_gains = elektrizitatsbedarf[int(self.gebaeudekategorie_sia)]/365.0/24.0*1000.0  # W per sqm (constant over the year)
        max_occupancy = self.energy_reference_area / personenflachen[int(self.gebaeudekategorie_sia)]

        heating_supply_system = dp.translate_system_sia_to_rc(self.heating_system)
        cooling_supply_system = dp.translate_system_sia_to_rc(self.cooling_system)
        heat_emission_system = dp.translate_heat_emission_system(self.heat_emission_system)
        cold_emission_system = dp.translate_heat_emission_system(self.cold_emission_system)

        self.annual_dhw_demand = dp.sia_annaul_dhw_demand(self.gebaeudekategorie_sia) * 1000  # Sia calculates in kWh, RC Simulator in Wh
        if self.dhw_heating_system == 'None' or None:
            self.annual_dhw_demand = 0.0
        else:
            pass

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
                          ach_vent_high = self.ach_vent_high,
                          ach_infl=self.ach_infl,
                          ventilation_efficiency=self.ventilation_efficiency,
                          thermal_capacitance_per_floor_area=self.thermal_capacitance_per_floor_area * 3600 * 1000,  # Comes as kWh/m2K and needs to be J/m2K
                          t_set_heating=self.t_set_heating,
                          t_set_cooling=self.t_set_cooling,  # maybe this can be added to the simulation object as well
                          max_cooling_energy_per_floor_area=self.max_cooling_energy_per_floor_area,
                          max_heating_energy_per_floor_area=self.max_heating_energy_per_floor_area,
                          heating_supply_system=heating_supply_system,
                          cooling_supply_system=cooling_supply_system,
                          heating_emission_system=heat_emission_system,
                          cooling_emission_system=cold_emission_system,
                          dhw_supply_temperature=self.dhw_supply_temperature,
                          heat_pump_efficiency = self.heat_pump_efficiency)

        ## Define occupancy
        occupancyProfile = pd.read_csv(occupancy_path)


        t_m_prev = 20.0  # This is only for the very first step in therefore it is hard coded.

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

        normal_direct_radiation = Loc.weather_data['dirnorrad_Whm2']
        horizontal_diffuse_radiation = Loc.weather_data['difhorrad_Whm2']
        global_horizontal_value = Loc.weather_data['glohorrad_Whm2']
        dni_extra = Loc.weather_data['extdirrad_Whm2']

        start = time.time()

        solar_zenith_deg, solar_azimuth_deg = dp.calc_sun_position(self.latitude, self.longitude)
        relative_air_mass = pvlib.atmosphere.get_relative_airmass(90 - solar_zenith_deg)
        solar_gains = 0
        window_tilt = 90.0
        for window in range(len(self.windows[0])):
            window_azimuth = dp.string_orientation_to_angle(self.windows[0][window])

            # The facotr 0.855 comes from SIA to account for shading and window frame and is included
            # here to ensure consistency to the SIA approach. (If this is continuously used, remove
            # from hard code.
            solar_gains += 0.855 * pvlib.irradiance.get_total_irradiance(window_tilt,
                                                                         window_azimuth,
                                                                         solar_zenith_deg,
                                                                         solar_azimuth_deg,
                                                                         normal_direct_radiation,
                                                                         global_horizontal_value,
                                                                         horizontal_diffuse_radiation,
                                                                         dni_extra=dni_extra,
                                                                         model="isotropic",
                                                                         airmass=relative_air_mass)['poa_global'] * \
                           self.windows[1][window] * self.windows[3][window] * self.shading_factor_hourly

        for hour in range(8760):
            # Occupancy for the time step
            occupancy = occupancyProfile.loc[hour, 'People'] * max_occupancy
            # Gains from occupancy and appliances
            internal_gains = gain_per_person * (presence_time_per_day/ 24) * 8760 / occupancyProfile['People'].sum() * \
                             occupancy + appliance_gains * reduction_factor_electricity * Office.floor_area

            self.internal_gains[hour] = internal_gains

            # Domestic hot water schedule  ### add this in a later stage
            dhw_demand = self.annual_dhw_demand / occupancyProfile['People'].sum()\
                         * occupancyProfile.loc[hour, 'People'] * self.energy_reference_area # Wh

            # Extract the outdoor temperature in Zurich for that hour
            t_out = Loc.weather_data['drybulb_C'][hour]


            Office.solve_building_energy(internal_gains=internal_gains, solar_gains=solar_gains[hour],
                                         t_out=t_out,
                                         t_m_prev=t_m_prev, dhw_demand=dhw_demand)

            # Set the previous temperature for the next time step
            t_m_prev = Office.t_m_next

            self.heating_electricity_demand[hour] = Office.heating_sys_electricity  # unit? heating electricity demand
            self.heating_fossil_demand[hour] = Office.heating_sys_fossils
            self.cooling_electricity_demand[hour] = Office.cooling_sys_electricity  # unit?
            self.cooling_fossil_demand[hour] = Office.cooling_sys_fossils
            self.electricity_demand[
                hour] = Office.heating_sys_electricity + Office.dhw_sys_electricity + Office.cooling_sys_electricity  # in Wh
            self.heating_demand[hour] = Office.heating_demand  # this is the actual heat emitted, unit?
            self.cooling_demand[hour] = Office.cooling_demand
            self.dhw_electricity_demand[hour] = Office.dhw_sys_electricity
            self.dhw_fossil_demand[hour] = Office.dhw_sys_fossils
            self.dhw_demand[hour] = dhw_demand
            self.indoor_temperature[hour] = Office.t_air

        self.solar_gains = solar_gains.to_numpy()
            # self.total_heat_demand[hour] = Office.heating_demand + Office.dhw_demand  ## add again when dhw is solved

    def run_SIA_electricity_demand(self, occupancy_path):
        self.app_light_other_electricity_monthly_demand = dp.sia_electricity_per_erf_hourly(occupancy_path,
                                                                                            self.gebaeudekategorie_sia,
                                                                                            self.has_mechanical_ventilation)



    def run_dynamic_emissions(self, emission_factor_source, emission_factor_source_UBP, emission_factor_type, grid_export_assumption='c'):
        """

        :return:
        """

        if not hasattr(self, 'heating_demand'):
            print(
                "Before you can calculate the dynamic emissions, you first have to run the dynamic heating simulation")
            quit()




        ### Too many ifs. TODO: simplify by adding into a single function or table.
        grid_emission_factors = dp.build_yearly_emission_factors(source=emission_factor_source, export_assumption=grid_export_assumption)
        grid_emission_factors_UBP = dp.build_yearly_emission_factors_UBP(source_UBP=emission_factor_source_UBP,
                                                                 export_assumption=grid_export_assumption)

        if self.heating_fossil_demand.any()>0:
            # Those factors come in kgCO2eq or UBP per kWh heating energy
            fossil_heating_emission_factors = dp.fossil_emission_factors(self.heating_system, self.combustion_efficiency_factor)
            fossil_heating_emission_factors_UBP = dp.fossil_emission_factors_UBP(self.heating_system, self.combustion_efficiency_factor)
        else:
            # This is necessary for the vectorized multiplication below
            fossil_heating_emission_factors = np.repeat(0, 8760)
            fossil_heating_emission_factors_UBP = np.repeat(0, 8760)

        if self.cooling_fossil_demand.any() > 0: # TODO: Check if cooling fossil demand is given in - or +
            fossil_cooling_emission_factors = dp.fossil_emission_factors(self.cooling_system, self.combustion_efficiency_factor)
            fossil_cooling_emission_factors_UBP = dp.fossil_emission_factors_UBP(self.cooling_system, self.combustion_efficiency_factor)
        else:
            fossil_cooling_emission_factors = np.repeat(0, 8760)
            fossil_cooling_emission_factors_UBP = np.repeat(0, 8760)

        if self.dhw_fossil_demand.any() > 0:
            fossil_dhw_emission_factors = dp.fossil_emission_factors(self.dhw_heating_system, self.combustion_efficiency_factor)
            fossil_dhw_emission_factors_UBP = dp.fossil_emission_factors_UBP(self.dhw_heating_system, self.combustion_efficiency_factor)
        else:
            fossil_dhw_emission_factors = np.repeat(0,8760)
            fossil_dhw_emission_factors_UBP = np.repeat(0, 8760)

        # self.app_light_other_electricity_monthly_demand is per energy reference area in kWh
        # the dynamic model runs in not normalized energy and Wh
        self.electricity_demand = self.app_light_other_electricity_monthly_demand * self.energy_reference_area * 1000 +\
                                  self.heating_electricity_demand + self.dhw_electricity_demand +\
                                  self.cooling_electricity_demand

        net_electricity_demand = self.electricity_demand-self.pv_production
        net_electricity_demand[net_electricity_demand < 0.0] = 0.0
        self.net_electricity_demand = net_electricity_demand


        self.fossil_emissions = np.empty(8760)
        self.fossil_emissions_UBP = np.empty(8760)
        self.electricity_emissions = np.empty(8760)
        self.electricity_emissions_UBP = np.empty(8760)

        for hour in range(8760):
            # The division by 1000 is necessary because RC models energy in Wh but the emission factors are given
            # in kgCO2 per kWh.
            self.fossil_emissions[hour] =((self.heating_fossil_demand[hour] * fossil_heating_emission_factors[hour]) +
                                          (self.cooling_fossil_demand[hour] * fossil_cooling_emission_factors[hour]) +
                                          (self.dhw_fossil_demand[hour] * fossil_dhw_emission_factors[hour]))/1000.0

            self.fossil_emissions_UBP[hour] = ((self.heating_fossil_demand[hour] * fossil_heating_emission_factors_UBP[hour]) +
                                               (self.cooling_fossil_demand[hour] * fossil_cooling_emission_factors_UBP[hour]) +
                                               (self.dhw_fossil_demand[hour] * fossil_dhw_emission_factors_UBP[hour])) / 1000.0

            self.electricity_emissions[hour] = (self.net_electricity_demand[hour] * grid_emission_factors[hour])/1000.0

            self.electricity_emissions_UBP[hour] = (self.net_electricity_demand[hour] * grid_emission_factors_UBP[hour]) / 1000.0


        self.operational_emissions = self.fossil_emissions + self.electricity_emissions
        self.operational_emissions_UBP = self.fossil_emissions_UBP + self.electricity_emissions_UBP


    def run_heating_sizing(self):
        # total energy per year divided by volllaststunden (SIA 2024; MFH) for heating
        # self.nominal_heating_power = self.heating_demand.sum()/830
        self.heating_hours = self.heating_demand[self.heating_demand >= 0.001]
        if self.heating_hours.size == 0:
            self.nominal_heating_power = 0.0
        else:
            self.nominal_heating_power = np.percentile(self.heating_hours, [99.5])

    def run_cooling_sizing(self):
        # total energy per year divided by volllaststunden (SIA 2024; MFH) for cooling
        # self.nominal_cooling_power = self.cooling_demand.min()
        # self.nominal_cooling_power = self.cooling_demand.sum()/650
        self.cooling_hours = self.cooling_demand[self.cooling_demand <= -0.001]

        if self.cooling_hours.any() > 0:
            self.nominal_cooling_power = np.percentile(abs(self.cooling_hours), [70])
        else:
            self.nominal_cooling_power = 0


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
