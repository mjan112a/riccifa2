import pandas as pd
import re
import sqlite3

def process_material_description(description):
    """
    Process a material description string to extract material, form, and weight.
    Returns tuple of (material, form, weight) or (None, None, None) if no match.
    """
    if not isinstance(description, str):
        return None, None, None
        
    # Pattern to match material descriptions
    pattern = r'(EpiX|KinetiX|DynamiX)\s+([^,]+),\s*(\d+)\s*lb'
    
    match = re.search(pattern, description)
    if match:
        material = match.group(1)
        form = match.group(2)
        weight = int(match.group(3))  # Convert to integer for calculations
        return material, form, weight
    return None, None, None

def process_data(input_file):
    """
    Process the CSV file to extract material information and calculate total weight.
    """
    # Read the CSV file with string data types for relevant columns
    df = pd.read_csv(input_file, skipinitialspace=True, dtype={
        'Date ': str,
        'Document Number ': str,
        'Name ': str,
        'Memo ': str,
        'Account ': str,
        'Qty ': str,
        'Amount ': str,
        'Item: Description (Sales) ': str,
        'Item: Item Type ': str,
        '\ufeffType ': str,
        'Type ': str
    })
    
    # Create new columns
    new_cols = {
        'material': [],
        'material_form': [],
        'weight': [],
        'total_weight': []
    }
    
    # Process each row
    for idx, row in df.iterrows():
        material, form, weight = process_material_description(row['Item: Description (Sales) '])
        
        # Store base columns
        new_cols['material'].append(material)
        new_cols['material_form'].append(form)
        new_cols['weight'].append(f"{weight} lbs" if weight is not None else None)
        
        # Calculate total weight using quantity
        if weight is not None and pd.notna(row['Qty ']):
            try:
                qty = abs(float(row['Qty ']))  # Convert to positive float
                total_weight = weight * qty
                new_cols['total_weight'].append(f"{int(total_weight)} lbs")
            except (ValueError, TypeError):
                new_cols['total_weight'].append(None)
        else:
            new_cols['total_weight'].append(None)
    
    # Add new columns to dataframe
    for col_name, col_data in new_cols.items():
        df[col_name] = col_data
    
    return df

def main():
    """
    Main function to process data and store in database
    """
    input_file = 'riccitest1.csv'
    
    try:
        # Process the data
        processed_df = process_data(input_file)
        
        # Print column types for debugging
        print("\nColumn dtypes:")
        print(processed_df.dtypes)
        
        # Print first few rows for debugging
        print("\nFirst few rows:")
        print(processed_df.head())
        
        # Connect to the SQLite database
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        
        # Insert processed data into database
        for idx, row in processed_df.iterrows():
            cursor.execute('''
                INSERT INTO invoices (
                    type, date, document_number, customer_name, memo, account, 
                    quantity, amount, item_description, item_type, 
                    material, material_form, weight, total_weight
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(row['\ufeffType '] if '\ufeffType ' in row else row['Type ']).strip(),
                str(row['Date ']).strip(),
                str(row['Document Number ']).strip(),
                str(row['Name ']).strip(),
                str(row['Memo ']).strip(),
                str(row['Account ']).strip(),
                float(str(row['Qty ']).strip()) if pd.notna(row['Qty ']) else 0.0,
                float(str(row['Amount ']).strip()) if pd.notna(row['Amount ']) else 0.0,
                str(row['Item: Description (Sales) ']).strip() if pd.notna(row['Item: Description (Sales) ']) else '',
                str(row['Item: Item Type ']).strip() if pd.notna(row['Item: Item Type ']) else '',
                row['material'],
                row['material_form'],
                row['weight'],
                row['total_weight']
            ))
        
        # Commit changes
        conn.commit()
        
        # Display summary statistics
        print("\nMaterial counts:")
        material_counts = processed_df['material'].value_counts().dropna()
        print(material_counts)
        
        print("\nTotal weight by material type:")
        material_weights = processed_df[processed_df['total_weight'].notna()].groupby('material').agg({
            'total_weight': lambda x: f"{sum(int(w.replace(' lbs', '')) for w in x)} lbs"
        })
        print(material_weights)
        
        # Display sample of processed data
        print("\nSample of processed data where material was extracted:")
        sample_df = processed_df[processed_df['material'].notna()][
            ['Item: Description (Sales) ', 'material', 'material_form', 'weight', 'Qty ', 'total_weight']
        ].head(10)
        print(sample_df)
        
        conn.close()
        print("\nData migration completed successfully.")
    except Exception as e:
        print(f"Error during data migration: {str(e)}")
        raise

if __name__ == "__main__":
    main()
