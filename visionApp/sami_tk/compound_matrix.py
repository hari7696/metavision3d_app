import pandas as pd
import logging
import numpy as np
from PIL import Image
import pickle
from skimage.transform import resize

logger = logging.getLogger(__name__)


def create_compound_matrix(data, col="result", roi=False, reverse=False):
    # print(data.columns)
    data = data.dropna(subset=["tissue_id", col])
    # print(len(data))
    # print("df initial:",np.count_nonzero(data[col]))

    unique_tissue_ids = data["tissue_id"].unique()
    nslice = len(unique_tissue_ids)
    # print(nslice)
    # print(np.count_nonzero(data[col]))

    # matrix = np.zeros((nslice, 200, 250))
    matrix = {}
    # nslice = len(data.tissue_id.unique())
    # #print(nslice)
    # matrix = np.zeros((nslice, 200, 350))
    # for ii in range(matrix.shape[0]):
    for ii, slice in enumerate(data["tissue_id"].unique()):
        data_temp = create_slice_sami(data, slice, col=col, roi=roi, reverse=reverse)
        # print(np.count_nonzero(data_temp))
        # x_vals = int((200 - data_temp.shape[0])/2)
        # y_vals = int((250 - data_temp.shape[1])/2) #find the (x,y) of the start vertex, '/2' means put the slice in the center
        # matrix[ii, int(x_vals/2):int(x_vals/2)+data_temp.shape[0], int(y_vals/2):int(y_vals/2)+data_temp.shape[1]] = data_temp
        # matrix[ii, x_vals:x_vals+data_temp.shape[0], y_vals:y_vals+data_temp.shape[1]] = data_temp
        matrix[ii] = data_temp
        # #print(data_temp.shape)
        # plt.imshow(matrix[ii], cmap='gray')
        # plt.axis('off')
        # plt.show()
    zarray = np.zeros((nslice, 200, 350))
    for key in matrix:
        # print(zarray.shape[0] / matrix[key].shape[0])
        # print()
        scale_factor = min(
            zarray.shape[1] / matrix[key].shape[0],
            zarray.shape[2] / matrix[key].shape[1],
        )
        # print("Sacle",scale_factor)

        # Resize the image array
        resized_image = resize(
            matrix[key],
            (
                int(matrix[key].shape[0] * scale_factor),
                int(matrix[key].shape[1] * scale_factor),
            ),
            anti_aliasing=False,
        )

        # Calculate padding
        pad_row = (zarray.shape[1] - resized_image.shape[0]) // 2
        pad_col = (zarray.shape[2] - resized_image.shape[1]) // 2

        # Place the resized image into the center of the zero array with padding
        zarray[
            key,
            pad_row : pad_row + resized_image.shape[0],
            pad_col : pad_col + resized_image.shape[1],
        ] = resized_image
        # plt.imshow(zarray[key], cmap='gray')
        # plt.show()
    return zarray


def create_slice_sami(df_all, slice, col="result", roi=False, reverse=False):

    # df_temp = df_all[df_all['tissue_id'] == slice]
    if roi == False:
        df_temp = df_all[df_all["tissue_id"] == slice]
    else:
        # print("roiiii")
        df_temp = df_all[(df_all["tissue_id"] == slice) & df_all["roi"].notna()]
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

    for value, x_ind, y_ind in zip(df_temp[col], x_indices, y_indices):
        if not np.isnan(value):
            reshaped_matrix[x_ind, y_ind] = value

    return reshaped_matrix


if __name__ == "__main__":
    df = pd.read_csv(
        r"C:\Users\ghari\Documents\OPS\UI\metavision3d_app\data\brain_glycomics_raw.csv"
    )
    moolecules = df.columns[3:]
    ##print(df.columns)
    df = df.rename(columns={"region": "tissue_id"})
    temp = create_compound_matrix(df, moolecules[0], roi=False, reverse=True)
    # Pickle the temp variable
    with open("temp2.pkl", "wb") as f:
        pickle.dump(temp, f)
    # print(temp.shape)
