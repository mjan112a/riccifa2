# Material Data Explorer

An interactive dashboard for analyzing material sales data with advanced visualization capabilities.

## Features

- Interactive time series analysis with customizable date ranges
- Material distribution and hierarchy visualization
- Customer analysis with detailed metrics
- Advanced filtering capabilities
- Weight tracking and analysis
- Dynamic data aggregation

## Components

- `app.py`: Main Streamlit application with interactive dashboard
- `migrate_data.py`: Data processing and database migration script
- `setup_database.py`: Database initialization and schema setup
- `update_database.py`: Database update utilities

## Setup

1. Install dependencies:
```bash
pip install streamlit pandas plotly sqlite3
```

2. Initialize the database:
```bash
python setup_database.py
```

3. Migrate data:
```bash
python migrate_data.py
```

4. Run the application:
```bash
streamlit run app.py
```

## Data Analysis Features

- Time-based trend analysis
- Material distribution visualization
- Customer behavior insights
- Weight tracking and aggregation
- Interactive filtering and drill-down capabilities

## Technology Stack

- Python
- Streamlit
- Pandas
- Plotly
- SQLite
