import numpy as np
from PIL import Image
from skimage.transform import resize

def create_compound_matrix_sami(data,col='result',roi=False,reverse=False):
    print(len(data))
    data = data.dropna(subset=['tissue_id', col])
    print(len(data))
    print("df initial:",np.count_nonzero(data[col]))
    
    unique_tissue_ids = data['tissue_id'].unique()
    nslice = len(unique_tissue_ids)
    print(nslice)
    print(np.count_nonzero(data[col]))
    
    # matrix = np.zeros((nslice, 200, 250))
    matrix = {}
    # nslice = len(data.tissue_id.unique())
    # print(nslice)
    # matrix = np.zeros((nslice, 200, 350))
    # for ii in range(matrix.shape[0]):
    for ii,slice in enumerate(data['tissue_id'].unique()):
        data_temp = create_slice_sami(data, slice,col=col, roi=roi,reverse=reverse)
        print(np.count_nonzero(data_temp))
        # x_vals = int((200 - data_temp.shape[0])/2) 
        # y_vals = int((250 - data_temp.shape[1])/2) #find the (x,y) of the start vertex, '/2' means put the slice in the center
        #matrix[ii, int(x_vals/2):int(x_vals/2)+data_temp.shape[0], int(y_vals/2):int(y_vals/2)+data_temp.shape[1]] = data_temp
        # matrix[ii, x_vals:x_vals+data_temp.shape[0], y_vals:y_vals+data_temp.shape[1]] = data_temp
        matrix[ii] = data_temp
        # print(data_temp.shape)
        # plt.imshow(matrix[ii], cmap='gray')
        # plt.axis('off')
        # plt.show()
    zarray = np.zeros((nslice,200,350))
    for key in matrix:
        print(zarray.shape[0] / matrix[key].shape[0])
        print()
        scale_factor = min(zarray.shape[1] / matrix[key].shape[0], zarray.shape[2] / matrix[key].shape[1])
        print("Sacle",scale_factor)
    
        # Resize the image array
        resized_image = resize(matrix[key], (int(matrix[key].shape[0] * scale_factor), int(matrix[key].shape[1] * scale_factor)), anti_aliasing=False)
    
        # Calculate padding
        pad_row = (zarray.shape[1] - resized_image.shape[0]) // 2
        pad_col = (zarray.shape[2] - resized_image.shape[1]) // 2
    
        # Place the resized image into the center of the zero array with padding
        zarray[key,pad_row:pad_row+resized_image.shape[0], pad_col:pad_col+resized_image.shape[1]] = resized_image
        # plt.imshow(zarray[key], cmap='gray')
        # plt.show()
    return zarray

def create_compound_matrix_sami_skeleton(data,col='result',roi=False,reverse=False):
    print(len(data))
    data = data.dropna(subset=['tissue_id', col])
    print(len(data))
    print("df initial:",np.count_nonzero(data[col]))
    
    unique_tissue_ids = data['tissue_id'].unique()
    nslice = len(unique_tissue_ids)
    print(nslice)
    print(np.count_nonzero(data[col]))
    matrix = {}
    for ii,slice in enumerate(data['tissue_id'].unique()):
        data_temp = create_slice_sami_skeleton(data, slice,col=col, roi= roi,reverse=reverse)
        print(np.count_nonzero(data_temp))
        matrix[ii] = data_temp
    zarray = np.zeros((nslice,200,350))
    for key in matrix:
        # print(zarray.shape[0] / matrix[key].shape[0])
        # print()
        scale_factor = min(zarray.shape[1] / matrix[key].shape[0], zarray.shape[2] / matrix[key].shape[1])
        print("Sacle",scale_factor)
    
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

