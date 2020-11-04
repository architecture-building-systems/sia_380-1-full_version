import os
import pandas as pd
from itertools import product

"""
This file is used to sample scenarios from the given scenario approaches. At the moment the full factorial approach is 
used, meaning that all possible combinations are "built". At a later stage a smarter way of sampling can be introduced.
"""

main_path = os.path.abspath(os.path.dirname(__file__))

options_path = os.path.join(main_path, 'data', 'scenario_options.xlsx')
scenarios_path = os.path.join(main_path, 'data', 'scenarios.xlsx')

options = pd.read_excel(options_path)


options_list = []
for column_name in options.columns:
    options_list.append(options[column_name].dropna())


scenarios = pd.DataFrame(list(product(*options_list)), columns=options.columns)
scenarios.to_excel(scenarios_path, "scenarios")
