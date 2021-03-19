import pandas as pd
import os
from file_lists import get_file_list


def open_csv_to_series_or_df(filename_path, column_names):

    '''
    Opens a csv file and uploads it to a pandas dataframe or series
    Returns this dataframe. DATA in FILENAME should be organized by columns.
    PARAMETERS: FILENAME COLUMN NAMES
    FILENAME - List of CSV files (returned by get_file_list);
    COLUMN NAMES - List. Header names for each column of dataframe.
    '''

    data = pd.read_csv\
        (filename_path,
         header=None,
         names=column_names,
         delim_whitespace=True)

    return data


def collect_data_from_one_or_multiple_csvs(files_path, file_type):

    files = get_file_list(files_path, file_type)
    df_list = []

    for i in files:
        path = os.path.join(files_path, i)
        df = pd.read_csv(path, header=0, index_col=[0])
        df_list.append(df)

    data = pd.concat(df_list)
    return data