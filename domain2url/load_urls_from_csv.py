#!/usr/bin/env python3
# domain2url/load_urls_from_csv.py
import csv
import os
from typing import List, Dict, Optional


def load_urls_from_csv(file_path: str,
                       only_available: bool = True,
                       protocol: Optional[str] = None,
                       domain: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Ładuje URL z pliku CSV z możliwością filtrowania.

    :param file_path: Ścieżka do pliku CSV
    :param only_available: Filtruj tylko dostępne URL
    :param protocol: Opcjonalny filtr protokołu (np. 'http', 'https')
    :param domain: Opcjonalny filtr domeny
    :return: Lista słowników z informacjami o URL
    """
    # Sprawdź, czy plik istnieje
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Plik {file_path} nie istnieje.")

    # Lista do przechowywania URL
    filtered_urls = []

    try:
        # Otwórz plik CSV
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # Użyj DictReader do wygodnego odczytu
            reader = csv.DictReader(csvfile)

            # Iteruj przez wiersze
            for row in reader:
                # Konwersja 'available' na bool (zabezpieczenie)
                available = row['available'].lower() in ['true', '1', 'yes']

                # Filtrowanie dostępności
                if only_available and not available:
                    continue

                # Filtrowanie protokołu
                if protocol and not row['url'].startswith(protocol + '://'):
                    continue

                # Filtrowanie domeny
                if domain and row['domain'] != domain:
                    continue

                # Dodaj do wyniku
                filtered_urls.append({
                    'domain': row['domain'],
                    'url': row['url'],
                    'available': available
                })

    except (csv.Error, IOError) as e:
        raise ValueError(f"Błąd odczytu pliku CSV: {e}")

    return filtered_urls


def print_urls(urls: List[Dict[str, str]], verbose: bool = False):
    """
    Wyświetla załadowane URL.

    :param urls: Lista URL do wyświetlenia
    :param verbose: Tryb szczegółowy
    """
    if not urls:
        print("Brak URL do wyświetlenia.")
        return

    print(f"Znaleziono {len(urls)} URL:")
    for url_info in urls:
        if verbose:
            print(f"Domena: {url_info['domain']}")
            print(f"URL: {url_info['url']}")
            print(f"Dostępna: {url_info['available']}")
            print("-" * 30)
        else:
            print(url_info['url'])


# Przykład użycia
def main():
    try:
        # Przykładowe użycie funkcji
        # Wszystkie dostępne URL
        all_urls = load_urls_from_csv('domain_urls.csv')
        print("Wszystkie dostępne URL:")
        print_urls(all_urls)

        print("\n--- Tylko protokół HTTP ---")
        # Tylko URL z protokołem HTTP
        http_urls = load_urls_from_csv('domain_urls.csv', protocol='http')
        print_urls(http_urls)

        print("\n--- Dla konkretnej domeny ---")
        # Dla konkretnej domeny
        domain_urls = load_urls_from_csv('domain_urls.csv', domain='airsca.com')
        print_urls(domain_urls, verbose=True)

    except Exception as e:
        print(f"Wystąpił błąd: {e}")


if __name__ == "__main__":
    main()