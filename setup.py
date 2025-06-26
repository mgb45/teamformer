"""Setup script for packaging and distributing the team_former module."""

from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(  # pylint: disable=too-many-positional-arguments
    name="team_former",
    version="0.1.0",
    author="Michael Burke",
    author_email="michael.g.burke@monash.edu",
    description="A team allocation tool using OR-Tools and parameterized with fire.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mgb45/teamformer",  # Replace with your repo URL
    packages=find_packages(),
    install_requires=["pandas", "ortools", "fire", "openpyxl", "xlrd"],
    entry_points={
        "console_scripts": [
            "team_former=team_former.make_teams:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
