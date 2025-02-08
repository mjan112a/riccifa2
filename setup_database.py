import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('invoices.db')
cursor = conn.cursor()

# Drop existing table if it exists
cursor.execute('DROP TABLE IF EXISTS invoices')

# Create the invoices table with new columns
cursor.execute('''
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    date TEXT,
    document_number TEXT,
    customer_name TEXT,
    memo TEXT,
    account TEXT,
    quantity REAL,
    amount REAL,
    item_description TEXT,
    item_type TEXT,
    material TEXT,
    material_form TEXT,
    weight TEXT,
    total_weight TEXT
)
''')

# Commit changes and close the connection
conn.commit()
conn.close()

print("Database and table created successfully with updated schema.")
