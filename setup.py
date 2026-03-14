#!/usr/bin/env python3
"""
Packaging setup for Arsenyc - Arsenal fork with Notion/Obsidian sync
"""

import pathlib
from setuptools import find_packages, setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()
REQUIREMENTS = (HERE / "requirements.txt").read_text().strip().split("\n")

setup(
    name="arsenyc",
    version="1.2.8",
    packages=find_packages(),
    install_requires=REQUIREMENTS,
    include_package_data=True,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "arsenyc = arsenal.app:main",
        ],
    },
)
