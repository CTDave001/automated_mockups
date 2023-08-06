# T-Shirt Mockup Generator

This project is a collection of Python scripts that automate the process of generating mockups by overlaying design images on predefined areas in mockup templates. It works with simple or complex mockup images including those where the placeholder box is rotated.

The script first identifies a target box within reference mockup images by looking for a specific color (e.g., black). It calculates the position, size, and rotation of this box relative to the overall image, and saves these details for multiple mockups in a JSON file.

Then, using these parameters, the script places design images onto real mockups (i.e., without target boxes). It scales and rotates the design according to each mockup's specific parameters, ensuring a real-life appearance. The top of the design aligns with the top of the box, and it is horizontally centered for a seamlessly fitting design in the mockup.

The tool takes two directories as input: one with the design images and the other with the mockup templates. It generates a new image for every combination of design and mockup, storing mockups in an output directory.

This tool is extremely helpful for designers, marketers, or anyone who needs to quickly generate a large number of mockups for design presentations, marketing collateral or e-commerce listings.

## Directories Tree
This is how your structure should look like:

```
/ShirtMockupGenerator
│   calculate_box_pos.py
│   create_mockups.py
│   README.md
│   requirements.txt
|   LICENSE
|   parameters.json
│
└───images
│   │   mockups
│   │   designs
│   │   output
|   |   box_mockups
```

## Getting Started

Follow these instructions to get the Shirt Mockup Generator running on your local machine.

### Prerequisites

Ensure you have the following installed:

- Python 3.8
- Pillow
- cv2 (OpenCV)
- numpy
- scikit-image

### Installing

Install the required Python dependencies using pip:

```bash
pip install -r requirements.txt
```

## Usage

**Step 1: Calculate Parameters**

The first step is to calculate the bounding box parameters for your mockup images. It identifies a specific color in your image (for example, a black box), and calculates the position, size, and rotation of this box.

Run the `calculate_parameters.py` script by passing the RGB color and directory for the mockup images as command-line arguments:

```sh
python calculate_parameters.py --color R G B --dir image_directory
```

Replace `R G B` with the RGB values of the color in your image, and `image_directory` with the directory that holds your mockup images. This will generate a `parameters.json` file with the calculated parameters.

**Step 2: Create Mockups**

The second step is to use the calculated parameters to position your designs onto the product mockups.

Run the `create_mockups.py` script by passing the paths to the parameters file, design images directory, mockup images directory, and the output directory as command-line arguments:

```sh
python create_mockups.py --param_file parameters.json --design_dir design_directory --mockup_dir mockup_directory --output_dir output_directory
```

Replace `design_directory`, `mockup_directory`, and `output_directory` with the corresponding directory paths.

## Example:

```sh
python calculate_parameters.py --color 0 0 0 --dir box_mockups
python create_mockups.py --param_file parameters.json --design_dir designs --mockup_dir mockups --output_dir output
```

In the above example, the scripts will look for black color (0, 0, 0 in RGB) in images located in the `box_mockups` directory. The positioned images will then be saved in the `output` directory.

## File Descriptions

- `calculate_parameters.py`: This script analyzes the base mockup images and calculates the parameters necessary for placing the user's shirt design properly on each mockup.

- `create_mockup.py`: This script takes user design images and places them onto the base mockups using the parameters computed with calculate_parameters.py.

- `images/mockups`: Contains the base mockup images.

- `images/designs`: Contains the user's shirt design images.

- `images/output`: Stores the generated mockups.

- `images/parameters.json`: Holds the computed parameters for each mockup.

## License

This project is licensed under the MIT License.
