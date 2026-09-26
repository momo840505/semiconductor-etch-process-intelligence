\# Raw Data



Raw dataset files are not committed to this repository because they are source data and can be downloaded from the original public dataset.



\## Dataset



\*\*A Multi-Model Dataset for BOSCH Plasma-Etching: Optical Emission Spectra, Process Parameters, and Wafer Measurements for Data-Driven Plasma Modeling\*\*



Zenodo record: \*\*17122442\*\*  

DOI: \*\*10.5281/zenodo.17122442\*\*



This project currently uses the process-parameter and 89-point wafer-measurement portions of the dataset. The large daily OES files are not required for the current analysis pipeline.



\## Required files



Place the following files in this directory before running the notebooks:



```text

data/raw/

├── Process\_data.nc

├── Dictionary\_process.nc

├── Lot\_status.xlsx

├── Si\_Oxide\_etch\_89\_points.csv

├── Readme.pdf

└── Wafer\_layout.pdf

```



\## Notebook dependency



The raw files are first checked and interpreted in:



```text

notebooks/00\_data\_understanding.ipynb

```



Data-quality rules and generated interim files are then created by:



```text

notebooks/01\_data\_quality.ipynb

```



Do not manually edit the raw dataset files.

