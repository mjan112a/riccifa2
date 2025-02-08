#!/bin/bash
python3.9 -m pip install -r requirements.txt
python3.9 -m streamlit run app.py --server.port $PORT --server.address 0.0.0.0