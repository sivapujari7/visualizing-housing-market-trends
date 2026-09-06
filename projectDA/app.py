import os
import pandas as pd
from flask import Flask, render_template, jsonify, request
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

def get_cleaned_data():
    """Loads the cleaned dataset."""
    path = app.config['CLEANED_DATA_PATH']
    if not os.path.exists(path):
        # Fallback to running prep if file doesn't exist
        print(f"Cleaned data not found at {path}. Running data prep...")
        from data_prep import clean_and_prepare_data, download_dataset
        download_dataset()
        clean_and_prepare_data()
    return pd.read_csv(path)

@app.route('/')
def home():
    """Home landing page route."""
    try:
        df = get_cleaned_data()
        stats = {
            'total_houses': len(df),
            'avg_price': f"${df['Sale Price'].mean():,.2f}",
            'avg_age': f"{df['House Age'].mean():.1f} years",
            'renovated_pct': f"{(df['Renovation Status'] == 'Renovated').mean():.1%}"
        }
    except Exception as e:
        print(f"Error loading stats for home: {e}")
        stats = {
            'total_houses': "N/A",
            'avg_price': "N/A",
            'avg_age': "N/A",
            'renovated_pct': "N/A"
        }
    return render_template('home.html', stats=stats)

@app.route('/dashboard')
def dashboard():
    """Dashboard page route."""
    return render_template('dashboard.html', 
                           tableau_url=app.config['TABLEAU_DASHBOARD_URL'])

@app.route('/storyboard')
def storyboard():
    """Storyboard page route."""
    return render_template('storyboard.html', 
                           tableau_url=app.config['TABLEAU_STORYBOARD_URL'])

@app.route('/about')
def about():
    """About page route."""
    return render_template('about.html')

# --- API Endpoints for Chart.js Fallback Dashboard ---

@app.route('/api/kpis')
def api_kpis():
    """Returns core KPI figures, optionally filtered."""
    try:
        df = get_cleaned_data()
        
        # Apply filters if passed as query params
        df = apply_filters(df, request.args)
        
        kpis = {
            'total_houses': int(len(df)),
            'avg_price': float(df['Sale Price'].mean()) if len(df) > 0 else 0,
            'total_basement_area': int(df['Basement Area Sqft'].sum()) if len(df) > 0 else 0,
            'avg_price_per_sqft': float(df['Price per Sqft'].mean()) if len(df) > 0 else 0
        }
        return jsonify(success=True, data=kpis)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/api/charts/sales_by_renovation')
def sales_by_renovation():
    """Returns sales metrics binned by years since renovation/construction."""
    try:
        df = get_cleaned_data()
        df = apply_filters(df, request.args)
        
        if len(df) == 0:
            return jsonify(success=True, data=[])

        # Bin Years Since Renovation
        # Ranges: 0-5 years, 6-10 years, 11-20 years, 21-40 years, 40+ years
        bins = [-1, 5, 10, 20, 40, 200]
        labels = ['0-5 Years', '6-10 Years', '11-20 Years', '21-40 Years', '40+ Years']
        
        df['Renovation Age Group'] = pd.cut(df['Years Since Renovation'], bins=bins, labels=labels)
        
        summary = df.groupby('Renovation Age Group', observed=False).agg(
            total_sales=('Sale Price', 'sum'),
            avg_price=('Sale Price', 'mean'),
            house_count=('id', 'count')
        ).reset_index()
        
        summary['total_sales'] = summary['total_sales'].fillna(0)
        summary['avg_price'] = summary['avg_price'].fillna(0)
        summary['house_count'] = summary['house_count'].fillna(0)
        
        data_list = []
        for _, row in summary.iterrows():
            data_list.append({
                'bin': row['Renovation Age Group'],
                'total_sales': float(row['total_sales']),
                'avg_price': float(row['avg_price']),
                'count': int(row['house_count'])
            })
            
        return jsonify(success=True, data=data_list)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/api/charts/age_by_renovation')
def age_by_renovation():
    """Returns the distribution of houses and house age by renovation status."""
    try:
        df = get_cleaned_data()
        df = apply_filters(df, request.args)
        
        if len(df) == 0:
            return jsonify(success=True, data=[])
            
        summary = df.groupby('Renovation Status').agg(
            count=('id', 'count'),
            avg_age=('House Age', 'mean'),
            avg_price=('Sale Price', 'mean')
        ).reset_index()
        
        data_list = []
        for _, row in summary.iterrows():
            data_list.append({
                'status': row['Renovation Status'],
                'count': int(row['count']),
                'avg_age': float(round(row['avg_age'], 1)),
                'avg_price': float(round(row['avg_price'], 2))
            })
            
        return jsonify(success=True, data=data_list)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/api/charts/age_by_features')
