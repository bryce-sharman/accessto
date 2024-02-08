# accessto: Access to opportunities calculator

**accessto** is a library that allows calculation of access to opportunities, a commonly used measure in transportation planning and urban design. This library is designed to support analyses being conducted by City of Toronto staff, although others are welcome to use.

This package is designed so that users will use a Jupyter Noteook to setup and run the calculations.

Finding travel times and costs are the crucial underpinning to access to opportunities calcutions. This library calls two open source libraries that will actually perform these calculations *OpenTripPlanner* (OTP) and *r5py*. This package was developed using OTP v2.4, which was the newest stable release at the time of development. 


## Installation

This installation guide is designed primarily for City of Toronto employees to install this library and its dependencies on (Windows) City infrastructure. This may vary slightly for other users.

### 1. Download miniconda package and environment management system. 

People working for the City of Toronto must use miniconda instead of the more complete-featured anaconda, as anaconda is not free for use by larger organizations.

The latest version of miniconda can be found here.
https://docs.conda.io/projects/miniconda/en/latest/index.html

Install for a single-user (just me option), as to install for all users requires admin priviledges. At the time of writing, the default installation folder is `C:\Users\[user name]\AppData\Local\miniconda3`. You can use the default advanced installation options

### 2. Run miniconda

From the Windows Start Menu, open *Anaconda Prompt (Miniconda3)

### 3. Create a new environment to hold r5py

Given the r5py dependency, create an r5py Anaconda environment. The following installation instructions are from the r5py documentation. This command creates an environment with r5py installed and all required dependencies for r5py. No additional requirements are needed if using OpenTripPlanner to calculate travel times.

```console
conda create \
    --name r5py \
    --channel conda-forge \
    r5py
```

> **_NOTE:_** Note for City of Toronto users, that this will not work when using City desktop computers or when connected to the VM. To run on a City computer I would install on a laptop not on the VM, and then copy the Python environment to the desktop computer. Note that miniconda must be installed to the same location on both computers for this to work.


Note that at one point I had an issue reading/writing shapefiles using this package. Hence I created an environment and install `fiona` and `pyorgio` before r5py. This workaround appears to resolve this issue.

```console
conda create --name r5py python=3.11
conda activate r5py
conda install --channel conda-forge fiona pyogrio jupyterlab
conda install --channel conda-forge r5py
```

### 4. Activate the r5py environment

In the Miniconda3 prompt, type:
```console 
(r5py) [local directory]> conda activate r5py
```

### 5. Install JupyterLab to this environment. 
In the Miniconda3 prompt, type:
```console
(r5py) [local directory]> conda install --channel conda-forge jupyterlab
```

### Install **accessto** to this environment

Download the code from this release and store in a convenient location.

```console
(r5py) [local directory]> pip install -e [path to the root folder of this library]
```
Note that the root folder of the library contains the *pyproject.toml* file.

To update this package, replace the previous command with the following:
```console
(r5py) [local directory]> pip install -e [path to the root folder of this library] --upgrade
```

### 6. Download OpenTripPlanner JAR file

*OpenTripPlanner* is distributed as a single stand-alone runnable JAR file. OTP v2.4.0 can be downloaded from their GitHub repository.
https://github.com/opentripplanner/OpenTripPlanner/releases

Download the 'shaded jar' file, *e.g.* **otp-2.4.0-shaded.jar**.



### 6. Install Java

Both *OpenTripPlanner* and *r5* use Java. If the system Java is too old, then you will to install a new JDK.

OpenTripPlanner version 2.4, requires JDK 17. The following JDK was used during development and testing of 
this library.

https://learn.microsoft.com/en-us/java/openjdk/download#openjdk-17

> **_NOTE:_** JDK installation requires admin priviledges. City of Toronto staff will need to contact IT to install this package. 



### 7. Download `r5`` JAR file and setup the `r5py`` config file

On City of Toronto computers, we've found that it's best to run using a local copy of the r5 .jar file. 

Download the `r5` JAR file, which is the package that performs the travel time computations. This is available on *r5's* GitHub page: https://github.com/conveyal/r5/releases.
As of the time of writing, the latest version is version 7.1, *r5-v7.1-all.jar*.  Download this and store in a local directory.

You will then need to setup the r5py config file, which among other things will point r5py to this file. On a windows machine *r5py* looks for this file in the %APPDATA% directory. You can find this by typing 
`%APPDATA%` in the URL of an explorer window. Create a file called `r5py.yml` in this directiory. The snippet below shows  the contents of this file on the testing computer.

```yaml
--max-memory=8G
--r5-classpath=C:\MyPrograms\r5\r5-v7.1-r5py-all.jar
--verbose=True
```

More information on r5py config files can be found on their documentation:
https://r5py.readthedocs.io/en/stable/user-guide/user-manual/configuration.html#configuration-via-config-files

### 8. Running accessto

*accessto* is designed to be run from a Jupyter notebook. To open the notebook, perform the following steps:

1. From the Windows Start Menu, open *Anaconda Prompt (Miniconda3)
2. Activate the `r5py` library by typing the following in the Miniconda prompt window
    ```console 
    (r5py) [local directory]> conda activate r5py
    ```
3. Open a Jupyter Lab file, then open Jupyter lab
    - first change directory to where your notebooks are stored
        ```console 
        (r5py) [local directory]> cd [notebook location] 
        (r5py) [notebook location]> jupyter lab
        ```

Several example scripts are included in the `example_notebooks` folder of this library package to help you get started.

Please also see the [**wiki**](https://github.com/bryce-sharman/accessto/wiki) for this project for more detailed documentation and usage guides.
