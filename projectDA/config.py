import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'antigravity-dev-secret-key-1337')
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RAW_DATA_PATH = os.path.join(BASE_DIR, 'data', 'raw_housing_data.csv')
    CLEANED_DATA_PATH = os.path.join(BASE_DIR, 'data', 'cleaned_housing_data.csv')
    
    # Tableau Public default URLs (Fallback/Template values that the user can replace)
    # The user can customize these after publishing their twb workbook.
    TABLEAU_DASHBOARD_URL = os.environ.get(
        'TABLEAU_DASHBOARD_URL', 
        'https://public.tableau.com/views/KingCountyHouseSales_15967067888740/Dashboard1'
    )
    
    TABLEAU_STORYBOARD_URL = os.environ.get(
        'TABLEAU_STORYBOARD_URL', 
        'https://public.tableau.com/views/KingCountyHouseSales-Storyboard/Storyboard'
    )
