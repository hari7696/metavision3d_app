import pandas as pd
import logging
import numpy as np
import pickle
from skimage.transform import resize
import logging
logger = logging.getLogger(__name__)


def create_compound_matrix(data, col="result", roi=False, reverse=False):

    id_to_name = {}
    # print(data.columns)
    data = data.dropna(subset=["region", col])
    # print(len(data))
    # print("df initial:",np.count_nonzero(data[col]))

    unique_tissue_ids = data["region"].unique()
    nslice = len(unique_tissue_ids)
    # print(nslice)
    # print(np.count_nonzero(data[col]))

    # matrix = np.zeros((nslice, 200, 250))
    matrix = {}
    # nslice = len(data.tissue_id.unique())
    # #print(nslice)
    # matrix = np.zeros((nslice, 200, 350))
    # for ii in range(matrix.shape[0]):
    highest_x = 0
    highest_y = 0
    for ii, slice in enumerate(data["region"].unique()):
        data_temp = create_slice_sami(data, slice, col=col, roi=roi, reverse=reverse)
        matrix[ii] = data_temp
        if data_temp.shape[0] > highest_x:
            highest_x = data_temp.shape[0]
        if data_temp.shape[1] > highest_y:
            highest_y = data_temp.shape[1]
        id_to_name[ii] = slice

    # zarray = np.zeros((nslice, 1500, 1500))
    # highest_x = highest_x + 10
    # highest_y = highest_y + 10
    # if highest_x > 2000:
    #     highest_x = 2010
    # if highest_y > 2000:
    #     highest_y = 2010

    zarray_high_res = np.zeros((nslice, 2000, 2000))
    zarray_high_res = zarray_high_res.astype(np.float16)

    # for key in matrix:

    #     scale_factor = min(
    #         zarray.shape[1] / matrix[key].shape[0],
    #         zarray.shape[2] / matrix[key].shape[1],
    #     )
    #     # scale_factor = scale_factor * 0.8
    #     # print(scale_factor  )
    #     # print(matrix[key].shape)
    #     # Resize the image array
    #     resized_image = resize(
    #         matrix[key],
    #         (
    #             int(matrix[key].shape[0] * scale_factor),
    #             int(matrix[key].shape[1] * scale_factor),
    #         ),
    #         anti_aliasing=False,
    #     )
    #     # Calculate padding
    #     pad_row = (zarray.shape[1] - resized_image.shape[0]) // 2
    #     pad_col = (zarray.shape[2] - resized_image.shape[1]) // 2

    #     # Place the resized image into the center of the zero array with padding
    #     zarray[
    #         key,
    #         pad_row : pad_row + resized_image.shape[0],
    #         pad_col : pad_col + resized_image.shape[1],
    #     ] = resized_image

    for key in matrix:

        scale_factor = min(
            zarray_high_res.shape[1] / matrix[key].shape[0],
            zarray_high_res.shape[2] / matrix[key].shape[1],
        )
        # print(scale_factor  )
        # print(matrix[key].shape)
        # Resize the image array
        resized_image = matrix[key]
        resized_image = resize(
            matrix[key],
            (
                int(matrix[key].shape[0] * scale_factor*0.9),
                int(matrix[key].shape[1] * scale_factor*0.9),
            ),
            anti_aliasing=False,
        )
        # Calculate padding
        pad_row = (zarray_high_res.shape[1] - resized_image.shape[0]) // 2
        pad_col = (zarray_high_res.shape[2] - resized_image.shape[1]) // 2
        # Place the resized image into the center of the zero array with padding
        zarray_high_res[
            key,
            pad_row : pad_row + resized_image.shape[0],
            pad_col : pad_col + resized_image.shape[1],
        ] = resized_image

    zarray_high_res = zarray_high_res.astype(np.float16)
    return None, zarray_high_res, id_to_name


def create_slice_sami(df_all, slice, col="result", roi=False, reverse=False):

    # df_temp = df_all[df_all["region"] == slice]
    if roi == False:
        df_temp = df_all[df_all["region"] == slice]
    else:
        # print("roiiii")
        df_temp = df_all[(df_all["region"] == slice) & df_all["roi"].notna()]
    # print("df_temp:")
    # print("df_temp:")

    # Get unique x and y values (rounded) and ensure they're numpy arrays
    x_values = np.around(df_temp["x"].to_numpy(), 0)
    y_values = np.around(df_temp["y"].to_numpy(), 0)
    unique_x = np.unique(x_values)
    unique_y = np.unique(y_values)

    cnt_x, cnt_y = len(unique_x), len(unique_y)

    # print("No. of unique x values:", cnt_x)
    # print("No. of unique y values:", cnt_y)

    reshaped_matrix = np.zeros((cnt_x, cnt_y))

    # Pre-calculate indices if possible
    x_indices = np.searchsorted(unique_x, x_values)
    y_indices = np.searchsorted(unique_y, y_values)

    for value, x_ind, y_ind in zip(df_temp[col].astype(np.float16),  y_indices, x_indices):
        #print(x_ind, y_ind, value)
        if not np.isnan(value):
            reshaped_matrix[ y_ind, x_ind] = float(value)

    reshaped_matrix = reshaped_matrix.astype(np.float16)
    return reshaped_matrix


if __name__ == "__main__":
    df = pd.read_csv(
        r"C:\Users\ghari\Documents\OPS\UI\metavision3d_app\data\brain_glycomics_raw.csv"
    )
    moolecules = df.columns[3:]
    ##print(df.columns)
    df = df.rename(columns={"region": "region"})
    temp = create_compound_matrix(df, moolecules[0], roi=False, reverse=True)
    # Pickle the temp variable
    with open("temp2.pkl", "wb") as f:
        pickle.dump(temp, f)
    # print(temp.shape)
