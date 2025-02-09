import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from supabase import create_client

# Initialize Supabase client with direct values and options
options = {
    'headers': {
        'X-Client-Info': 'supabase-py/2.3.0',
    },
    'auth': {
        'persistSession': False
    }
}

supabase = create_client(
    "https://vnsmqgwwpdssmbtmiwrd.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZuc21xZ3d3cGRzc21idG1pd3JkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkwNTk0NzUsImV4cCI6MjA1NDYzNTQ3NX0.yOWDTHq8GluOgjnAeEFj1hm0aE3ll1Axz9bSpnFHaFs",
    options=options
)

# Set page config
st.set_page_config(layout="wide")

# Initialize authentication state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Authentication credentials - store these securely in production
VALID_USERS = {
    "admin": "riccifa2024",  # You can change these credentials later
}

# Login form if not authenticated
if not st.session_state.authenticated:
    st.title("Login Required")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if username in VALID_USERS and password == VALID_USERS[username]:
                st.session_state.authenticated = True
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")
    st.stop()

# Initialize session state for costs if not exists
if 'material_costs' not in st.session_state:
    st.session_state.material_costs = {}

# Query the invoices table from Supabase
response = supabase.table('invoices').select("*").execute()
df = pd.DataFrame(response.data)

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
        # Try to convert to float first to handle Excel numeric dates
        numeric_date = float(excel_date)
        # Use 'excel' origin for proper conversion of Excel dates
        return pd.to_datetime(numeric_date, unit='D', origin='1899-12-30')
    except (ValueError, TypeError):
        try:
            # If not a number, try normal datetime parsing
            return pd.to_datetime(excel_date)
        except:
            return None

# Convert dates
df['date'] = df['date'].apply(excel_date_to_datetime)

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["Material Analysis", "Profit Analysis", "Interactive Metrics", "Raw Data"])

