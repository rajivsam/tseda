
import pandas as pd

class LocalDataLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load_data(self) -> pd.DataFrame:
        """Load data from a local CSV file into a pandas DataFrame."""
        try:
            data = pd.read_csv(self.file_path)
            return data
        except FileNotFoundError:
            print(f"Error: The file at {self.file_path} was not found.")
            return pd.DataFrame()
        except pd.errors.EmptyDataError:
            print("Error: The file is empty.")
            return pd.DataFrame()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return pd.DataFrame()