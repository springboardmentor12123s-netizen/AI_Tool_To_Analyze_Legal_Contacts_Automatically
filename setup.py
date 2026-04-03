from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="infosys-project",
    version="0.1.0",
    author="Kanika Mittal",
    author_email="kanikamittal2592005@gmail.com",
    description="AI Tool to Read and Analyze Legal Contracts Automatically",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/infosys-project",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
