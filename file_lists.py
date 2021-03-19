import os
import glob
import pandas as pd


def get_file_list(path, filetype):
    # Opens a list containing all filenames of file type in path with

    os.chdir(path)

    for filename in sorted(glob.glob(filetype), key=os.path.getmtime):
        # Add all file names from session path to file list

        try:
            file_list.append(filename)

        except:
            file_list = list()
            file_list.append(filename)

    return file_list


def get_filenames_match_pattern_from_file_list(files, pattern, regex):

    ''' ---------------------------------------------------------------------------
    Returns indexes of csv_files elements matching the given regular expression
    Arguments:
        a) files: a list of filenames;
        b) regular_expression to match against the filenames in csv_files.
        c) regex: if True, regular expression matching is used. If False, string matching is used

    Returns: A list containing subsample from files that match the given regex
    ----------------------------------------------------------------------------'''
    files = pd.Series(files)

    if regex == True:
        match_files = files.str.extract(pattern).dropna()
        indices = match_files.index.values
        indices.sort()

    else:
        match_files = files.str.contains(pattern, regex=False)
        indices = (match_files[match_files == True]).index.values

    file_list = list()

    for i in indices:
        file_list.append(files[i])

    return file_list
