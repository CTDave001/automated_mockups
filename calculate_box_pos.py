import os
import argparse
import cv2
import json
from PIL import Image
import numpy as np
from skimage import io
from skimage.color import rgb2gray
from skimage.measure import label, regionprops

def calculate_parameters(image_path, target_color):
    image = io.imread(image_path)[:, :, :3]
    grayscale = rgb2gray(image)

    r, g, b = target_color
    target_gray = 0.2989*r + 0.5870*g + 0.1140*b
    mask = grayscale == target_gray

    label_img, _ = label(mask, connectivity=mask.ndim, return_num=True)
    properties = regionprops(label_img)

    if properties:
        for prop in properties:
            if prop.area == np.max([p.area for p in properties]):
                bbox = prop.bbox
                height = bbox[2]-bbox[0]
                width = bbox[3]-bbox[1]
                rotation = prop.orientation
        return bbox, height, width, rotation
    else:
        print(f"No properties found for image: {image_path}")
        return None, None, None, None

def save_parameters(directory, target_color):
    parameters = {}
    for filename in os.listdir(directory):
        if filename.endswith(".png") or filename.endswith(".jpg"):  
            image_path = os.path.join(directory, filename)
            bbox, height, width, rotation = calculate_parameters(image_path, target_color)
            if bbox and height and width:
                parameters[filename] = {"bbox": bbox, "height": height, "width": width, "rotation": rotation}
    with open("parameters.json", "w") as file:
        json.dump(parameters, file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate parameters for positioning designs on product mockups.")
    parser.add_argument('--color', type=int, nargs=3, metavar=('R', 'G', 'B'), help="The RGB values of the color to find in the images.")
    parser.add_argument('--hex_color', type=str, help="The hexadecimal value of the color to find in the images.")
    parser.add_argument('--dir', type=str, default='images/box_mockups', help="Directory of images with the box.")
    
    args = parser.parse_args()

    if args.hex_color:
        hex_color = args.hex_color.lstrip('#')
        target_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2 ,4))
    else:
        target_color = tuple(args.color)

    save_parameters(args.dir, target_color)
