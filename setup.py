"""
Setup script for Universal K-Sites package.
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="k-sites",
    version="1.0.0",
    author="Kanaka KK, Sandip Garai, Jeevan C, Tanzil Fatima",
    author_email="kanakakk@example.com",
    description="Universal K-Sites: AI-Powered CRISPR Guide RNA Design Platform with Pathway-Aware Off-Target Filtering",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/KanakaKK/K-sites",
    project_urls={
        "Bug Reports": "https://github.com/KanakaKK/K-sites/issues",
        "Source": "https://github.com/KanakaKK/K-sites",
        "Documentation": "https://github.com/KanakaKK/K-sites/blob/main/README.md",
    },
    packages=find_packages(),  # This will find all packages including subpackages
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "biopython>=1.78",
        "neo4j>=4.4.0",
        "pyyaml>=5.4.0",
        "tqdm>=4.60.0",
        "dataclasses-json>=0.5.0",
        "pandas>=1.3.0",
    ],
    entry_points={
        "console_scripts": [
            "k-sites=k_sites.cli:main",
        ],
    },
    keywords="crispr, bioinformatics, genomics, gene-editing, rna-guides, biology, research, pathway-analysis, go-terms",
    include_package_data=True,
    zip_safe=False,
)