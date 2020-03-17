import numpy as np
import pandas as pd
import os
import sys
sys.path.insert(1, r"C:\Users\walkerl\Documents\code\RC_BuildingSimulator\rc_simulator")
import supply_system


def embodied_emissions_heat_generation_kbob_per_kW(system_type):
    """
    This function takes a heat generation system type and returns the respective embodied emissions per kW of installed
    power.
    --> this function is very basic and needs to be improved.
    :param system_type: string of gshp, ashp, electric heater
    :return: float, embodied kgCO2 equivalent per kW of installed power
    """

    ## Define embodied emissions: # In a later stage this could be included in the RC model "supply_system.py file"
    if system_type == "gshp":
        coeq = 272.5 #kg/kW [KBOB 2016]
    elif system_type == "ashp":
        coeq = 363.75 #kg/kW [KBOB 2016]

    elif system_type == "electric heater":
        coeq = 7.2/5.0  #kg/kW [ecoinvent auxiliary heating unit production, electric, 5kW]

    else:
        print("Embodied emissions for this system type are not defined")
        pass

    return coeq

def embodied_emissions_borehole_per_m():

    coeq_borehole = 28.1 #kg/m[KBOB 2016]
    return coeq_borehole

def embodied_emissions_heat_emission_system_per_m2(em_system_type):

    if em_system_type == "underfloor heating":
        coeq_underfloor_heating = 5.06 #kg/m2 [KBOB]

    return coeq_underfloor_heating

def embodied_emissions_pv_per_kW():
    coeq_pv = 2080 # kg/kWp [KBOB 2016]
    return coeq_pv



def persons_from_area_sia(energy_reference_area, type=1):

    if type ==1:
        personenflache = 50.  # m2/p

    elif type == 3:
        personenflache = 14.

    occupants = energy_reference_area / personenflache
    return occupants


def electric_appliances_sia(energy_reference_area, type=1, value="standard"):
    """
    This function calculates the use of electric appliances according to SIA 2024
    :param energy_reference_area: float, m2, energy reference area of the room/building
    :param type: int, use type according to SIA2024
    :param value: str, reference value according to SIA choice of "standard", "ziel" and "bestand"
    :return: np.array of hourly electricity demand for appliances in Wh
    """
    if type==1:  # Typ 1 SIA Wohnen (1.1 MFH, 1.2 EFH)
        max_hourly = {"standard":8.0, "ziel": 4.0, "bestand":10.0}
        demand_profile = max_hourly[value] * np.repeat(
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.8, 0.2, 0.1, 0.1, 0.1, 0.1, 0.8, 0.2, 0.1, 0.1, 0.1, 0.2, 0.8, 1.0, 0.2,
             0.2, 0.2, 0.1], 365)
    elif type==3: #Typ 3 SIA Einzel-, Gruppenbüro
        max_hourly = {"standard": 7.0, "ziel": 3.0, "bestand": 15.0}
        demand_profile = max_hourly[value] * np.repeat(
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.6, 0.8, 1.0, 0.8, 0.4, 0.6, 1.0, 0.8, 0.6, 0.2, 0.1, 0.1, 0.1,
             0.1, 0.1, 0.1], 365)

    else:
        print("No demand schedule for electrical appliances has been defined for this case.")

    return demand_profile * energy_reference_area #Wh


def build_yearly_emission_factors(export_assumption="c"):

    choice = "TEF" + export_assumption
    emissions_df = pd.read_excel(r"C:\Users\walkerl\Documents\code\proof_of_concept\data\emission_factors_AC.xlsx",
                                 index="Time")
    emissions_df = emissions_df.set_index('Time')
    emissions_df.resample('Y').mean()
    #swiss
    hourly_emission_factor = np.repeat(emissions_df.resample('Y').mean()[choice].to_numpy(), 8760)/1000.0 #kgCO2eq/kWh

    return hourly_emission_factor

