#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to extract organization names from the provided list and create a CSV with domains
"""

import csv
import re

# Polish keywords/suffixes to identify Polish names
POLISH_KEYWORDS = [
    'pl', 'polska', 'polski', 'polskie', 'polskiego', 'polskiej', 'polskich',
    'wdrozenie', 'zlecenia', 'planowanie', 'kodziaki', 'entuzjasta', 'edukacjadomowa',
    'estymacja', 'ewaporacja', 'demogracja', 'dobryemail', 'anonimizacja',
    'nierezydent', 'spekulacja', 'modularyzacja'
]


def is_polish_name(name):
    """Check if the name appears to be Polish"""
    # Check if ends with -pl
    if name.endswith('-pl'):
        return True

    # Check for Polish keywords
    for keyword in POLISH_KEYWORDS:
        if keyword in name.lower():
            return True

    return False


def generate_domain(name):
    """Generate domain name based on the rules"""
    # Remove 'Owner' or other status text that might be in the name
    name = name.split(' ')[0].strip()

    # Handle special cases for -com and -pl endings
    if name.endswith('-com'):
        domain = name[:-4] + '.com'  # Replace -com with .com
    elif name.endswith('-pl'):
        domain = name[:-3] + '.pl'  # Replace -pl with .pl
    elif name.endswith('-de'):
        domain = name[:-3] + '.de'  # Replace -pl with .pl
    elif name.endswith('-org'):
        domain = name[:-4] + '.org'  # Replace -pl with .pl
    elif name.endswith('-app'):
        domain = name[:-4] + '.app'  # Replace -pl with .pl
    elif name.endswith('-info'):
        domain = name[:-5] + '.info'  # Replace -pl with .pl
    else:
        # For other cases, add .pl for Polish names, otherwise .com
        if is_polish_name(name):
            domain = name + '.pl'
        else:
            domain = name + '.com'

    return domain


def main():
    # Read the input from paste.txt
    with open("domains.csv", "w", newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=';')
        csvwriter.writerow(["name", "domain"])  # Write header

        # Get the list of organization names from paste.txt
        with open("org.txt", "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Extract organization name (first word in the line)
                parts = line.split(' ')
                org_name = parts[0].strip()

                # Generate domain name
                domain = generate_domain(org_name)

                # Write to CSV
                csvwriter.writerow([org_name, domain])

    print(f"Domains extracted and saved to domains.csv")


if __name__ == "__main__":
    main()