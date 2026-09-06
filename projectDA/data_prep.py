import os
import urllib.request
import pandas as pd
import numpy as np

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
RAW_DATA_PATH = os.path.join(DATA_DIR, 'raw_housing_data.csv')
CLEANED_DATA_PATH = os.path.join(DATA_DIR, 'cleaned_housing_data.csv')
DATASET_URL = 'https://raw.githubusercontent.com/jmatth11/King-County-House-Data-Set/master/kc_house_data.csv'

def download_dataset():
    """Downloads the housing sales dataset if it doesn't exist locally."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory: {DATA_DIR}")

    if not os.path.exists(RAW_DATA_PATH):
        print(f"Downloading dataset from: {DATASET_URL} ...")
        try:
            urllib.request.urlretrieve(DATASET_URL, RAW_DATA_PATH)
            print("Download completed successfully!")
        except Exception as e:
            print(f"Error downloading dataset: {e}")
            raise e
    else:
        print("Raw dataset already exists locally.")

def clean_and_prepare_data():
    """Cleans the raw dataset and creates calculated fields."""
    if not os.path.exists(RAW_DATA_PATH):
        raise FileNotFoundError(f"Raw data file not found at {RAW_DATA_PATH}")

    print("Loading dataset...")
    df = pd.read_csv(RAW_DATA_PATH)
    initial_count = len(df)
    print(f"Total records loaded: {initial_count}")

    # 1. Remove duplicates
    print("Checking for duplicate records...")
    df.drop_duplicates(subset=['id'], keep='first', inplace=True)
    duplicates_removed = initial_count - len(df)
    print(f"Removed {duplicates_removed} duplicate house IDs.")

    # 2. Handle missing values
    print("Handling missing/null values...")
    # Drop rows with null values in critical fields (if any)
    critical_cols = ['price', 'bedrooms', 'bathrooms', 'sqft_living', 'yr_built']
    df.dropna(subset=critical_cols, inplace=True)
    
    # Fill remaining nulls in non-critical fields with appropriate defaults
    for col in df.columns:
        if df[col].isnull().any():
            if df[col].dtype in [np.float64, np.int64]:
                df[col].fillna(df[col].median(), inplace=True)
            else:
                df[col].fillna(df[col].mode()[0], inplace=True)

    # 3. Correct data types & extract Sale Year
    print("Correcting data types...")
    df['date'] = df['date'].astype(str)
    df['Sale Year'] = df['date'].apply(lambda x: int(x[:4]))
    
    df['price'] = df['price'].astype(float)
    df['bedrooms'] = df['bedrooms'].astype(int)
    df['bathrooms'] = df['bathrooms'].astype(float)
    df['floors'] = df['floors'].astype(float)
    df['yr_built'] = df['yr_built'].astype(int)
    df['yr_renovated'] = df['yr_renovated'].astype(int)
    df['sqft_basement'] = df['sqft_basement'].astype(int)
    df['sqft_living'] = df['sqft_living'].astype(int)

    # 4. Rename fields for Tableau & user-friendliness
    print("Renaming fields...")
    df.rename(columns={
        'price': 'Sale Price',
        'bedrooms': 'Bedrooms',
        'bathrooms': 'Bathrooms',
        'sqft_living': 'Living Area Sqft',
        'sqft_lot': 'Lot Area Sqft',
        'floors': 'Floors',
        'waterfront': 'Waterfront',
        'view': 'View',
        'condition': 'Condition',
        'grade': 'Grade',
        'sqft_above': 'Above Ground Area Sqft',
        'sqft_basement': 'Basement Area Sqft',
        'yr_built': 'Year Built',
        'yr_renovated': 'Year Renovated',
        'zipcode': 'Zipcode',
        'lat': 'Latitude',
        'long': 'Longitude'
    }, inplace=True)

    # 5. Create calculated fields
    print("Creating calculated fields...")
    
    # A. House Age = Sale Year - Year Built
    df['House Age'] = df['Sale Year'] - df['Year Built']
    df['House Age'] = df['House Age'].clip(lower=0)

    # B. Renovation Status = 'Renovated' if Year Renovated > 0 else 'Not Renovated'
    df['Renovation Status'] = df['Year Renovated'].apply(lambda x: 'Renovated' if x > 0 else 'Not Renovated')

    # C. Years Since Renovation = Sale Year - Year Renovated if Renovated else House Age
    df['Years Since Renovation'] = df.apply(
        lambda row: max(0, row['Sale Year'] - row['Year Renovated']) if row['Renovation Status'] == 'Renovated'
        else row['House Age'], axis=1
    )

    # D. Price per Sqft = Sale Price / Living Area Sqft
    df['Price per Sqft'] = df['Sale Price'] / df['Living Area Sqft']
    df['Price per Sqft'] = df['Price per Sqft'].round(2)

    # Validate range of fields
    print("Validating imported records...")
    df = df[df['Sale Price'] > 0]
    df = df[df['Bedrooms'] > 0]
    
    final_count = len(df)
    print(f"Data validation complete.")
    print(f"Initial row count: {initial_count}")
    print(f"Final cleaned row count: {final_count}")
    print(f"Percentage of records retained: {final_count/initial_count:.2%}")

    # Export clean dataset
    print(f"Exporting cleaned dataset to: {CLEANED_DATA_PATH} ...")
    df.to_csv(CLEANED_DATA_PATH, index=False)
    print("Data prep pipeline execution completed successfully!")

    return {
        "initial_count": initial_count,
        "final_count": final_count,
        "duplicates_removed": duplicates_removed,
        "average_price": df['Sale Price'].mean(),
        "total_basement_area": df['Basement Area Sqft'].sum()
    }

if __name__ == '__main__':
    download_dataset()
    clean_and_prepare_data()
