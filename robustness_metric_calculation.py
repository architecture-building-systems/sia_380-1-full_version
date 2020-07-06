import pandas as pd
import numpy as np
import plotly.express as px

import data_prep as dp




scenarios_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\scenarios_UBA.xlsx"
configurations_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\configurations_UBA.xlsx"
performance_matrix_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\performance_matrix_UBA_hourly.xlsx"


scenarios = pd.read_excel(scenarios_path, index_col="Scenario")
configurations = pd.read_excel(configurations_path,  skiprows=[1], index_col="Configuration")
performance_matrix = pd.read_excel(performance_matrix_path, index_col="Configuration")



print(dp.maximin(performance_matrix, minimizing=True))
print(dp.maximax(performance_matrix, minimizing=True))
print(dp.hurwicz(performance_matrix, 0.5, minimizing=True))
print(dp.laplace_insufficient_reasoning(performance_matrix, minimizing=True))
print(dp.minimax_regret(performance_matrix, minimizing=True))
print(dp.percentile_based_skewness(performance_matrix, minimizing=True))
print(dp.starrs_domain_criterion(performance_matrix, 20, minimizing=True))