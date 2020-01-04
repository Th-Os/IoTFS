import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="iot-fs",
    version="0.0.1",
    author="Thomas Oswald",
    author_email="thomas.oswald@student.ur.de",
    description="A Filesystem for IoT data flows.",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/th-os/iotfs",
    packages=setuptools.find_packages(),
    platforms=['Linux'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Linux",
    ],
    python_requires='>=3.5'
)
