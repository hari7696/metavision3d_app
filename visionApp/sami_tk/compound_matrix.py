import pandas as pd
import logging
import numpy as np
from PIL import Image
import pickle
logger = logging.getLogger(__name__)


def create_slice_sami_skeleton(df_all,slice, col, roi=False,reverse = False):
    
    if roi == False:
        df_temp = df_all[df_all['tissue_id'] == slice]
    else:
        #print("roiiii")
        df_temp=df_all[(df_all['tissue_id'] == slice) & df_all['roi'].notna()]
    # print("df_temp:")

    # Get unique x and y values (rounded) and ensure they're numpy arrays
    x_values = np.around(df_temp['x'].to_numpy(), 0)
    y_values = np.around(df_temp['y'].to_numpy(), 0)
    unique_x = np.unique(x_values)
    unique_y = np.unique(y_values)
    
    cnt_x, cnt_y = len(unique_x), len(unique_y)
    reshaped_matrix = np.zeros((cnt_x, cnt_y))
    
    # Pre-calculate indices if possible
    x_indices = np.searchsorted(unique_x, x_values)
    y_indices = np.searchsorted(unique_y, y_values)
    
    for value, x_ind, y_ind in zip(df_temp[col], x_indices, y_indices):
        # if not np.isnan(value):
        reshaped_matrix[x_ind, y_ind] = 1

    return reshaped_matrix

def create_compound_matrix_sami_skeleton(data,col,roi=False,reverse=False):
    
    logger.debug("Creating compound matrix skeletion")
    logger.debug("Data shape: {}".format(data.shape))
    logger.debug("Data columns: {}".format(data.columns))
    data = data.dropna(subset=['tissue_id', col])
    logger.debug("Data shape after dropping na: {}".format(data.shape))

    unique_tissue_ids = data['tissue_id'].unique()
    nslice = len(unique_tissue_ids)

    matrix = {}
    for ii,slice in enumerate(unique_tissue_ids):
        data_temp = create_slice_sami_skeleton(data, slice,col=col, roi= roi,reverse=reverse)
        matrix[ii] = data_temp
    zarray = np.zeros((nslice,200,350))
    for key in matrix:

        scale_factor = min(zarray.shape[1] / matrix[key].shape[0], zarray.shape[2] / matrix[key].shape[1])
        # Resize the image array
        # resized_image = resize(matrix[key], (int(matrix[key].shape[0] * scale_factor), int(matrix[key].shape[1] * scale_factor)), anti_aliasing=False)
        image = Image.fromarray(matrix[key])
        new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
        resized = image.resize(new_size, Image.LANCZOS)
        resized_image = np.array(resized)
        # Calculate padding
        pad_row = (zarray.shape[1] - resized_image.shape[0]) // 2
        pad_col = (zarray.shape[2] - resized_image.shape[1]) // 2
    
        # Place the resized image into the center of the zero array with padding
        zarray[key,pad_row:pad_row+resized_image.shape[0], pad_col:pad_col+resized_image.shape[1]] = resized_image
        # plt.imshow(zarray[key], cmap='gray')
        # plt.show()
    return zarray

if __name__ == "__main__":
    df = pd.read_csv(r"C:\Users\ghari\Documents\OPS\UI\metavision3d_app\data\brain_glycomics_raw.csv")
    moolecules = df.columns[3:]
    print(df.columns)
    df = df.rename(columns={'region': 'tissue_id'})    
    temp = create_compound_matrix_sami_skeleton(df,moolecules[0], roi=False,reverse=True)
    # Pickle the temp variable
    with open('temp.pickle', 'wb') as f:
        pickle.dump(temp, f)
    print(temp.shape)