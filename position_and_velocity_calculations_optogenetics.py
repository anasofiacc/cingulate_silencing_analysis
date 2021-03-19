import numpy as np
import pandas as pd
import os
import re
import matplotlib.pyplot as plt
import seaborn as sns
from open_files import collect_data_from_one_or_multiple_csvs
from matplotlib.cbook import boxplot_stats

from collect_and_organize_position_data_optogenetics import get_position_and_run_info_in_multi_index_df
from boolean_position_masks_according_to_rat import get_boolean_position_masks_according_to_rat
from save_dfs_to_csv_files import save_df_list_into_csv, save_df_to_csv


def collect_and_save_position_data_for_posterior_analysis_all_rats(path):
    '''

    :param path:
    :return: Void.
    '''

    # Get folders in path
    path_folders = os.listdir(path)

    df_list = list()
    for folder in path_folders:
        folder_dir = os.path.join(path, folder)

        # Get rat name
        ratname = re.search(r"_(\w+#\d)", folder_dir)[1]
        rat_data = collect_and_organize_position_data_for_each_rat(folder_dir, ratname)
        rat_data['rat'] = ratname

        df_list.append(rat_data)

    all_data = pd.concat(df_list)
    save_df_to_csv(all_data, path, 'position_data_pruned_all_rats')


def collect_and_organize_position_data_for_each_rat(files_path, ratname):

    # Collect multi_index dataframe with position data from all sessions.
    # The Multi index divides data by session
    data = get_position_and_run_info_in_multi_index_df(files_path, specs_to_runs=True)
    # Calculate vx, vy, vtotal and remove velocity points > 120 cm /s
    # Create bins for data and filter x from start to choice point
    data = calculate_velocities_and_interpolate_high_velocity_points(data, ratname)

    return data


def calculate_velocities_and_interpolate_high_velocity_points(data, ratname):

    # Calculate deltas, x and y component velocity. With these, calculate the velocity:
    # the hypotenuse of x and y diff divided by delta timestamp.
    # Remove backward movements

    data = (data.assign(y_diff=lambda x: x['y'].diff(),
                        timestamp_diff=lambda x: x['timestamp'].diff().fillna(0))
                .assign(vx=lambda x: x['x_diff'] / x['timestamp_diff'],
                        vy=lambda x: x['y_diff'] / x['timestamp_diff'],
                        v=lambda x: (np.hypot(x['x_diff'], x['y_diff'])) / x['timestamp_diff'])
                .pipe(remove_and_interpolate_high_velocity_points))
               # .pipe(remove_backward_movements, ratname))

    return data


def remove_and_interpolate_high_velocity_points(data):

    # Velocities above 120 cm /s are not considered. They should be interpolated.
    high_vel_mask = (data['vx'] > 120) | (data['vy'] > 120) | (data['v'] > 120)

    data.loc[high_vel_mask, ['vx', 'vy', 'v']] = np.nan

    nr_high_vel_points = len(high_vel_mask[high_vel_mask == 1])
    print('NUMBER OF HIGH VELOCITY POINTS INTERPOLATED: ' + str(nr_high_vel_points))
    percentage_high_vel = nr_high_vel_points / len(data)
    print('% POINTS REMOVED: ' + str(percentage_high_vel))

    data = (data.interpolate(method='linear', limit=1)
                .dropna())

    return data


def remove_backward_movements(data, ratname):

    #  Backward movement in the x axis has a  threshold locomotion = 4cm/s and occurs in the central or rw arm
    central_mask, rw_mask, arm1_mask, arm2_mask = get_boolean_position_masks_according_to_rat(data, ratname)
    x1 = central_mask & (data['vx'] < -4)
    x2 = rw_mask & (data['vx'] > 4)
    x_backward_mask = x1 | x2

    print('% BACKWARD MOVEMENT POINTS REMOVED (CENTRAL + TO RW): ' + str(len(data[x_backward_mask]) / len(data)))

    # vy > 4 cm/s for the trajectory 1 arm and vy < -4 cm/s for the trajectory 2 arm
    y1 = arm1_mask & (data['vy'] > 4)
    y2 = arm2_mask & (data['vy'] < -4)
    y_backward_mask = y1 | y2

    print('% BACKWARD MOVEMENT POINTS REMOVED (ARMS): ' + str(len(data[y_backward_mask]) / len(data)))

    # Convert to NaN all points with backward movement
    data.loc[x_backward_mask, 'vx'] = np.nan
    data.loc[y_backward_mask, 'vy'] = np.nan

    # Remove NaNs
    data = data.dropna()

    return data



''' ------------------------------- LINEARIZED POSITION --------------------------------- '''


def create_position_bins(data, colname):
    bins = {
        'x':
            ['xbins', 'xbin_center'],
        'y':
            ['ybins', 'ybin_center'],
        'linear_position':
            ['linear_bins', 'linear_bin_center']
    }

    data[bins[colname][0]] = pd.cut(data[colname], 133)
    data[bins[colname][1]] = data[bins[colname][0]].apply(lambda x: x.mid)

    return data


def calculate_linear_position(data, files_path, ratname):

    data = (data.pipe(create_position_bins, 'x'),
            data.pipe(create_position_bins, 'y'),
            data.pipe(calculate_linear_position, files_path, ratname))

    data, distances = create_linearized_position(data, ratname)
    save_df_list_into_csv([data, distances],
                          files_path,
                          ratname,
                          ['position_data', 'distances'])


