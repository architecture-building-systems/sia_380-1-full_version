import pandas as pd
import matplotlib.pyplot as plt
from pandas.plotting import parallel_coordinates


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 10)


classifier = "u-value wall"


scenarios_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\scenarios.xlsx"
configurations_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\configurations.xlsx"
performance_matrix_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\performance_matrix.xlsx"


scenarios = pd.read_excel(scenarios_path)
configurations = pd.read_excel(configurations_path,  skiprows=[1])
performance_matrix = pd.read_excel(performance_matrix_path, index_col="Configuration")


all_data = pd.concat([configurations, performance_matrix], axis=1)
scenario_list = list(scenarios.index)
data_to_plot = all_data[scenario_list]
data_to_plot[classifier] = all_data[classifier]


fig = plt.figure(figsize=(12,10))
title= fig.suptitle("Performance in Scenarios", fontsize=18)
fig.subplots_adjust(top=0.93,wspace=0)

pc = parallel_coordinates(data_to_plot, classifier)

plt.show()