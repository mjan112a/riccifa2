mkdir -p ~/.streamlit/

# Export environment variables if not set
if [ -z "$SUPABASE_URL" ]; then
    export SUPABASE_URL="https://vnsmqgwwpdssmbtmiwrd.supabase.co"
fi

if [ -z "$SUPABASE_KEY" ]; then
    export SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZuc21xZ3d3cGRzc21idG1pd3JkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkwNTk0NzUsImV4cCI6MjA1NDYzNTQ3NX0.yOWDTHq8GluOgjnAeEFj1hm0aE3ll1Axz9bSpnFHaFs"
fi

# Create Streamlit configuration
echo "\
[server]\n\
headless = true\n\
enableCORS = false\n\
port = $PORT\n\
\n\
[browser]\n\
serverAddress = '0.0.0.0'\n\
" > ~/.streamlit/config.toml