def age_by_features():
    """Returns average house age grouped by Bedrooms, Bathrooms, and Floors."""
    try:
        df = get_cleaned_data()
        df = apply_filters(df, request.args)
        
        if len(df) == 0:
            return jsonify(success=True, data={})

        # 1. Age by Bedrooms (grouping 5+ together)
        df['Bedrooms_Group'] = df['Bedrooms'].apply(lambda x: '5+' if x >= 5 else str(int(x)))
        bed_summary = df.groupby('Bedrooms_Group').agg(
            avg_age=('House Age', 'mean'),
            count=('id', 'count')
        ).sort_index().to_dict('index')
        
        # 2. Age by Floors (rounding floor values for clean charts)
        df['Floors_Group'] = df['Floors'].apply(lambda x: f"{x:.1f} Flr")
        floor_summary = df.groupby('Floors_Group').agg(
            avg_age=('House Age', 'mean'),
            count=('id', 'count')
        ).sort_index().to_dict('index')

        # 3. Age by Bathrooms (binning bathrooms: 0-1.5, 1.75-2.5, 2.75-3.5, 3.75+)
        def bin_bathrooms(b):
            if b <= 1.5: return '0-1.5 Baths'
            elif b <= 2.5: return '1.75-2.5 Baths'
            elif b <= 3.5: return '2.75-3.5 Baths'
            else: return '3.75+ Baths'
            
        df['Bathrooms_Group'] = df['Bathrooms'].apply(bin_bathrooms)
        bath_order = ['0-1.5 Baths', '1.75-2.5 Baths', '2.75-3.5 Baths', '3.75+ Baths']
        
        bath_summary_raw = df.groupby('Bathrooms_Group').agg(
            avg_age=('House Age', 'mean'),
            count=('id', 'count')
        ).to_dict('index')
        
        bath_summary = {key: bath_summary_raw.get(key, {'avg_age': 0, 'count': 0}) for key in bath_order}

        result = {
            'bedrooms': {k: {'avg_age': float(round(v['avg_age'], 1)), 'count': int(v['count'])} for k, v in bed_summary.items()},
            'floors': {k: {'avg_age': float(round(v['avg_age'], 1)), 'count': int(v['count'])} for k, v in floor_summary.items()},
            'bathrooms': {k: {'avg_age': float(round(v['avg_age'], 1)), 'count': int(v['count'])} for k, v in bath_summary.items()}
        }
        
        return jsonify(success=True, data=result)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

def apply_filters(df, args):
    """Helper to apply query parameter filters to a dataframe."""
    # Bedrooms filter
    bedrooms = args.get('bedrooms')
    if bedrooms and bedrooms != 'All':
        if bedrooms == '5+':
            df = df[df['Bedrooms'] >= 5]
        else:
            df = df[df['Bedrooms'] == int(bedrooms)]
            
    # Bathrooms filter
    bathrooms = args.get('bathrooms')
    if bathrooms and bathrooms != 'All':
        if bathrooms == '0-1.5':
            df = df[df['Bathrooms'] <= 1.5]
        elif bathrooms == '1.75-2.5':
            df = df[(df['Bathrooms'] > 1.5) & (df['Bathrooms'] <= 2.5)]
        elif bathrooms == '2.75-3.5':
            df = df[(df['Bathrooms'] > 2.5) & (df['Bathrooms'] <= 3.5)]
        elif bathrooms == '3.75+':
            df = df[df['Bathrooms'] > 3.5]

    # Floors filter
    floors = args.get('floors')
    if floors and floors != 'All':
        df = df[df['Floors'] == float(floors)]

    # Renovation status filter
    ren_status = args.get('renovation_status')
    if ren_status and ren_status != 'All':
        df = df[df['Renovation Status'] == ren_status]

    # House Age filter (binned)
    age = args.get('house_age')
    if age and age != 'All':
        if age == 'New (<10 yrs)':
            df = df[df['House Age'] < 10]
        elif age == 'Moderate (10-30 yrs)':
            df = df[(df['House Age'] >= 10) & (df['House Age'] <= 30)]
        elif age == 'Old (30-50 yrs)':
            df = df[(df['House Age'] > 30) & (df['House Age'] <= 50)]
        elif age == 'Vintage (50+ yrs)':
            df = df[df['House Age'] > 50]

    # Sale Price filter (binned)
    price = args.get('sale_price')
    if price and price != 'All':
        if price == 'Under $300k':
            df = df[df['Sale Price'] < 300000]
        elif price == '$300k - $600k':
            df = df[(df['Sale Price'] >= 300000) & (df['Sale Price'] <= 600000)]
        elif price == '$600k - $1M':
            df = df[(df['Sale Price'] > 600000) & (df['Sale Price'] <= 1000000)]
        elif price == 'Over $1M':
            df = df[df['Sale Price'] > 1000000]

    return df

if __name__ == '__main__':
    # Verify cleaned data path is set up, else prep it
    get_cleaned_data()
    app.run(debug=True, port=5000)
