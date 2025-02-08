import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Set page config
st.set_page_config(layout="wide")

# Connect to the SQLite database
conn = sqlite3.connect('invoices.db')

# Query the invoices table
query = "SELECT * FROM invoices"
df = pd.read_sql_query(query, conn)

# Close the database connection
conn.close()

# Remove rows without total weight
df = df[df['total_weight'].notna() & (df['total_weight'] != '')]

# Convert weight strings to numeric values
def extract_weight(weight_str):
    if pd.isna(weight_str) or weight_str is None:
        return 0
    try:
        return float(weight_str.replace(' lbs', ''))
    except (ValueError, AttributeError):
        return 0

# Process weight columns
df['weight_value'] = df['weight'].apply(extract_weight)
df['total_weight_value'] = df['total_weight'].apply(extract_weight)

# Convert Excel-style dates to datetime
def excel_date_to_datetime(excel_date):
    try:
        # Excel dates are number of days since 1900-01-01
        # (except for Excel's leap year bug)
        return pd.Timestamp('1899-12-30') + pd.Timedelta(days=float(excel_date))
    except:
        return None

# Convert dates
df['date'] = df['date'].apply(excel_date_to_datetime)

# Streamlit app
st.title("Advanced Material Data Explorer")

# Sidebar filters
st.sidebar.header("Filters")

# Date range selector
date_range = st.sidebar.date_input(
    "Select Date Range",
    [df['date'].min(), df['date'].max()],
    min_value=df['date'].min().date(),
    max_value=df['date'].max().date()
)

# Time aggregation selector
time_agg = st.sidebar.selectbox(
    "Time Aggregation",
    ["Daily", "Weekly", "Monthly"]
)

# Material and customer filters
material_types = ['All'] + sorted(df['material'].dropna().unique().tolist())
selected_material = st.sidebar.selectbox("Select Material Type", material_types)

customer_names = ['All'] + sorted(df['customer_name'].unique().tolist())
selected_customer = st.sidebar.selectbox("Select Customer", customer_names)

# Filter data based on selections
filtered_df = df.copy()
if len(date_range) == 2:
    filtered_df = filtered_df[
        (filtered_df['date'].dt.date >= date_range[0]) &
        (filtered_df['date'].dt.date <= date_range[1])
    ]
if selected_material != 'All':
    filtered_df = filtered_df[filtered_df['material'] == selected_material]
if selected_customer != 'All':
    filtered_df = filtered_df[filtered_df['customer_name'] == selected_customer]

# Overview metrics in expanded format
st.header("Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_weight = filtered_df['total_weight_value'].sum()
    st.metric("Total Weight", f"{total_weight:,.0f} lbs")

with col2:
    total_orders = len(filtered_df[filtered_df['material'].notna()])
    st.metric("Total Orders", total_orders)

with col3:
    unique_customers = len(filtered_df['customer_name'].unique())
    st.metric("Unique Customers", unique_customers)

with col4:
    avg_order_size = total_weight / total_orders if total_orders > 0 else 0
    st.metric("Avg Order Size", f"{avg_order_size:,.0f} lbs")

# Time Series Analysis
st.header("Time Series Analysis")

# Prepare time series data based on selected aggregation
def aggregate_time_series(df, agg_level):
    if agg_level == "Daily":
        df['period'] = df['date'].dt.date
    elif agg_level == "Weekly":
        df['period'] = df['date'].dt.to_period('W').astype(str)
    else:  # Monthly
        df['period'] = df['date'].dt.to_period('M').astype(str)
    
    return df.groupby('period').agg({
        'total_weight_value': 'sum',
        'material': 'count'
    }).reset_index()

time_series_data = aggregate_time_series(filtered_df, time_agg)

# Create time series plot
fig_time = go.Figure()
fig_time.add_trace(go.Scatter(
    x=time_series_data['period'],
    y=time_series_data['total_weight_value'],
    name='Total Weight',
    mode='lines+markers'
))
fig_time.add_trace(go.Scatter(
    x=time_series_data['period'],
    y=time_series_data['material'],
    name='Number of Orders',
    yaxis='y2',
    mode='lines+markers'
))

fig_time.update_layout(
    title=f'{time_agg} Trends',
    yaxis=dict(title='Total Weight (lbs)'),
    yaxis2=dict(title='Number of Orders', overlaying='y', side='right'),
    hovermode='x unified'
)

st.plotly_chart(fig_time, use_container_width=True)

# Material Analysis Section
st.header("Material Analysis")
col1, col2 = st.columns(2)

with col1:
    # Material Distribution
    material_counts = filtered_df['material'].value_counts().reset_index()
    material_counts.columns = ['Material', 'Count']
    material_counts = material_counts[material_counts['Material'].notna()]

    fig_distribution = px.pie(material_counts, 
                            values='Count',
                            names='Material',
                            title='Distribution of Materials')
    st.plotly_chart(fig_distribution)

with col2:
    # Material Form Analysis
    material_form_counts = filtered_df.groupby(['material', 'material_form'])['total_weight_value'].sum().reset_index()
    
    fig_treemap = px.treemap(material_form_counts,
                            path=[px.Constant("All"), 'material', 'material_form'],
                            values='total_weight_value',
                            title='Material Hierarchy by Weight')
    st.plotly_chart(fig_treemap)

# Customer Analysis
st.header("Customer Analysis")

# Top Customers
customer_totals = filtered_df.groupby('customer_name').agg({
    'total_weight_value': 'sum',
    'material': 'count'
}).reset_index()
customer_totals.columns = ['Customer', 'Total Weight (lbs)', 'Number of Orders']
customer_totals = customer_totals.sort_values('Total Weight (lbs)', ascending=False).head(10)

fig_customers = px.bar(customer_totals,
                      x='Customer',
                      y=['Total Weight (lbs)', 'Number of Orders'],
                      title='Top 10 Customers Analysis',
                      barmode='group')
fig_customers.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_customers)

# Customer-Material Heatmap
pivot_data = filtered_df.pivot_table(
    values='total_weight_value',
    index='customer_name',
    columns='material',
    aggfunc='sum',
    fill_value=0
).head(10)  # Top 10 customers

fig_heatmap = px.imshow(pivot_data,
                        title='Customer-Material Relationship Heatmap',
                        aspect='auto')
st.plotly_chart(fig_heatmap)

# Detailed Data View
st.header("Detailed Data")
if not filtered_df.empty:
    columns_to_display = ['customer_name', 'material', 'material_form', 
                         'weight', 'total_weight', 'amount', 'date']
    st.dataframe(filtered_df[columns_to_display])
else:
    st.write("No data available for the selected filters.")

# Footer
st.markdown("---")
st.markdown("Advanced Data Explorer for Material Analysis")
