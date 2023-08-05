import os
import cv2
import json
from PIL import Image
import numpy as np
from skimage import io
from skimage.color import rgb2gray
from skimage.measure import label, regionprops

def calculate_parameters(image_path, target_color):
    image = io.imread(image_path)
    grayscale = rgb2gray(image)

    r, g, b = target_color
    target_gray = 0.2989*r + 0.5870*g + 0.1140*b
    mask = grayscale == target_gray
    
    label_img, _ = label(mask, connectivity=mask.ndim, return_num=True)
    properties = regionprops(label_img)
    
    for prop in properties:
        if prop.area == np.max([p.area for p in properties]):
            bbox = prop.bbox
            height = bbox[2]-bbox[0]
            width = bbox[3]-bbox[1]
            rotation = prop.orientation

    return bbox, height, width, rotation

def save_parameters(directory, target_color):
    parameters = {}
    for filename in os.listdir(directory):
        if filename.endswith(".png") or filename.endswith(".jpg"):  
            image_path = os.path.join(directory, filename)
            bbox, height, width, rotation = calculate_parameters(image_path, target_color)
            parameters[filename] = {"bbox": bbox, "height": height, "width": width, "rotation": rotation}

    with open("parameters.json", "w") as file:
        json.dump(parameters, file)

# Usage
mockups_with_boxes_dir = 'BoxMocks'
target_color = (0, 0, 0)  # The color to find in the images (in this case, black)
save_parameters(mockups_with_boxes_dir, target_color)
