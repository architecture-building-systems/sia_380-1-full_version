import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt
from pandas.plotting import parallel_coordinates


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 10)


classifier = "envelope type"


scenarios_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\scenarios_UBA.xlsx"
configurations_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\configurations_UBA.xlsx"
performance_matrix_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\performance_matrix_UBA_hourly.xlsx"


scenarios = pd.read_excel(scenarios_path)
configurations = pd.read_excel(configurations_path,  skiprows=[1])
performance_matrix = pd.read_excel(performance_matrix_path, index_col="Configuration")



repeater = len(scenarios.index)

all_configs = pd.DataFrame(configurations.values.repeat(repeater, axis=0), columns=configurations.columns)

repeater = len(configurations.index)
all_scenarios = pd.concat([scenarios]*repeater, ignore_index=True)

all_data = pd.concat([all_configs, all_scenarios], axis=1)

all_data.rename(columns={"Unnamed: 0":"Scenario"}, inplace=True)

all_data["Performance"] = 0


def performance_reader(row, performance_matrix):

   return performance_matrix[row["Scenario"]][row["Configuration"]]


all_data["Performance"] = all_data.apply(lambda row: performance_reader(row, performance_matrix), axis=1)

all_data.to_excel(r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\all_data.xlsx")




plot_data = all_data[all_data["weatherfile"]==r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zürich-2070-B1.epw"]
fig = px.parallel_categories(plot_data, dimensions=["envelope type", "heating system", "PV area", "window areas"],
                             color="Performance", color_continuous_scale="inferno_r" )
fig.update_layout(title="Scenario Performances based on Configuration")

# fig.show()

plot_data = all_data[all_data["weatherfile"]==r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zürich-hour_historic.epw"]
fig = px.parallel_categories(plot_data, dimensions=["envelope type", "heating system", "PV area", "window areas"],
                             color="Performance", color_continuous_scale="inferno_r" )
fig.update_layout(title="Scenario Performances based on Configuration")

# fig.show()


threshold = 5.5
plot_data = all_data[all_data["Performance"]<=threshold]
fig = px.parallel_categories(plot_data, dimensions=["envelope type", "heating system", "PV area", "window areas"],
                             color="Performance", color_continuous_scale="inferno_r" )
fig.update_layout(title="Scenario Performances based on Configuration")

# fig.show()



plot_data = all_data

plot_data["Performance"] = (plot_data["Performance"] <= threshold)*1
print(plot_data)
fig = px.parallel_categories(plot_data, dimensions=["envelope type", "heating system", "PV area", "window areas"],
                             color="Performance", color_continuous_scale="Bluered" )
fig.update_layout(title="Scenario Performances based on Configuration")

fig.show()

quit()



all_data.boxplot(column="Performance", by="envelope type")
plt.ylabel("Annual operational emissions in kgCO2eq")
# all_data.groupby(by="envelope type").boxplot(column="Performance", subplots=False)
plt.show()

all_data.boxplot(column="Performance", by="heating system")
plt.ylabel("Annual operational emissions in kgCO2eq")
plt.show()

all_data.boxplot(column="Performance", by="PV area")
plt.ylabel("Annual operational emissions in kgCO2eq")
plt.show()

all_data.boxplot(column="Performance", by="Configuration")
plt.ylabel("Annual operational emissions in kgCO2eq")
plt.show()

all_data.boxplot(column="Performance", by="Scenario")
plt.ylabel("Annual operational emissions in kgCO2eq")
plt.show()



all_data.boxplot(column="Performance", by="weatherfile")
plt.ylabel("Annual operational emissions in kgCO2eq")
plt.show()

all_data.boxplot(column="Performance", by="heating setpoint")
plt.ylabel("Annual operational emissions in kgCO2eq")
plt.show()


all_data.boxplot(column="Performance", by=["envelope type", "heating system"])
plt.ylabel("Annual operational emissions in kgCO2eq")
plt.show()

"""
all_data = pd.concat([configurations, performance_matrix], axis=1)
scenario_list = list(scenarios.index)
data_to_plot = all_data[scenario_list]
data_to_plot[classifier] = all_data[classifier]

print(all_data)


fig = plt.figure(figsize=(12,10))
title= fig.suptitle("Performance in Scenarios", fontsize=18)
fig.subplots_adjust(top=0.93,wspace=0)

pc = parallel_coordinates(all_data["envelope type"], classifier , colormap="tab10")
plt.ylabel("kgCO2 eq /m2 /a")
plt.xlabel("Scenario Number")

plt.show()
"""