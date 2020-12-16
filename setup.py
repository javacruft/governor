import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="governor-canonical",  # Replace with your own username
    version="0.0.1",
    author="Dominik Fleischmann",
    author_email="dominik.fleischmann@canonical.com",
    description="Base for Governor Charms",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DomFleischmann/governor",
    packages=["governor"],
    install_requires=[
        'juju',
        'ops',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