def create_slice_sami(df_all,slice, col='result', roi=False,reverse = False):
    '''
    nslice = len(df_all.tissue_id.unique())
    # if reverse:
    #     df_temp = df_all[df_all['tissue_id'] == nslice-slice_number]
    # else:
    #     df_temp = df_all[df_all['tissue_id'] == (slice_number+1)]
    df_temp = df_all[df_all['tissue_id'] == slice]
    cnt_x = 0
    cnt_y = 0
    print("df_temp:",np.count_nonzero(df_temp[col]))
    # list to hold visited values
    visited_x = []
    visited_y = []

    # loop for counting the unique
    x_values = np.around(df_temp['x'].to_numpy(), 0)
    y_values = np.around(df_temp['y'].to_numpy(), 0)
    
    for i in range(len(x_values)):
        if x_values[i] not in visited_x: 
            visited_x.append(x_values[i])
            cnt_x += 1
        if y_values[i] not in visited_y: 
            visited_y.append(y_values[i])
            cnt_y += 1

    print("No.of.unique values :", cnt_x)
    print("No.of.unique values :", cnt_y)

    visited_x = np.array(visited_x)
    visited_y = np.array(visited_y)

    sort_x_inds = visited_x.argsort()
    sort_y_inds = visited_y.argsort()

    visited_x = visited_x[sort_x_inds]
    visited_y = visited_y[sort_y_inds]
    
#     print(visited_x, "\n")
#     print(visited_y, "\n")

    reshaped_matrix = np.zeros((cnt_x, cnt_y))
    for ii, vi in enumerate(df_temp[col]):
        # print("vi:", vi)
        if not np.isnan(vi):
            x_ind = find_nearest(visited_x, x_values[ii])
            y_ind = find_nearest(visited_y, y_values[ii])
            reshaped_matrix[x_ind, y_ind] = vi
        else:
            continue
    return reshaped_matrix
    '''
    # df_temp = df_all[df_all['tissue_id'] == slice]
    if roi == False:
        df_temp = df_all[df_all['tissue_id'] == slice]
    else:
        print("roiiii")
        df_temp=df_all[(df_all['tissue_id'] == slice) & df_all['roi'].notna()]
    print("df_temp:")
    print("df_temp:")

    # Get unique x and y values (rounded) and ensure they're numpy arrays
    x_values = np.around(df_temp['x'].to_numpy(), 0)
    y_values = np.around(df_temp['y'].to_numpy(), 0)
    unique_x = np.unique(x_values)
    unique_y = np.unique(y_values)
    
    cnt_x, cnt_y = len(unique_x), len(unique_y)

    print("No. of unique x values:", cnt_x)
    print("No. of unique y values:", cnt_y)

    reshaped_matrix = np.zeros((cnt_x, cnt_y))
    
    # Pre-calculate indices if possible
    x_indices = np.searchsorted(unique_x, x_values)
    y_indices = np.searchsorted(unique_y, y_values)
    
    for value, x_ind, y_ind in zip(df_temp[col], x_indices, y_indices):
        if not np.isnan(value):
            reshaped_matrix[x_ind, y_ind] = value

    return reshaped_matrix

def create_slice_sami_skeleton(df_all,slice, col='result', roi=False,reverse = False):
    if roi == False:
        df_temp = df_all[df_all['tissue_id'] == slice]
    else:
        print("roiiii")
        df_temp=df_all[(df_all['tissue_id'] == slice) & df_all['roi'].notna()]
    print("df_temp:")

    # Get unique x and y values (rounded) and ensure they're numpy arrays
    x_values = np.around(df_temp['x'].to_numpy(), 0)
    y_values = np.around(df_temp['y'].to_numpy(), 0)
    unique_x = np.unique(x_values)
    unique_y = np.unique(y_values)
    
    cnt_x, cnt_y = len(unique_x), len(unique_y)

    print("No. of unique x values:", cnt_x)
    print("No. of unique y values:", cnt_y)

    reshaped_matrix = np.zeros((cnt_x, cnt_y))
    
    # Pre-calculate indices if possible
    x_indices = np.searchsorted(unique_x, x_values)
    y_indices = np.searchsorted(unique_y, y_values)
    
    for value, x_ind, y_ind in zip(df_temp[col], x_indices, y_indices):
        # if not np.isnan(value):
        reshaped_matrix[x_ind, y_ind] = 1

    return reshaped_matrix