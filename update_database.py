import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('invoices.db')
cursor = conn.cursor()

# Add new columns to the invoices table
cursor.execute('ALTER TABLE invoices ADD COLUMN product TEXT')
cursor.execute('ALTER TABLE invoices ADD COLUMN item_weight REAL')
cursor.execute('ALTER TABLE invoices ADD COLUMN total_weight REAL')

# Commit changes and close the connection
conn.commit()
conn.close()

print("Database schema updated successfully.")
