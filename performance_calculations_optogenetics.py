import numpy as np
import pandas as pd
import os
import re
from file_lists import get_file_list

""" -------------------------- FUNCTIONS TO COLLECT PERFORMANCE DATA  ------------------------------- """


def organize_folder_directories_and_get_performance_data(main_path, conditions_to_plot):
    """
    Organize the directories from the main path to the experimental group folders.
    For each experimental group (CTRL or EXP) collects each rat's performance given stimulation condition data, for all
    sessions.

    :param main_path: path where data is stored
    :param conditions_to_plot: list. which conditions to plot
    :return: Pandas DataFrame
    """

    # Get folder names of main path:
    folders = os.listdir(main_path)
    folders_dirs = list()

    # Create a path for each experimental group folder (main path + condition folder):
    for i in folders:

        folders_dirs.append(os.path.join(main_path, i))

    # For each experimental group (CTRL or EXP), collect performance given stimulation condition (all sessions) per rat
    for folder in folders_dirs:

        # For the control group rats
        if 'CTRL' in folder:
            ctrl_data_all_rats = get_performance_given_stim_condition_data(
                folder,
                conditions_to_plot
            )

        # For the experimental group rats
        elif 'NPHR' in folders:
            exp_data_all_rats = get_performance_given_stim_condition_data(
                folder,
                conditions_to_plot
            )

    return ctrl_data_all_rats, exp_data_all_rats


def get_performance_given_stim_condition_data(group_folder_path, conditions_to_plot):

    """
    Collects performance given stimulation condition per rat inside the given experimental group in folder
    in the group folder path

    :param group_folder_path: Path to experimental group folder. Inside this folder (CTRL or EXP) the rat folders exist,
    containing the behavioral performance data of each individual rat
    :param conditions_to_plot: List of conditions to plot
    :return: Pandas Dataframe containing the performance data given stimulation condition, of all rats inside
     the group folder
    """

    # Get directories of each rat folder inside group folder (condition folders: CTRL, EXP)
    rat_folders = os.listdir(group_folder_path)
    rat_folders_path = list()

    # Add each rat folders path to rat_folders list
    for i in rat_folders:

        rat_folders_path.append(os.path.join(group_folder_path, i))

    rat_id = list()
    data_all_rats_list = list()
    # For each subject, calculate performance given stimulation condition for all sessions
    for rat in rat_folders_path:

        id = re.search(r"(\w+\d)", rat)
        print(id)
        #rat_id.append(id[0])

        data_per_rat = calculate_performance_per_session_stim(rat, conditions_to_plot)
        data_per_rat['ratcode'] = id[0]

        # Concatenate data from individual subjects to data_all_rats dataframe
        data_all_rats_list.append(data_per_rat)

    data_all_rats = pd.concat(data_all_rats_list, names=['#'])

    return data_all_rats


def calculate_performance_per_session_stim(path, conditions_to_plot):

    file_list = get_file_list(path, '*.csv')
    file_list.sort()

    stim = list()
    performance = list()

    for filename in file_list:

        session = pd.read_csv(os.path.join(path, filename), names=['SAMPLE', 'STIM', 'OUTCOME'], header=None)
        counts_stim_outcome = session.groupby(['STIM', 'OUTCOME']).size()
        counts_stim = session['STIM'].value_counts()

        for condition in conditions_to_plot:

            if condition in counts_stim.index:

                performance.append(counts_stim_outcome.loc[(condition, 1)]/(counts_stim.loc[condition]))
                stim.append(condition)

    performance = pd.DataFrame({'stim': stim, 'perf': performance})

    return performance



