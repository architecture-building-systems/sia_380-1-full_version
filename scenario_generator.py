import os
import pandas as pd
from itertools import product

main_path = os.path.abspath(os.path.dirname(__file__))

options_path = os.path.join(main_path, 'data', 'scenario_options.xlsx')
scenarios_path = os.path.join(main_path, 'data', 'scenarios.xlsx')

options = pd.read_excel(options_path)


options_list = []
for column_name in options.columns:
    options_list.append(options[column_name].dropna())


scenarios = pd.DataFrame(list(product(*options_list)), columns=options.columns)
scenarios.to_excel(scenarios_path, "scenarios")
