# T-Shirt Mockup Generator

The T-Shirt Mockup Generator is a Python-based tool for generating realistic shirt mockups given a specified design and a set of base mockup images.

This program works by calculating several parameters (e.g., bounding box, width, height, rotation angle) of a designated 'target area' in the base mockup images, where the user-specified shirt design will be placed. 

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
