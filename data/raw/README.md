# Raw Data

Raw dataset files are not committed to this repository because they are source data and can be downloaded from the original public dataset.

## Dataset

**A Multi-Model Dataset for BOSCH Plasma-Etching: Optical Emission Spectra, Process Parameters, and Wafer Measurements for Data-Driven Plasma Modeling**

Zenodo record: **17122442**  
DOI: **10.5281/zenodo.17122442**

This project currently uses the process-parameter and 89-point wafer-measurement portions of the dataset. The large daily OES files are not required for the current analysis pipeline.

## Required Files

Place the following files in this directory before running the notebooks:

```text
data/raw/
├── Process_data.nc
├── Dictionary_process.nc
├── Lot_status.xlsx
├── Si_Oxide_etch_89_points.csv
├── Readme.pdf
└── Wafer_layout.pdf
```

## Notebook Dependency

The raw files are first checked and interpreted in:

```text
notebooks/00_data_understanding.ipynb
```

Data-quality rules and generated interim files are then created by:

```text
notebooks/01_data_quality.ipynb
```

Do not manually edit the raw dataset files.
