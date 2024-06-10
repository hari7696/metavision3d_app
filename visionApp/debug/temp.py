import numpy as np
import matplotlib.pyplot as plt
import pickle
# from pylab import *
from PIL import Image
from matplotlib.figure import Figure
with open(r'C:\Users\ghari\Documents\OPS\UI\metavision3d_app\visionApp\debug\temp.pickle', 'rb') as file:
    arr = pickle.load(file)

fig = Figure(figsize=(1, 0.57), dpi=150)
ax = fig.add_subplot(111)
ax.set_facecolor('black')
fig.patch.set_facecolor('black')
ax.imshow(arr[0], cmap="gray",vmin=0)
plt.show()


    def get_files(self): 
        self.files_to_path_dict = {}
        self.files = []
        for dirpath, dirs, lst_files in os.walk(self.working_folder):
            for file in lst_files:
                if file.endswith(".h5ad"):
                    # print(file, dirpath)
                    if os.path.dirname(dirpath) != "clustering":
                        new_dir_ref = os.path.basename(dirpath)
                        file_ = new_dir_ref + "/" + file
                    self.files_to_path_dict[file_] = os.path.join(dirpath, file)
                    self.files.append(file_)