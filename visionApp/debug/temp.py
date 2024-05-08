import numpy as np
import matplotlib.pyplot as plt
import pickle
from pylab import Figure
from PIL import Image
with open('temp.pickle', 'rb') as file:
    arr = pickle.load(file)

image = Image.fromarray(arr[0])
image.show()
plt.show()