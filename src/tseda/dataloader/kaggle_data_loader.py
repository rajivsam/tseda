"""Kaggle dataset download helper using the Kaggle public API."""

import os
from kaggle.api.kaggle_api_extended import KaggleApi
from dotenv import load_dotenv
from sys import exit
from pathlib import Path

def download_kaggle_dataset(dataset_slug: str, download_path: str) -> None:
    """Download and unzip a Kaggle dataset to a local directory.

    Credentials are read from the ``KAGGLE_USERNAME`` / ``KAGGLE_KEY``
    environment variables (or a ``.env`` file via ``python-dotenv``).

    Args:
        dataset_slug: The URL path segment after ``kaggle.com/datasets/``
            (e.g. ``'arashnic/max-planck-weather-dataset'``).
        download_path: Existing local directory where files will be saved.
    """

    path = Path(download_path)
    if not path.is_dir():
        print("Directory does not exist or is not valid., please check the path and try again.")
        exit(1)
    
    load_dotenv()  # Load environment variables from .env file
    api = KaggleApi()
    api.authenticate()
    
    print(f"Downloading {dataset_slug}...")
    api.dataset_download_files(dataset_slug, path=download_path, unzip=True)
    print("Download complete.")

