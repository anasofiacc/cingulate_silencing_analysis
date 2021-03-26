
import pandas as pd
import numpy as np
import os
import re
from file_lists import get_file_list, get_filenames_match_pattern_from_file_list
from assertion_error import check_assertion_error


def collect_and_organize_position_data(files_path):

    '''

    :param files_path: directory of the files containing the timestamps and position to be analyzed.
    :param attribute_specs_to_runs: if True, attribute information about run type, stim condition and outcome
    to each run (must be True only after manual inspection of runs and run specs file is created for all sessions).

    :return:  MultiIndex DataFrame with the levels session, run number and index. Contains x and y position and
            respective timestamps. Also included information about
            1)run type; 2) stimulation condition; 3) outcome information if attribute_specs_to_runs == True
    '''

    if isinstance(files_path, str):
        # Get all .csv files in directory (= files_path). Returns as Series.
        csv_files = get_file_list(files_path, "*.csv")

        # Use regular expressions to get lists of csv files with position data or respective timestamps.
        # Searches for file type and date of recording
        timestamp_files = get_filenames_match_pattern_from_file_list(csv_files, r'(_[A-Z]{2}_[A-Z]{10})', regex=True)
        position_files = get_filenames_match_pattern_from_file_list(csv_files, r'(_[A-Z]{8}_[A-Z]{8})', regex=True)

        timestamp_files.sort()
        position_files.sort()

        df_list = []
        # Collect timestamped position data for each session.
        for p, t in zip(position_files, timestamp_files):

            timestamped_position, session_code = collect_data_from_file_into_df(files_path, t, p)
            timestamped_position['session'] = session_code
            df_list.append(timestamped_position)

        # Concatenate all dfs (1 per session) to a single one
        data = pd.concat(df_list)

    return data


def collect_data_from_file_into_df(files_path, timestamp_filename, position_filename):
    '''
    Opens xy position and respective timestamps files. Stores data into a dataframe.
    Data is classified according to each rat run. Position and timestamp data is numbered according to run number.
    :param files_path: directory path to files to be open
    :param timestamp_filename: file name containing xy position timestamps of given session
    :param position_filename: file name containing xy position data of given session

    :return: Dataframe with data from one session, divided into 5 columns: timestamp, x, y, x_diff, run_nr
    '''

    # Find session code in position filename.
    match = re.search(r"((\d+-){2}\d+T(\d+_){2}\d+)", position_filename)
    session_code = match.group(0)

    # Find rat code in files_path.
    match = re.search(r"_(\w+\d+)", files_path)
    rat = match.group(1)

    # Reads timestamp csv file into a dataframe
    timestamps = pd.read_csv(os.path.join(files_path, timestamp_filename),
                             header=None, names=['timestamp'], delim_whitespace=True)

    position = pd.read_csv(os.path.join(files_path, position_filename),
                           header=None, names=['x', 'y'], delim_whitespace=True)

    print('\n Opening timestamps:%s. Length:%d'%(timestamp_filename, len(timestamps)))
    print('\n Opening position:%s. Length:%d'%(position_filename, len(position)))

    # Wrangles position and timestamp data to return a concatenated single dataframe
    timestamped_position = organize_session_data(timestamps, position, session_code, rat)

    return timestamped_position, session_code


def organize_session_data(timestamps, position, session_code, rat):

    '''
    Performs several data wrangling processes:
        - Interpolation of NaNs and zeros in position data
        - Check for length discrepancies in same session position and timestamp data.
        - Adds column ['run_nr'] that classifies data according to run number

    :param timestamps: session timestamp xy data
    :param position: session xy position data
    :param session_code: session code that identifies the session data.

    :return: Clean, interpolated single dataframe containing timestamps and xy position and datapoints labelled
    according to run number.
    '''

    # Interpolate NaN and zeros (loss of position data) in position dataframe
    position = (position.replace(0, np.nan)
                        .interpolate(method='linear', limit=5)

                        .fillna(0))

    # Number of data points in each session, in the position frame and timestamp frame must be equal
    check_assertion_error(len(timestamps) == len(position), '\n N points in session %s is different!\n'%session_code)

    # Convert timestamps to ms and reference it to the first timestamp (1st timestamp = 0)
    first_timestamp = timestamps.iloc[0]
    timestamps = (timestamps - first_timestamp) * 1e-7

    # Concatenate timestamps and position into a single 3 column, 2 x levels index DataFrame.
    timestamped_position = pd.concat([timestamps, position], axis=1)

    # Converts xy from pixels to cm. Then Label data points according to run number.
    for col in ['x', 'y']:
        timestamped_position[col] = (timestamped_position[col]*10)/50

    timestamped_position = (timestamped_position.pipe(prune_run_start, rat)
                            .pipe(divide_into_runs, session_code))

    return timestamped_position


def divide_into_runs(df, session_code):
    '''
    Labels each data point (timestamp - x - y) by run number. Each run the rat performs - sample or test - will be
    detected by consecutive x differences. Differences above a certain distance (in cm) will be considered a
    transition between runs and labelled accordingly with number starting in 1.
    :param df: dataframe with xy timestamped position data.
    :param session_code.
    :return: dataframe with xy timestamped position data labelled according to run number
    '''

    # Drop data from run 31 - session 2019-09-23 (Backward run) and run 44 - session 2019-08-20
    # Calculate difference between consecutive elements in 'x' and store them in new column 'x_diff'
    df = remove_erratic_points_according_to_session(df, session_code)
    df['x_diff'] = (df['x'].diff()).fillna(0)

    # Get indexes of elements below diff pxs in x position.
    diff = get_diff_according_to_session(session_code)

    # Get the run breaks, including the first and last index of the session
    run_breaks = df.head(1).index.tolist() + (df[df['x_diff'] < diff]).index.tolist() + df.tail(1).index.tolist()

    run_number = 1
    df['run_nr'] = np.NaN
    for i, j in zip(run_breaks, run_breaks[1:]):

        df.loc[i:j, 'run_nr'] = run_number
        run_number += 1

    return df


def get_diff_according_to_session(session_code):

    df = pd.read_csv("E:/POSITION DATA/RUN_BREAKS_EXCEPTIONS.csv")
    print(session_code)
    diff = df.loc[df['session'] == session_code, 'diff']
    print(diff)
    if diff.empty:

        diff = -100
    else:
        diff = diff.iloc[0]

    print(diff)
    return diff


def remove_erratic_points_according_to_session(df, session_code):

    if session_code == '2019-09-23T11_17_17':

        indices = df[(df['timestamp'] >= 954.0004607999999) & (df['timestamp'] <= 957.7860736)].index
        new_df = df.drop(indices)
        return new_df
    else:
        return df


def prune_run_start(df, rat):

    '''
    Remove position points before the rat crosses the start ROI limit
    :param df: timestamped position dataframe
    :param rat: rat code
    :return: DataFrame
    '''

    stim_roi = pd.read_csv("E:/MAZE_MEASURMENTS/STIM_ROI_XLIM_TO_RAT_MAPPING.csv", header=0)

    xlim = stim_roi.loc[stim_roi['rat'] == rat, ['stim_roi_x']]
    xlim = xlim['stim_roi_x'].iloc[0]

    df = df[df['x'] >= xlim]

    return df

