"""
Automated Mockup Generator - Create product mockups at scale.

This package provides tools for automatically generating product mockups by
overlaying design images onto mockup templates with precise positioning and rotation.
"""

__version__ = "1.0.0"
__author__ = "CTDave001"
__license__ = "MIT"

from .calculator import MockupCalculator, BoxParameters
from .generator import MockupGenerator
from .utils import Color, ImageFormat

__all__ = [
    "MockupCalculator",
    "MockupGenerator",
    "BoxParameters",
    "Color",
    "ImageFormat",
    "__version__",
]
