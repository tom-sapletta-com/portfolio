#!/bin/bash
cd "/home/tom/github/tom-sapletta-com/portfolio"
source "/home/tom/github/tom-sapletta-com/portfolio/venv/bin/activate"
python portfolio_generator.py
deactivate
