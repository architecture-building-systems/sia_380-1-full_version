import pandas as pd
import numpy as np
import plotly.express as px



pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 10)


classifier = "PV Area"


scenarios_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\scenarios_UBA.xlsx"
configurations_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\configurations_UBA.xlsx"
performance_matrix_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\performance_matrix_UBA_hourly.xlsx"


scenarios = pd.read_excel(scenarios_path)
configurations = pd.read_excel(configurations_path,  skiprows=[1])
performance_matrix = pd.read_excel(performance_matrix_path, index_col="Configuration")


""" Das kann später genutzt werden um alles in einer Tabelle zu haben:

# repeater = len(scenarios.index)
#
# all_configs = pd.DataFrame(configurations.values.repeat(repeater, axis=0), columns=configurations.columns)
#
# repeater = len(configurations.index)
# all_scenarios = pd.concat([scenarios]*repeater, ignore_index=True)
#
# all_data = pd.concat([all_configs, all_scenarios], axis=1)
#
# all_data.rename(columns={"Unnamed: 0":"Scenario"}, inplace=True)
#
# all_data["Performance"] = 0
#
#
# def performance_reader(row, performance_matrix):
#
#    return performance_matrix[row["Scenario"]][row["Configuration"]]
#
#
# all_data["Performance"] = all_data.apply(lambda row: performance_reader(row, performance_matrix), axis=1)
"""

### Add a scenario and a bla filter here.




all_data = pd.concat([configurations, performance_matrix], axis=1)
scenario_list = list(scenarios.index)
data_to_plot = all_data[scenario_list]
data_to_plot[classifier] = all_data[classifier]


fig = plt.figure(figsize=(12,10))
title= fig.suptitle("Performance in Scenarios", fontsize=18)
fig.subplots_adjust(top=0.93,wspace=0)

pc = parallel_coordinates(data_to_plot, classifier, colormap="Set2")
plt.ylabel("kgCO2 eq /m2 /a")
plt.xlabel("Scenario Number")

plt.show()
