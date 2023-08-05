# Shirt Mockup Generator

Shirt Mockup Generator is a Python tool for generating shirt mockups. It uses image processing techniques to identify a designated 'target area' on a base mockup image where a user's design image will be placed.

## Repository Structure
```
/ShirtMockupGenerator
│   run.py
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

---

## Getting Started:

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites:

To run this code, you need the following installed:

- Python 3.8
- PIL
- cv2
- OpenCV
- numpy
- skimage


### Installing:

To install the required dependencies run:

```bash
pip install -r requirements.txt
```

## Usage:

You can start the program by running `run.py` script:

```python
python run.py
```

This will start the process of generating shirt mockups.

---

## File Overview:

- `run.py`: This is the main entry script to run the Shirt Mockup Generator.

- `images/mockups`: This directory contains the base mockup images that will be used for generating the shirt mockups.

- `images/designs`: This directory contains the user's design images that will be placed onto the base mockup images.

- `images/output`: This directory is where the generated shirt mockups will be saved.

- `images/parameters.json`: This file stores the parameters computed for each mockup (bounding box, width, height, rotation angle), used for placing the design images onto the mockups.

---

## License:

This project is licensed under the MIT License.
