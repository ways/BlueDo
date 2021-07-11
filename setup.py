# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
icon_path = 'share/icons/hicolor/256x256/apps'

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='bluedo',
    version='0.56',
    description='Bluetooth proximity automation',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/ways/BlueDo/',

    author='Lars Falk-Petersen',
    author_email='dev@falkp.no',

    license='GPLv3+',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project?
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: End Users/Desktop',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',

        # Specify the Python versions you support here.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        "Topic :: Desktop Environment",
        "Topic :: Desktop Environment :: Gnome",
        "Topic :: Security",
        "Environment :: X11 Applications :: Gnome",
        "Operating System :: POSIX :: Linux",
        "Natural Language :: English"
    ],
    keywords='bluetooth',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=['setuptools', 'configparser', 'appdirs', 'wheel', 'PyBluez', 'PyGObject'],
    entry_points={
        'console_scripts': [
            'bluedo=bluedo:main',
        ],
    },
    data_files=[
        ('share/applications', ['applications/bluedo.desktop']),
        (icon_path, ['bluedo/bluedo.png']),
    ],
    include_package_data=True,
    python_requires='>=3.9',
    #test_suite = 'tests',
)

