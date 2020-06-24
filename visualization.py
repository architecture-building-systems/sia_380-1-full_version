import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pandas.plotting import parallel_coordinates


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 10)


classifier = "heating system"


scenarios_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\scenarios.xlsx"
configurations_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\configurations.xlsx"
performance_matrix_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\performance_matrix.xlsx"


scenarios = pd.read_excel(scenarios_path)
configurations = pd.read_excel(configurations_path,  skiprows=[1])
performance_matrix = pd.read_excel(performance_matrix_path, index_col="Configuration")


print(configurations.index)
print(scenarios.index)

repeater = len(scenarios.index)

all_configs = pd.DataFrame(configurations.values.repeat(repeater, axis=0), columns=configurations.columns)

repeater = len(configurations.index)
all_scenarios = pd.concat([scenarios]*repeater, ignore_index=True)

all_data = pd.concat([all_configs, all_scenarios], axis=1)

all_data.rename(columns={"Unnamed: 0":"Scenario"}, inplace=True)


def func(x, y):
    return performance_matrix[x][y]

all_data["Performance"] = performance_matrix[all_data['Scenario']][all_data['Configuration']]


print(all_data)




"""
all_data = pd.concat([configurations, performance_matrix], axis=1)
scenario_list = list(scenarios.index)
data_to_plot = all_data[scenario_list]
data_to_plot[classifier] = all_data[classifier]


fig = plt.figure(figsize=(12,10))
title= fig.suptitle("Performance in Scenarios", fontsize=18)
fig.subplots_adjust(top=0.93,wspace=0)

pc = parallel_coordinates(data_to_plot, classifier)

plt.show()
"""