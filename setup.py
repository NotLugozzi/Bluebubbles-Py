#!/usr/bin/env python3

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open(os.path.join(this_directory, 'requirements.txt'), encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='bluebubbles-client',
    version='1.0.0',
    description='BlueBubbles GTK4 Client for Linux',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='NotLugozzi',
    author_email='',
    url='https://github.com/NotLugozzi/Bluebubbles-Py',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'bluebubbles=main:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Communications :: Chat',
        'Topic :: Desktop Environment :: Gnome',
    ],
    data_files=[
        ('share/applications', ['com.github.bluebubbles.client.desktop']),
        ('share/metainfo', ['com.github.bluebubbles.client.metainfo.xml']),
        ('share/icons/hicolor/scalable/apps', ['icons/com.github.bluebubbles.client.svg']),
    ],
)