def create_linearized_position(data, ratname):

    # Collect boolean masks to fragment data position and create a linearized position
    central_mask, rw_mask, arm1_mask, arm2_mask = get_boolean_position_masks_according_to_rat(data, ratname)
    arms_mask = arm1_mask | arm2_mask

    data['linear_position'] = np.where(central_mask, data['x'], np.nan)
    data, distance_to_cp, cp_stamps, run_id = add_travelled_distance(data, arms_mask, 'y')
    data, distance_to_curves, curve_stamps, run_id = add_travelled_distance(data, rw_mask, 'x')
    print(distance_to_cp.head())
    print(distance_to_curves.head())
    data = (data.pipe(create_position_bins, 'linear_position')
                .dropna())

    distances = (pd.concat([run_id, distance_to_cp, cp_stamps, distance_to_curves, curve_stamps], axis=1)
                 .rename(columns={0: 'cp', 1: 'cp_stamps', 2: 'curves', 3: 'curves_stamps'}))

    return data, distances


def add_travelled_distance(data, position_mask, colname):

    data_pooled = data.groupby(['session', 'run_nr'])
    travelled_distances = []
    distance_stamps = []
    session = []
    run_nr = []

    for run in data_pooled.groups.keys():

        # Get data from given run
        run_data = data_pooled.get_group(run).dropna()
        # Collect max x value from run data
        distance = run_data['linear_position'].max()
        # Collect corresponding timestamp
        distance_stamp = (run_data.loc[run_data['linear_position'] == distance, 'timestamp']).iloc[0]
        distance_xy = run_data[colname].iloc[-1]

        c1 = position_mask
        c2 = data['run_nr'] == run[1]
        c3 = data.index.get_level_values('session') == run[0]
        criteria = c1 & c2 & c3

        data['linear_position'] = np.where(
            criteria,
            abs(distance_xy - data[colname]) + distance + 5,
            data['linear_position'])

        travelled_distances.append(distance)
        distance_stamps.append(distance_stamp)
        session.append(run[0])
        run_nr.append(run[1])

    distances = pd.Series(travelled_distances)
    distance_stamps = pd.Series(distance_stamps)

    run_id = pd.DataFrame({'session': session, 'run_nr': run_nr})

    return data, distances, distance_stamps, run_id


def remove_travelled_distance_outliers(data, distance_to_cp, distance_to_curves, run_id):

    distances = pd.concat([distance_to_cp, distance_to_curves], axis=1)
    distances = distances.rename(index=run_id, columns={0: 'cp', 1: 'curves'})

    sns.set(style="white")
    sns.boxplot(data=distances)
    plt.show()

    data, distances = get_distance_outliers_and_remove_runs(data, distances)

    return data, distances


def get_distance_outliers_and_remove_runs(data, distances):

    for col in distances.columns:
        outliers = boxplot_stats(distances[col]).pop(0)['fliers']
        print(col)
        print(outliers)
        for out in np.unique(outliers):

            i_outlier = (distances[distances[col] == out]).index.values
            distances = distances.drop(i_outlier)

            c1 = data['run_nr'] == i_outlier[0][1]
            c2 = data.index.get_level_values('session') == i_outlier[0][1]
            criteria = c1 & c2

            data['run_nr'] = np.where(criteria, np.nan, data['run_nr'])

    data = data.dropna()

    return data, distances


''' ---------------      LATENCIES CALCULATIONS     ------------------ '''


def calculate_latency_to_cp(files_path):

    # Collect position data and distances
    position = collect_data_from_one_or_multiple_csvs(files_path, "*position_data.csv")
    distances = collect_data_from_one_or_multiple_csvs(files_path, "*distances.csv")

    latencies = distances.drop(['curves', 'curves_stamps'], axis=1)

    cols = ['run_type', 'stim_condition', 'outcome', 'rat', 'first_stamps']
    latencies = pd.concat([latencies, pd.DataFrame(columns=cols)], sort=True)

    for session, run_nr in zip(latencies['session'],
                               latencies['run_nr']):

        run = position[(position.index.values == session) & \
                       (position['run_nr'] == run_nr)]

        # Collect timestamps
        mask = (latencies['session'] == session) & (latencies['run_nr'] == run_nr)
        latencies.loc[mask, ['first_stamps']] = run['timestamp'].iloc[0]

        # Collect other trial relevant info
        for col in cols[0:4]:
            latencies.loc[mask, col] = run[col].iloc[0]

        # Calculate the latency from start to CP
        latencies['cp_lat'] = latencies['cp_stamps'] - latencies['first_stamps']
        run_latency = latencies['cp_lat'].dropna().tail(1)

        if run_latency.iloc[0] > 30:

            position = position[~ ((position.index.values == session) &
                                (position['run_nr'] == run_nr))]

    latencies = latencies[latencies['cp_lat'] < 30]

    return latencies, position, distances


def calculate_freq_timeouts(df, cols_groupby):

    ''' Calculate the frequency of timeout runs in each group, given a list of column names to group by'''

    # Collecting the number of trials in each groupby group - now dividing also by rat
    total = df.groupby(cols_groupby)['cp_lat'].count()

    # Collecting the number of trials with latency to cp between 10 and 30 s (timeouts)
    timeout_mask = df['cp_lat'].between(10, 30)
    timeout_runs = df[timeout_mask]
    timeouts = timeout_runs.groupby(cols_groupby)['cp_lat'].count()

    # Calculate the proportion of timeouts per group
    freq_timeouts = timeouts/total
    freq_timeouts = freq_timeouts.reset_index()

    return freq_timeouts
