# T-Shirt Mockup Generator

This project is a collection of Python scripts that automate the process of generating mockups by overlaying design images on predefined areas in mockup templates. It works with simple or complex mockup images including those where the placeholder box is rotated.

The script first identifies a target box within reference mockup images by looking for a specific color (e.g., black). It calculates the position, size, and rotation of this box relative to the overall image, and saves these details for multiple mockups in a JSON file.

Then, using these parameters, the script places design images onto real mockups (i.e., without target boxes). It scales and rotates the design according to each mockup's specific parameters, ensuring a real-life appearance. The top of the design aligns with the top of the box, and it is horizontally centered for a seamlessly fitting design in the mockup.

The tool takes two directories as input: one with the design images and the other with the mockup templates. It generates a new image for every combination of design and mockup, storing mockups in an output directory.

This tool is extremely helpful for designers, marketers, or anyone who needs to quickly generate a large number of mockups for design presentations, marketing collateral or e-commerce listings.

## Repository Structure

```
/ShirtMockupGenerator
│   calculate_parameters.py
│   create_mockup.py
│   README.md
│   requirements.txt
|   LICENSE
│
└───images
│   │   mockups
│   │   designs
│   │   output
|   |   parameters.json
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

1. Use the `calculate_parameters.py` script to compute the parameters for each base mockup image and save it to a .json file:

   ```python
   python calculate_parameters.py
   ```

2. Apply your designs to the mockups using the `create_mockup.py` script:

   ```python
   python create_mockup.py
   ```

The resulting mockups can be found in the 'images/output' directory. 

## File Descriptions

- `calculate_parameters.py`: This script analyzes the base mockup images and calculates the parameters necessary for placing the user's shirt design properly on each mockup.

- `create_mockup.py`: This script takes user design images and places them onto the base mockups using the parameters computed with calculate_parameters.py.

- `images/mockups`: Contains the base mockup images.

- `images/designs`: Contains the user's shirt design images.

- `images/output`: Stores the generated mockups.

- `images/parameters.json`: Holds the computed parameters for each mockup.

## License

This project is licensed under the MIT License.
