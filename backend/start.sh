#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Start Flask development server
flask run --host=0.0.0.0 --port=5000