with tab1:
    st.title("Advanced Material Data Explorer")
    
    # Sidebar filters
    st.sidebar.header("Filters")

    # Date range selector
    # Get valid min and max dates with error handling
    valid_dates = df['date'].dropna()
    if len(valid_dates) > 0:
        min_date = valid_dates.min()
        max_date = valid_dates.max()
        
        date_range = st.sidebar.date_input(
            "Select Date Range",
            [min_date, max_date],
            min_value=min_date.date(),
            max_value=max_date.date()
        )
    else:
        st.error("No valid dates found in the data")
        date_range = []

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
        # Create a copy to avoid modifying the original dataframe
        df = df.copy()
        
        # Ensure date column is datetime
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Drop rows where date conversion failed
        df = df[df['date'].notna()]
        
        if df.empty:
            return pd.DataFrame(columns=['period', 'total_weight_value', 'material'])
            
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

    # Create time series plot if data exists
    if not filtered_df.empty:
        time_series_data = aggregate_time_series(filtered_df, time_agg)
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
    else:
        st.write("No data available for the selected time period")

    # Material Analysis Section
    st.header("Material Analysis")
    col1, col2 = st.columns(2)

    with col1:
        # Material Distribution
        if not filtered_df.empty:
            material_counts = filtered_df['material'].value_counts().reset_index()
            material_counts.columns = ['Material', 'Count']
            material_counts = material_counts[material_counts['Material'].notna()]

            if not material_counts.empty:
                fig_distribution = px.pie(material_counts, 
                                    values='Count',
                                    names='Material',
                                    title='Distribution of Materials')
                st.plotly_chart(fig_distribution)
            else:
                st.write("No material data available for the selected filters")
        else:
            st.write("No data available for the selected filters")

    with col2:
        # Material Form Analysis
        if not filtered_df.empty:
            material_form_counts = filtered_df.groupby(['material', 'material_form']).agg({
                'total_weight_value': ['sum', 'count', lambda x: x.mean()],
                'amount': 'sum'
            }).reset_index()
            
            if not material_form_counts.empty:
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
            else:
                st.write("No material form data available for the selected filters")
        else:
            st.write("No data available for the selected filters")


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
    # Use consistent time aggregation
    def get_period_str(date_col, agg_level):
        if agg_level == "Daily":
            return date_col.dt.date
        elif agg_level == "Weekly":
            return date_col.dt.to_period('W').astype(str)
        else:  # Monthly
            return date_col.dt.to_period('M').astype(str)

    # Create profit trends plot if data exists
    if not filtered_df.empty:
        profit_time = filtered_df.copy()
        profit_time['period'] = get_period_str(profit_time['date'], time_agg)
        profit_time = profit_time.groupby('period').agg({
            'profit': 'sum',
            'margin': 'mean'
        }).reset_index()

        fig_profit_time = go.Figure()
        fig_profit_time.add_trace(go.Scatter(
            x=profit_time['period'],
            y=profit_time['profit'],
            name='Profit',
            mode='lines+markers'
        ))
        fig_profit_time.add_trace(go.Scatter(
            x=profit_time['period'],
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
    else:
        st.write("No data available for the selected time period")

    # Profit by Material
    st.header("Profit by Material")
    col1, col2 = st.columns(2)

    with col1:
        if not filtered_df.empty:
            material_profit = filtered_df.groupby('material').agg({
                'profit': 'sum',
                'margin': 'mean'
            }).reset_index()

            if not material_profit.empty:
                fig_material_profit = px.bar(material_profit,
                                       x='material',
                                       y=['profit', 'margin'],
                                       title='Profit and Margin by Material',
                                       barmode='group')
                st.plotly_chart(fig_material_profit)
            else:
                st.write("No material profit data available for the selected filters")
        else:
            st.write("No data available for the selected filters")

    with col2:
        if not filtered_df.empty:
            # Profit by Customer
            customer_profit = filtered_df.groupby('customer_name').agg({
                'profit': 'sum',
                'margin': 'mean'
            }).reset_index().sort_values('profit', ascending=False).head(10)

            if not customer_profit.empty:
                fig_customer_profit = px.bar(customer_profit,
                                       x='customer_name',
                                       y=['profit', 'margin'],
                                       title='Top 10 Customers by Profit',
                                       barmode='group')
                fig_customer_profit.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_customer_profit)
            else:
                st.write("No customer profit data available for the selected filters")
        else:
            st.write("No data available for the selected filters")

    # Profit Heatmap
    st.header("Profit Analysis by Customer and Material")
    if not filtered_df.empty:
        profit_heatmap = filtered_df.pivot_table(
            values='profit',
            index='customer_name',
            columns='material',
            aggfunc='sum',
            fill_value=0
        ).head(10)  # Top 10 customers

        if not profit_heatmap.empty:
            fig_profit_heatmap = px.imshow(profit_heatmap,
                                      title='Customer-Material Profit Heatmap',
                                      aspect='auto',
                                      color_continuous_scale='RdYlGn')  # Red for low profit, green for high profit
            st.plotly_chart(fig_profit_heatmap)
        else:
            st.write("No profit heatmap data available for the selected filters")
    else:
        st.write("No data available for the selected filters")

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

with tab3:
    st.title("Interactive Metrics Analysis")

    # Weight vs Time and Client and Segment
    st.header("Weight Analysis by Time, Client, and Segment")
    
    # Get unique segments for filtering
    segments = ['All'] + sorted(filtered_df['material_form'].unique().tolist())
    selected_segment = st.selectbox("Select Segment", segments, key='segment_selector')
    
    # Filter by segment if needed
    segment_df = filtered_df if selected_segment == 'All' else filtered_df[filtered_df['material_form'] == selected_segment]
    
    if not segment_df.empty:
        # Prepare time series data with client breakdown
        weight_time_client = segment_df.copy()
        weight_time_client['period'] = get_period_str(weight_time_client['date'], time_agg)
        weight_time_client = weight_time_client.groupby(['period', 'customer_name'])['total_weight_value'].sum().reset_index()
        
        # Create interactive weight vs time plot
        fig_weight_client = px.line(weight_time_client,
                                  x='period',
                                  y='total_weight_value',
                                  color='customer_name',
                                  title=f'Weight Trends by Client ({time_agg})',
                                  labels={'total_weight_value': 'Total Weight (lbs)',
                                         'period': 'Time Period',
                                         'customer_name': 'Client'})
        fig_weight_client.update_layout(hovermode='x unified')
        st.plotly_chart(fig_weight_client, use_container_width=True)
    else:
        st.write("No data available for the selected filters")

    # Other Metrics vs Time
    st.header("Multiple Metrics Analysis")
    
    # Define available metrics
    metrics = {
        'Total Revenue': lambda df: -df['amount'].sum(),
        'Average Order Value': lambda df: -df['amount'].mean(),
        'Profit per Order': lambda df: df['profit'].mean(),
        'Orders per Customer': lambda df: df.groupby('customer_name').size().mean(),
        'Average Margin': lambda df: df['margin'].mean(),
        'Total Weight per Order': lambda df: df['total_weight_value'].mean()
    }
    
    # Let user select metrics to display
    selected_metrics = st.multiselect(
        "Select Metrics to Display",
        list(metrics.keys()),
        default=['Total Revenue', 'Average Margin']
    )
    
    if selected_metrics and not filtered_df.empty:
        # Prepare time series data for selected metrics
        metrics_df = filtered_df.copy()
        metrics_df['period'] = get_period_str(metrics_df['date'], time_agg)
        
        # Calculate metrics over time
        metrics_over_time = []
        for period in sorted(metrics_df['period'].unique()):
            period_data = metrics_df[metrics_df['period'] == period]
            period_metrics = {'period': period}
            for metric in selected_metrics:
                period_metrics[metric] = metrics[metric](period_data)
            metrics_over_time.append(period_metrics)
        
        metrics_df = pd.DataFrame(metrics_over_time)
        
        # Create interactive multi-metric plot
        fig_metrics = go.Figure()
        for metric in selected_metrics:
            fig_metrics.add_trace(go.Scatter(
                x=metrics_df['period'],
                y=metrics_df[metric],
                name=metric,
                mode='lines+markers'
            ))
        
        fig_metrics.update_layout(
            title='Multiple Metrics Over Time',
            hovermode='x unified',
            showlegend=True
        )
        st.plotly_chart(fig_metrics, use_container_width=True)
    else:
        st.write("Please select at least one metric to display")

    # Quantity of Orders by Client Monthly by Segment
    st.header("Monthly Order Analysis")
    
    if not filtered_df.empty:
        # Prepare monthly order data
        monthly_orders = filtered_df.copy()
        monthly_orders['month'] = monthly_orders['date'].dt.to_period('M').astype(str)
        monthly_orders = monthly_orders.groupby(['month', 'customer_name', 'material_form']).size().reset_index(name='order_count')
        
        # Create heatmap
        fig_monthly = px.density_heatmap(
            monthly_orders,
            x='month',
            y='customer_name',
            z='order_count',
            facet_col='material_form',
            title='Monthly Order Quantity by Client and Segment',
            labels={'order_count': 'Number of Orders',
                   'month': 'Month',
                   'customer_name': 'Client',
                   'material_form': 'Segment'},
            color_continuous_scale='Viridis'
        )
        
        fig_monthly.update_layout(
            height=600,
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_monthly, use_container_width=True)
    else:
        st.write("No data available for the selected filters")

with tab4:
    st.title("Raw Supabase Data")
    
    # Get all columns from the original dataframe
    all_columns = df.columns.tolist()
    
    # Column selector
    selected_columns = st.multiselect(
        "Select Columns to Display",
        all_columns,
        default=['date', 'customer_name', 'material', 'material_form', 'total_weight', 'amount']
    )
    
    # Create display dataframe
    if selected_columns:
        display_raw_df = df[selected_columns].copy()
        
        # Convert date column to readable format if it exists
        if 'date' in selected_columns:
            display_raw_df['date'] = display_raw_df['date'].dt.date
            
        # Convert amount to positive if it exists
        if 'amount' in selected_columns:
            display_raw_df['amount'] = -display_raw_df['amount']
        
        # Add search functionality
        search_term = st.text_input("Search in any column", "")
        
        if search_term:
            mask = pd.DataFrame([display_raw_df[col].astype(str).str.contains(search_term, case=False, na=False)
                               for col in display_raw_df.columns]).any()
            display_raw_df = display_raw_df[mask]
        
        # Display row count
        st.write(f"Showing {len(display_raw_df)} rows")
        
        # Display the data with sorting capability
        st.dataframe(
            display_raw_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Add download button
        csv = display_raw_df.to_csv(index=False)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name="supabase_data.csv",
            mime="text/csv"
        )
    else:
        st.warning("Please select at least one column to display")

    # Footer
st.markdown("---")
st.markdown("Advanced Data Explorer for Material Analysis")
