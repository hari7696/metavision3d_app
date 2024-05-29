### Setup ###
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# colormap1
cmap1 = plt.get_cmap('magma', 256)
new_colors1 = cmap1(np.linspace(0, 1, 256))
new_colors1[0] = [0, 0, 0, 1]

new_cmap1 = mcolors.LinearSegmentedColormap.from_list("new_cmap1", new_colors1)
if "new_cmap1" in plt.colormaps():
    plt.colormaps.unregister("new_cmap1")
plt.colormaps.register(cmap=new_cmap1)

# colormap2
cmap2 = plt.get_cmap('viridis', 256)
new_colors2 = cmap2(np.linspace(0, 1, 256))
new_colors2[0] = [0, 0, 0, 1]

new_cmap2 = mcolors.LinearSegmentedColormap.from_list("new_cmap2", new_colors2)
if "new_cmap2" in plt.colormaps():
    plt.colormaps.unregister("new_cmap2")
plt.colormaps.register(cmap=new_cmap2)