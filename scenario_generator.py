import pandas as pd
import numpy as np
from itertools import product

options_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\scenario_options.xlsx"
scenarios_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\scenarios.xlsx"

options = pd.read_excel(options_path)


options_list = []
for column_name in options.columns:
    options_list.append(options[column_name].dropna())


scenarios = pd.DataFrame(list(product(*options_list)), columns=options.columns)
scenarios.to_excel(scenarios_path, "scenarios")
