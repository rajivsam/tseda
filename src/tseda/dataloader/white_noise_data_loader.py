from .local_dataloader import LocalDataLoader
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class WhiteNoiseDataLoader(LocalDataLoader):
    def __init__(self, file_path: str = "data/white_noise_series.csv"):
        super().__init__(file_path)

    def get_series(self) -> pd.Series:
        """Generate a white noise series for 30 days with hourly frequency."""
        num_days = 30
        samples_per_day = 24
        num_samples = num_days * samples_per_day
        
        # Create a datetime index for 30 days with hourly frequency
        start_date = datetime.now()
        time_index = pd.to_datetime([start_date + timedelta(hours=i) for i in range(num_samples)])
        
        # Generate white noise data
        white_noise = np.random.normal(loc=0, scale=1, size=num_samples)
        
        # Create a pandas Series
        series = pd.Series(white_noise, index=time_index)
        
        return series
