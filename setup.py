from setuptools import setup
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="pymixin",
    version="1.1.1",
    author="Martmists",
    author_email="martmists@gmail.com",
    description="A high-level library for manipulating Python Bytecode in an easy way.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License"
    ],
    packages=["mixin"],
    requires=["pyasm"],
    python_requires=">=3.5",
)
