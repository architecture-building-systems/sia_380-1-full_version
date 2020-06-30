import pandas as pd
import numpy as np
import plotly.express as px




scenarios_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\scenarios_UBA.xlsx"
configurations_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\configurations_UBA.xlsx"
performance_matrix_path = r"C:\Users\walkerl\Documents\code\sia_380-1-full_version\data\Zwischenspeichern\Case_study_I\performance_matrix_UBA_hourly.xlsx"


scenarios = pd.read_excel(scenarios_path, index_col="Scenario")
configurations = pd.read_excel(configurations_path,  skiprows=[1], index_col="Configuration")
performance_matrix = pd.read_excel(performance_matrix_path, index_col="Configuration")




## Maximin
def maximin(performance_matrix, minimizing=False):

    if minimizing==False:
        min_vector = performance_matrix.min(axis=1)
        maximin = min_vector.max()
        maximin_scenario = min_vector.idxmax()

        print("Maximin:")
        print("Scenario: " + str(maximin_scenario))
        print("Value: " + str(maximin) + "\n")
        return(maximin_scenario, maximin)

    elif minimizing==True:
        max_vector = performance_matrix.max(axis=1)
        minimax = max_vector.min()
        maximin_scenario = max_vector.idxmin()

        print("Maximin:")
        print("Scenario: " + str(maximin_scenario))
        print("Value: " + str(minimax) + "\n")
        return (maximin_scenario, minimax)


def maximax(performance_matrix, minimizing=False):
    if minimizing == False:
        max_vector = performance_matrix.max(axis=1)
        maximax = max_vector.max()
        maximax_scenario = max_vector.idxmax()

        print("Maximax:")
        print("Scenario: " + str(maximax_scenario))
        print("Value: " + str(maximax) + "\n")
        return (maximax_scenario, maximax)

    elif minimizing==True:
        min_vector = performance_matrix.min(axis=1)
        minimin = min_vector.min()
        maximin_scenario = min_vector.idxmin()

        print("Maximax:")
        print("Scenario: " + str(maximin_scenario))
        print("Value: " + str(minimin) + "\n")
        return (maximin_scenario, minimin)



def hurwicz(performance_matrix, coefficient_of_pessimism, minimizing=False):

    if minimizing==False:
        max_vector = performance_matrix.max(axis=1)
        min_vector = performance_matrix.min(axis=1)
        hurwicz_vector = coefficient_of_pessimism * min_vector + (1.0-coefficient_of_pessimism)*max_vector
        hurwicz = hurwicz_vector.max()
        hurwicz_scenario = hurwicz_vector.idxmax()
        print("Hurwicz:")
        print("Scenario: " + str(hurwicz_scenario))
        print("Value: " + str(hurwicz) + "\n")

    elif minimizing==True:
        max_vector = performance_matrix.min(axis=1)
        min_vector = performance_matrix.max(axis=1)
        hurwicz_vector = coefficient_of_pessimism * min_vector + (1.0-coefficient_of_pessimism)*max_vector
        hurwicz = hurwicz_vector.min()
        hurwicz_scenario = hurwicz_vector.idxmin()
        print("Hurwicz:")
    print("Scenario: " + str(hurwicz_scenario))
    print("Value: " + str(hurwicz) + "\n")

    return (hurwicz_scenario, hurwicz)

def laplace_insufficient_reasoning(performance_matrix, minimizing=False):
    laplace_vector = performance_matrix.mean(axis=1)
    if minimizing==False:
        laplace = laplace_vector.max()
        laplace_scenario = laplace_vector.idxmax()

    elif minimizing==True:
        laplace = laplace_vector.min()
        laplace_scenario = laplace_vector.idxmin()

    return (laplace_scenario, laplace)

def minimax_regret(performance_matrix, minimizing=False):

    if minimizing==False:
        column_maxes = performance_matrix.max()
        regret_matrix = -(performance_matrix-column_maxes)
        max_regret_vector = regret_matrix.max(axis=1)
        if max_regret_vector.lt(0.0).any():
            print("negative regrets were simulated, check if you formulated your problem correctly")

        minimax_regret = max_regret_vector.min()
        minimax_regret_scenario = max_regret_vector.idxmin()


    if minimizing==True:
        column_mins = performance_matrix.min()
        regret_matrix = performance_matrix-column_mins
        max_regret_vector = regret_matrix.max(axis=1)
        print(max_regret_vector)
        if max_regret_vector.lt(0.0).any():
            print("negative regrets were simulated, check if you formulated your problem correctly")

        minimax_regret = max_regret_vector.min()
        minimax_regret_scenario = max_regret_vector.idxmin()


    return(minimax_regret_scenario, minimax_regret)

def percentile_based_skewness(performance_matrix, minimizing=False):
    q_ten = performance_matrix.quantile(0.1, axis=1)  # Ten percent percentile
    q_fifty = performance_matrix.quantile(0.5, axis=1)  # Median
    q_ninety = performance_matrix.quantile(0.9, axis=1)  # 90 percent percentile

    skew_vector = ((q_ninety+q_ten)/2 - q_fifty)/((q_ninety-q_ten)/2)

    if minimizing==False:
        max_skew = skew_vector.max()
        max_skew_position = skew_vector.idxmax()

        return(max_skew_position, max_skew)

    elif minimizing==True:
        min_skew = skew_vector.min()
        min_skew_position = skew_vector.idxmin()
        return (min_skew_position, min_skew)



def starrs_domain_criterion(performance_matrix, threshold, minimizing=False):

    if minimizing==False:
        pass_fail_matrix = (performance_matrix > threshold)*1

    elif minimizing==True:
        pass_fail_matrix = (performance_matrix < threshold) * 1

    score_vector = pass_fail_matrix.mean(axis=1)

    starr = score_vector.max()
    starr_scenario = np.argwhere(score_vector.to_numpy()==starr).flatten().tolist()
    if len(starr_scenario)==1:
        starr_scenario = starr_scenario[0]
    return(starr_scenario, starr)