def build_yearly_emission_factors_sia():
    hourly_emission_factor = np.repeat(139, 8760) / 1000.0  # kgCO2eq/kWh SIA380
    return hourly_emission_factor

def build_yearly_emission_factors_eu():
    hourly_emission_factor = np.repeat(630, 8760) / 1000.0  # kgCO2eq/kWh www.co2-monitor.ch/de/information/glossar/
    return hourly_emission_factor

def build_monthly_emission_factors(export_assumption="c"):
    """
    This function creates simple monthly emission factors of the Swiss consumption mix based on the year 2015.
    It returns an hourly list of the monthly values. No input is needed. The list is generated here to omit hard coding
    values within the simulatin process.
    :return: np array of length 8760 with monthly emission factors on hourly resolution.
    """
    if export_assumption=="c":
        grid_emission_factor = {"jan": .1366, "feb": .1548, "mar": .1403, "apr": .1170, "may": .0578, "jun": .0716,
                                "jul": .0956, "aug": .1096, "sep": .1341, "oct": .1750, "nov": .1644, "dec": .1577}  # for TEFc (AC)

    elif export_assumption=="d":
        grid_emission_factor = {"jan": .1108, "feb": .1257, "mar": .1175, "apr": .0937, "may": .0400, "jun": .0463,
                                "jul": .0594, "aug": .0931, "sep": .1111, "oct": .1418, "nov": .1344, "dec": .1343}  # for TEFd (AC)

    else:
        "Choice of export assumption not valid"

    ## Factors above According to ST Alice Chevrier
    ## hours of the months:
    # jan:  0 - 743
    # feb:  744 - 1415
    # mar:  1440 - 2159
    # apr:  2160 - 2906
    # may:  2907 - 3623
    # jun:  3624 - 4343
    # jul:  4344 - 5087
    # aug:  5088 - 5831
    # sep:  5832 - 6551
    # oct:  6552 - 7295
    # nov:  7296 - 8015
    # dec:  8016 - 8759

    hourly_emission_factors = np.concatenate([
        np.repeat(grid_emission_factor["jan"], 744),
        np.repeat(grid_emission_factor["feb"], 672),
        np.repeat(grid_emission_factor["mar"], 744),
        np.repeat(grid_emission_factor["apr"], 720),
        np.repeat(grid_emission_factor["may"], 744),
        np.repeat(grid_emission_factor["jun"], 720),
        np.repeat(grid_emission_factor["jul"], 744),
        np.repeat(grid_emission_factor["aug"], 744),
        np.repeat(grid_emission_factor["sep"], 720),
        np.repeat(grid_emission_factor["oct"], 744),
        np.repeat(grid_emission_factor["nov"], 720),
        np.repeat(grid_emission_factor["dec"], 744)
    ])  # in g/kWh
    return hourly_emission_factors

def build_grid_emission_hourly(export_assumption="c"):
    emissions_df = pd.read_excel(r"C:\Users\walkerl\Documents\code\proof_of_concept\data\emission_factors_AC.xlsx")
    choice="TEF"+export_assumption
    hourly_emission_factors = emissions_df[choice].to_numpy()/1000.0
    return(hourly_emission_factors)

def fossil_emission_factors(system_type):
    """
     for now, wood and pellets are listed in these are also combustion based systems
     TODO: omit fossils and maybe only include pellets
    :param system_type:
    :return:
    """
    treibhausgaskoeffizient = {"Oil": 0.319, "Natural Gas": 0.249, "Wood": 0.020, "Pellets": 0.048}
    #kgCO2/kWh SIA380 2015 Anhang C Tab 5
    hourly_emission_factor = np.repeat(treibhausgaskoeffizient[system_type], 8760)  # kgCO2eq/kWh SIA380
    return hourly_emission_factor




