pip install -r requirements.txt
mkdir -p staticfiles
python -m streamlit run app.py --server.port 8501 --browser.serverAddress 0.0.0.0