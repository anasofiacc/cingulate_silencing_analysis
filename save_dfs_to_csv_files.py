import os


def save_df_list_into_csv(df_list, path, ratname, filename_list):

    for df, filename in zip(df_list, filename_list):

        save_df_to_csv(df, path, ratname, filename)


def save_df_to_csv(df, path, filename):

    final_file_name = filename+'.csv'
    file_path = os.path.join(path, final_file_name)

    df.to_csv(file_path, header=True, index=True)
