import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client
import requests

# Load environment variables
load_dotenv()

def migrate_data():
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase = create_client(supabase_url, supabase_key)
    
    try:
        # Connect to SQLite database
        sqlite_conn = sqlite3.connect('invoices.db')
        
        # Read data from SQLite
        df = pd.read_sql_query("SELECT * FROM invoices", sqlite_conn)
        sqlite_conn.close()
        
        # Remove the SQLite id column if it exists
        if 'id' in df.columns:
            df = df.drop('id', axis=1)
        
        # Convert DataFrame to list of dictionaries
        records = df.to_dict('records')
        
        # Insert data into Supabase using REST API
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        # Split records into chunks to avoid request size limits
        chunk_size = 1000
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            response = requests.post(
                f"{supabase_url}/rest/v1/invoices",
                headers=headers,
                json=chunk
            )
            response.raise_for_status()
            print(f"Migrated records {i} to {i + len(chunk)}")
        
        print(f"Successfully migrated {len(records)} records to Supabase")
        
    except Exception as e:
        print(f"Error migrating data: {str(e)}")

if __name__ == "__main__":
    migrate_data()