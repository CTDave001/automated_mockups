import os
import argparse
import cv2
import json
from PIL import Image
import numpy as np
from skimage import io
from skimage.color import rgb2gray
from skimage.measure import label, regionprops

def load_parameters(path):
    with open(path, "r") as file:
        parameters = json.load(file)
    return parameters

def create_mockup(mockup_path, design_path, output_path, bbox, width, height, rotation, transparency):
    mockup = Image.open(mockup_path)
    design = Image.open(design_path)

    aspect_ratio = design.height / design.width
    design_width = width
    design_height = int(width * aspect_ratio)

    if design_height > height:
        design_height = height
        design_width = int(height / aspect_ratio)

    design = design.resize((design_width, design_height))
    design = design.rotate(np.degrees(rotation), expand=True)

    designCopy = design.copy()
    designCopy.putalpha(transparency)
    design.paste(designCopy, design)

    position = (int(bbox[1] + width / 2 - design.width / 2), int(bbox[0]))

    mockup.paste(design, position, design)
    mockup.save(output_path)

def create_mockups(design_dir, mockup_dir, parameters, output_dir, transparency):
    os.makedirs(output_dir, exist_ok=True)

    for design_filename in os.listdir(design_dir):
        if design_filename.endswith(".png") or design_filename.endswith(".jpg"):  
            design_path = os.path.join(design_dir, design_filename)
            for mockup_filename, params in parameters.items():
                mockup_path = os.path.join(mockup_dir, mockup_filename)
                output_path = os.path.join(output_dir, f"{os.path.splitext(design_filename)[0]}_{os.path.splitext(mockup_filename)[0]}.png")
                create_mockup(mockup_path, design_path, output_path, params["bbox"], params["width"], params["height"], params["rotation"], transparency)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create mockup designs based on given parameters.")
    parser.add_argument('--param_file', type=str, default='parameters.json', help="File path for parameters.")
    parser.add_argument('--design_dir', type=str, default='images/designs', help="Directory of design images.")
    parser.add_argument('--mockup_dir', type=str, default='images/mockups', help="Directory of mockup images.")
    parser.add_argument('--output_dir', type=str, default='images/output', help="Directory to save the output images.")
    parser.add_argument('--transparency', type=int, default=255, help="Amount of transparency for the design (0-255).")
    args = parser.parse_args()

    parameters = load_parameters(args.param_file)
    create_mockups(args.design_dir, args.mockup_dir, parameters, args.output_dir, args.transparency)
