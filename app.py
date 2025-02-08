import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Set page config
st.set_page_config(layout="wide")

# Initialize session state for costs if not exists
if 'material_costs' not in st.session_state:
    st.session_state.material_costs = {}

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
        return pd.Timestamp('1899-12-30') + pd.Timedelta(days=float(excel_date))
    except:
        return None

# Convert dates
df['date'] = df['date'].apply(excel_date_to_datetime)

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

# Cost inputs in sidebar
st.sidebar.header("Material Costs (per lb)")
unique_material_forms = sorted(df['material_form'].dropna().unique())
for form in unique_material_forms:
    if form not in st.session_state.material_costs:
        st.session_state.material_costs[form] = 0.0
    st.session_state.material_costs[form] = st.sidebar.number_input(
        f"Cost for {form}",
        value=float(st.session_state.material_costs[form]),
        step=0.01,
        format="%.2f"
    )

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

# Calculate profits
filtered_df['cost_per_lb'] = filtered_df['material_form'].map(st.session_state.material_costs)
filtered_df['total_cost'] = filtered_df['total_weight_value'] * filtered_df['cost_per_lb']
filtered_df['profit'] = -filtered_df['amount'] - filtered_df['total_cost']  # Negative amount because income is stored as negative
filtered_df['margin'] = (filtered_df['profit'] / -filtered_df['amount']) * 100  # Calculate margin as percentage

# Create tabs
tab1, tab2 = st.tabs(["Material Analysis", "Profit Analysis"])

with tab1:
    st.title("Advanced Material Data Explorer")
    
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
        material_form_counts = filtered_df.groupby(['material', 'material_form']).agg({
            'total_weight_value': ['sum', 'count', lambda x: x.mean()],
            'amount': 'sum'
        }).reset_index()
        
        # Flatten column names and rename
        material_form_counts.columns = ['material', 'material_form', 'total_weight', 'order_count', 'avg_order_size', 'total_income']
        
        # Format the hover text
        material_form_counts['hover_text'] = (
            'Total Weight: ' + material_form_counts['total_weight'].round(0).astype(str) + ' lbs<br>' +
            'Orders: ' + material_form_counts['order_count'].astype(str) + '<br>' +
            'Avg Order: ' + material_form_counts['avg_order_size'].round(0).astype(str) + ' lbs<br>' +
            'Total Income: $' + (-material_form_counts['total_income']).round(2).astype(str)
        )
        
        fig_treemap = px.treemap(material_form_counts,
                                path=[px.Constant("All"), 'material', 'material_form'],
                                values='total_weight',
                                title='Material Hierarchy Analysis',
                                custom_data=['hover_text'])
        
        fig_treemap.update_traces(
            hovertemplate='%{label}<br>%{customdata[0]}<extra></extra>'
        )
        
        st.plotly_chart(fig_treemap)

with tab2:
    st.title("Profit Analysis")

    # Profit Overview
    st.header("Profit Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_profit = filtered_df['profit'].sum()
        st.metric("Total Profit", f"${total_profit:,.2f}")

    with col2:
        avg_margin = filtered_df['margin'].mean()
        st.metric("Average Margin", f"{avg_margin:.1f}%")

    with col3:
        total_revenue = -filtered_df['amount'].sum()  # Negative because income is stored as negative
        st.metric("Total Revenue", f"${total_revenue:,.2f}")

    with col4:
        total_cost = filtered_df['total_cost'].sum()
        st.metric("Total Cost", f"${total_cost:,.2f}")

    # Profit Over Time
    st.header("Profit Trends")
    profit_time = filtered_df.groupby(filtered_df['date'].dt.to_period(time_agg[0])).agg({
        'profit': 'sum',
        'margin': 'mean'
    }).reset_index()
    profit_time['date'] = profit_time['date'].astype(str)

    fig_profit_time = go.Figure()
    fig_profit_time.add_trace(go.Scatter(
        x=profit_time['date'],
        y=profit_time['profit'],
        name='Profit',
        mode='lines+markers'
    ))
    fig_profit_time.add_trace(go.Scatter(
        x=profit_time['date'],
        y=profit_time['margin'],
        name='Margin %',
        yaxis='y2',
        mode='lines+markers'
    ))

    fig_profit_time.update_layout(
        title=f'Profit and Margin Trends ({time_agg})',
        yaxis=dict(title='Profit ($)'),
        yaxis2=dict(title='Margin (%)', overlaying='y', side='right'),
        hovermode='x unified'
    )
    st.plotly_chart(fig_profit_time, use_container_width=True)

    # Profit by Material
    st.header("Profit by Material")
    col1, col2 = st.columns(2)

    with col1:
        material_profit = filtered_df.groupby('material').agg({
            'profit': 'sum',
            'margin': 'mean'
        }).reset_index()

        fig_material_profit = px.bar(material_profit,
                                   x='material',
                                   y=['profit', 'margin'],
                                   title='Profit and Margin by Material',
                                   barmode='group')
        st.plotly_chart(fig_material_profit)

    with col2:
        # Profit by Customer
        customer_profit = filtered_df.groupby('customer_name').agg({
            'profit': 'sum',
            'margin': 'mean'
        }).reset_index().sort_values('profit', ascending=False).head(10)

        fig_customer_profit = px.bar(customer_profit,
                                   x='customer_name',
                                   y=['profit', 'margin'],
                                   title='Top 10 Customers by Profit',
                                   barmode='group')
        fig_customer_profit.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_customer_profit)

    # Profit Heatmap
    st.header("Profit Analysis by Customer and Material")
    profit_heatmap = filtered_df.pivot_table(
        values='profit',
        index='customer_name',
        columns='material',
        aggfunc='sum',
        fill_value=0
    ).head(10)  # Top 10 customers

    fig_profit_heatmap = px.imshow(profit_heatmap,
                                  title='Customer-Material Profit Heatmap',
                                  aspect='auto',
                                  color_continuous_scale='RdYlGn')  # Red for low profit, green for high profit
    st.plotly_chart(fig_profit_heatmap)

    # Detailed Profit Data
    st.header("Detailed Profit Data")
    if not filtered_df.empty:
        profit_columns = ['customer_name', 'material', 'material_form', 
                         'total_weight_value', 'cost_per_lb', 'total_cost',
                         'amount', 'profit', 'margin', 'date']
        display_df = filtered_df[profit_columns].copy()
        display_df['date'] = display_df['date'].dt.date
        display_df['amount'] = -display_df['amount']  # Flip the sign to make it positive
        display_df = display_df.rename(columns={'amount': 'Income'})  # Rename after flipping the sign
        st.dataframe(display_df)
    else:
        st.write("No data available for the selected filters.")

# Footer
st.markdown("---")
st.markdown("Advanced Data Explorer for Material Analysis")
