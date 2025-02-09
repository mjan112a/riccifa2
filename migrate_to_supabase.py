import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def migrate_data():
    # Connect to SQLite database
    sqlite_conn = sqlite3.connect('invoices.db')
    
    # Read data from SQLite
    df = pd.read_sql_query("SELECT * FROM invoices", sqlite_conn)
    sqlite_conn.close()
    
    # Initialize Supabase client
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
    
    # Convert DataFrame to list of dictionaries
    records = df.to_dict('records')
    
    # Insert data into Supabase
    try:
        response = supabase.table('invoices').insert(records).execute()
        print(f"Successfully migrated {len(records)} records to Supabase")
    except Exception as e:
        print(f"Error migrating data: {str(e)}")

if __name__ == "__main__":
    migrate_data()