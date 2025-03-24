#!/bin/bash
cd "/home/tom/github/tom-sapletta-com/portfolio"
source "/home/tom/github/tom-sapletta-com/portfolio/portfolio-env/bin/activate"
python portfolio_generator.py
deactivate
