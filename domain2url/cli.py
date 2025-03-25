#!/usr/bin/env python3
# domain2url/main.py
import os
import sys
import csv
import argparse
import logging
import urllib3
from typing import List, Dict
from dotenv import load_dotenv
import requests

# Załaduj zmienne środowiskowe
load_dotenv()

# Konfiguracja domyślnych wartości
DEFAULT_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 5))
DEFAULT_USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0')
DEFAULT_LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
DEFAULT_LOG_FILE = os.getenv('LOG_FILE', 'url_generator.log')
DEFAULT_LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
DEFAULT_OUTPUT_SUFFIX = os.getenv('DEFAULT_OUTPUT_SUFFIX', '_urls.csv')
DEFAULT_ONLY_AVAILABLE = os.getenv('ONLY_AVAILABLE', 'false').lower() == 'true'
DEFAULT_VERBOSE = os.getenv('VERBOSE', 'false').lower() == 'true'

# Konfiguracja protokołów i wariantów www
URL_PROTOCOLS = os.getenv('URL_PROTOCOLS', 'http,https').split(',')
USE_WWW_VARIANTS = os.getenv('URL_WWW_VARIANTS', 'true').lower() == 'true'

# Wyłączenie ostrzeżeń SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def setup_logging(log_level: str = DEFAULT_LOG_LEVEL,
                  log_file: str = DEFAULT_LOG_FILE,
                  log_format: str = DEFAULT_LOG_FORMAT):
    """Konfiguracja systemu logowania."""
    # Konwersja poziomu logowania
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Nieprawidłowy poziom logowania: {log_level}')

    # Konfiguracja formatu logowania
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def generate_urls(domain: str) -> List[str]:
    """Generuje różne warianty URL dla danej domeny."""
    urls = []
    for protocol in URL_PROTOCOLS:
        # Dodaj bazowy URL bez www
        urls.append(f'{protocol}://{domain}')

        # Opcjonalnie dodaj warianty z www
        if USE_WWW_VARIANTS:
            urls.append(f'{protocol}://www.{domain}')

    return urls


def check_url_availability(url: str,
                           timeout: int = DEFAULT_TIMEOUT,
                           logger: logging.Logger = None) -> bool:
    """Sprawdza dostępność URL."""
    try:
        # Dodaj nagłówek User-Agent, aby uniknąć blokowania
        headers = {
            'User-Agent': DEFAULT_USER_AGENT
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            verify=False,  # Wyłączenie weryfikacji SSL
            allow_redirects=True
        )

        # Sprawdzenie kodu odpowiedzi
        is_available = response.status_code < 400

        if logger:
            logger.info(f"URL: {url}, Status: {response.status_code}, Dostępny: {is_available}")

        return is_available

    except Exception as e:
        if logger:
            logger.warning(f"Błąd sprawdzania URL {url}: {e}")
        return False


# Python
def sort_by_length_descending(arr):
    return sorted(arr, key=len, reverse=True)


def process_domains(input_file: str,
                    output_file: str = None,
                    only_available: bool = DEFAULT_ONLY_AVAILABLE,
                    verbose: bool = DEFAULT_VERBOSE,
                    logger: logging.Logger = None) -> List[Dict]:
    """Przetwarza domeny i generuje listę wyników."""
    # Sprawdzenie, czy plik wejściowy istnieje
    if not os.path.exists(input_file):
        if logger:
            logger.error(f"Plik {input_file} nie istnieje.")
        raise FileNotFoundError(f"Plik {input_file} nie istnieje.")

    # Domyślna nazwa pliku wyjściowego
    if output_file is None:
        output_file = os.path.splitext(input_file)[0] + DEFAULT_OUTPUT_SUFFIX

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            domains = [line.strip() for line in f if line.strip()]
    except IOError as e:
        if logger:
            logger.error(f"Błąd odczytu pliku: {e}")
        raise

    results = []

    for domain in domains:
        domain_urls = generate_urls(domain)
        domain_urls = sort_by_length_descending(domain_urls)

        for url in domain_urls:
            is_available = check_url_availability(url, logger=logger)
            # Opcjonalne filtrowanie tylko dostępnych URL
            if not only_available or is_available:
                result = {
                    'domain': domain,
                    'url': url,
                    'available': is_available
                }
                results.append(result)

                # Opcjonalny tryb verbose
                if verbose and logger:
                    logger.info(f"Domena: {domain}, URL: {url}, Dostępna: {is_available}")
                break

    # Zapis do pliku CSV
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['domain', 'url', 'available']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for result in results:
                writer.writerow(result)

        if logger:
            logger.info(f"Zakończono. Wyniki zapisano w {output_file}")

        return results
    except IOError as e:
        if logger:
            logger.error(f"Błąd zapisu pliku: {e}")
        raise


def main():
    # Konfiguracja parsera argumentów
    parser = argparse.ArgumentParser(
        description='Generuje i sprawdza dostępność URL dla listy domen.',
        epilog='Przykład: python url_generator.py domains.txt -o wyniki.csv -a -v'
    )

    # Argumenty jak poprzednio, ale z domyślnymi wartościami z .env
    parser.add_argument('input',
                        type=str,
                        help='Plik wejściowy z listą domen')

    parser.add_argument('-o', '--output',
                        type=str,
                        help='Plik wyjściowy CSV')

    parser.add_argument('-a', '--available',
                        action='store_true',
                        default=DEFAULT_ONLY_AVAILABLE,
                        help='Wyświetl/zapisz tylko dostępne URL')

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        default=DEFAULT_VERBOSE,
                        help='Wyświetl szczegółowe informacje')

    # Dodatkowe opcje dla logowania
    parser.add_argument('--log-level',
                        type=str,
                        default=DEFAULT_LOG_LEVEL,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Poziom logowania')

    parser.add_argument('--log-file',
                        type=str,
                        default=DEFAULT_LOG_FILE,
                        help='Plik dziennika')

    # Parsowanie argumentów
    args = parser.parse_args()

    # Konfiguracja logowania
    logger = setup_logging(
        log_level=args.log_level,
        log_file=args.log_file
    )

    try:
        # Wywołanie głównej funkcji przetwarzania
        process_domains(
            input_file=args.input,
            output_file=args.output,
            only_available=args.available,
            verbose=args.verbose,
            logger=logger
        )
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania skryptu: {e}")
        sys.exit(1)




if __name__ == "__main__":
    main()