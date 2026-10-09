from pathlib import Path
from setuptools import setup, find_packages

this_directory = Path(__file__).parent
readme_path = this_directory / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="codefetch-cli",
    version="1.2.3",
    description="Quickly fetch code files from GitHub repositories with simple commands",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Inzamamul Qureshi",
    author_email="inzamamulqureshi@gmail.com",
    url="https://github.com/InzamamulQureshi/Codefetch",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "codefetch = codefetch.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: Utilities",
    ],
)
