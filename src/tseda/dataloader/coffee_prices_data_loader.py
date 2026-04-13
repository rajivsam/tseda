"""Data loader for the ICO coffee prices dataset."""

from .local_dataloader import LocalDataLoader
import pandas as pd

class CoffeePricesDataLoader(LocalDataLoader):
    """Load and expose the coffee prices CSV as a named ``signal`` series."""

    def __init__(self, file_path: str = "data/coffee_prices.csv"):
        """Configure the loader with the default coffee prices CSV path.

        Args:
            file_path: Path to the coffee prices CSV file.
        """
        super().__init__(file_path)

    def load_coffee_prices(self) -> pd.DataFrame:
        """Load coffee prices data from a local CSV file."""
        data = self.load_data()
        data.columns = ["date", "signal"]
        data.date = pd.to_datetime(data.date)


        if not data.empty:
            # Additional processing specific to coffee prices can be added here
            return data
        else:
            print("No data loaded.")
            return pd.DataFrame()

    def get_series(self) -> pd.Series:
        """Get the 'signal' series from the coffee prices data."""
        data = self.load_coffee_prices()
        data.index = data.date
        if not data.empty:
            return data["signal"]
        else:
            print("No data available to extract series.")
            return pd.Series(dtype=float)