def extract_wall_data(filepath, name="Betonwand, Wärmedämmung mit Lattenrost, Verkleidung", area=0,
                               type="GWP[kgCO2eq/m2]", ):
    """
    MAKE SURE TO HAVE THE RIGHT DIMENSIONS IN YOUR SOURCE FILE AND IN YOUR CALCULATION
    THIS FUNCTION HAS TO BE EXTENDED AND CONSOLIDATED
    :param filepath:
    :param name:
    :param area:
    :param type:
    :return:
    """
    data = pd.read_excel(filepath, header=0, index_col=1)
    if type == "U-value":
        return data[data["Bezeichnung"] == name][type][:1].values[0]

    elif area <=0:
        print("No wall area is specified for the calculation of the wall's embodied impact")
        return 0

    else:
        return(data[data["Bezeichnung"] == name][type][:1].values[0]*area)
        ## The zero is here for the moment becaues each element is included with 0.18 and 0.25m insulation.
        ## This way always the 0.18 version is chosen.



def extract_decarbonization_factor(grid_decarbonization_path, grid_decarbonization_until, grid_decarbonization_type,
                                   from_year, to_year):

    decarb_factors = pd.read_excel(grid_decarbonization_path, sheet_name=str(grid_decarbonization_until),
                                   header=[6,7], index_col=0)[grid_decarbonization_type]['Factor'].loc[from_year:to_year]

    return decarb_factors.to_numpy()

### This shows how to use the function:
# grid_decarbonization_until = 2050  # Choose from 2050, 2060 and 2080
# grid_decarbonization_type = 'linear'  # Choose from 'linear', exponential, quadratic, constant
# grid_decarbonization_path = r'C:\Users\walkerl\Documents\code\proof_of_concept\data\future_decarbonization\Decarbonization sceanrios.xlsx'
# from_year = 2019
# to_year = 2080
#
# extract_decarbonization_factor(grid_decarbonization_until, grid_decarbonization_type, from_year, to_year)


def translate_system_sia_to_rc(system):
    """
    These can be adapted if needed. At the moment all the combustion based systems are chosen to be new oil Boilers.
    This makes sense for the energy calculations. For the emission calculations the respective emission factors are
    chosen as "fossil emission factors" making it add up in the end.
    :param system:
    :return:
    """
    system_dictionary = {'Oil':supply_system.OilBoilerNew, 'Natural Gas':supply_system.OilBoilerNew ,
                         'Wood':supply_system.OilBoilerMed , 'Pellets':supply_system.OilBoilerNew,
                         'GSHP':supply_system.HeatPumpWater, 'ASHP':supply_system.HeatPumpAir,
                         'electric':supply_system.ElectricHeating}
    return system_dictionary[system]


def hourly_to_monthly(hourly_array):
    hours_per_month = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])*24
    monthly_values = np.empty(12)
    start_hour = 0

    for month in range(12):
        end_hour = start_hour+hours_per_month[month]
        monthly_values[month] = hourly_array[start_hour:end_hour].sum()
        start_hour = start_hour + hours_per_month[month]
    return monthly_values


def sia_electricity_per_erf_hourly(occupancy_path, gebaeudekategorie_sia):
        """
        This function distributes the electricity demand of SIA380-1 according tooccupancy schedules of SIA2024
        It is questionable if this is correct but probably a good first approximation.
        :param occupancy_path: the same occupancy path used for the RC model according to SIA 2024 where monthly and
        weekly schedules are combined.
        :return:
        """

        # Diese Angaben werden ebenfalls in runSIA380 verwendet und sollten früher oder später nach data_prep oder
        # in ein file verschoben werden.
        elektrizitatsbedarf = {1: 28., 2: 22., 3: 22., 4: 11., 5: 33., 6: 33., 7: 17., 8: 28., 9: 17., 10: 6., 11: 6.,
                               12: 56.}  # 380-1 Tab12

        occupancyProfile = pd.read_csv(occupancy_path)
        occupancy_factor = np.empty(8760)
        total = occupancyProfile['People'].sum()
        for hour in range(8760):
            occupancy_factor[hour] = occupancyProfile.loc[hour, 'People']/total

        return occupancy_factor * elektrizitatsbedarf[int(gebaeudekategorie_sia)]
