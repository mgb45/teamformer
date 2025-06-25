
from setuptools import setup, find_packages

setup(
    name='team_former',
    version='0.1.0',
    author='Michael Burke',
    author_email='michael.g.burke@monash.edu',
    description='A team allocation tool using OR-Tools and parameterized with fire.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/mgb45/teamformer',  # Replace with your repo URL
    packages=find_packages(),
    install_requires=[
        'pandas',
        'ortools',
        'fire',
        'openpyxl',
        'xlrd'
    ],
    entry_points={
        'console_scripts': [
            'team_former=team_former.make_teams:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)