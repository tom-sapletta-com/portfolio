import os
import logging
from urllib.parse import urlparse
from typing import Optional, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import time

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class ScreenshotCapture:
    """
    Klasa do przechwytywania zrzutów ekranu stron internetowych.
    """

    def __init__(
            self,
            output_dir: str = 'screenshots',
            width: int = 1200,
            height: int = 1600,
            #crop_ratio: Tuple[int, int] = (4, 1)
            crop_ratio: Tuple[int, int] = (1, 1)
    ):
        """
        Inicjalizacja obiektu ScreenshotCapture.

        Args:
            output_dir (str): Katalog do zapisu zrzutów
            width (int): Szerokość okna przeglądarki
            height (int): Wysokość okna przeglądarki
            crop_ratio (tuple): Proporcje przycięcia zrzutu (szerokość, wysokość)
        """
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.crop_ratio = crop_ratio

        # Utworzenie katalogu na zrzuty, jeśli nie istnieje
        os.makedirs(output_dir, exist_ok=True)

    def _normalize_url(self, url: str) -> str:
        """
        Normalizacja adresu URL.

        Args:
            url (str): Adres URL do normalizacji

        Returns:
            str: Znormalizowany adres URL
        """
        if not url.startswith(('http://', 'https://')):
            return f'https://{url}'
        return url

    def _generate_filename(self, url: str) -> str:
        """
        Generowanie nazwy pliku na podstawie URL.

        Args:
            url (str): Adres URL

        Returns:
            str: Znormalizowana nazwa pliku
        """
        parsed_url = urlparse(url)
        return f"{parsed_url.netloc.replace('.', '_').replace(':', '_')}.png"

    def capture(self, url: str) -> Optional[str]:
        """
        Zrobienie zrzutu ekranu strony internetowej z dłuższym czasem oczekiwania na załadowanie JavaScript.

        Args:
            url (str): Adres URL strony do zrzutu

        Returns:
            Optional[str]: Ścieżka do zapisanego zrzutu ekranu lub None
        """
        # Normalizacja URL
        normalized_url = self._normalize_url(url)

        # Generowanie nazwy pliku
        filename = self._generate_filename(normalized_url)
        output_path = os.path.join(self.output_dir, filename)

        # Konfiguracja opcji Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Tryb bezokienkowy
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'--window-size={self.width},{self.height}')

        driver = None
        try:
            # Inicjalizacja sterownika Chrome
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            # Nawigacja do strony
            driver.get(normalized_url)

            # Oczekiwanie na załadowanie strony i JavaScript (maks. 10 sekund)
            wait = WebDriverWait(driver, 10)
            try:
                # Poczekaj na załadowanie dokumentu
                wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')

                # Opcjonalnie: dodatkowe oczekiwanie na konkretne elementy, jeśli potrzeba
                # Przykład: wait.until(EC.presence_of_element_located((By.ID, 'main-content')))
            except TimeoutException:
                logging.warning(f"Przekroczono limit czasu ładowania strony: {normalized_url}")

            # Krótkie dodatkowe oczekiwanie na dociążenie dynamicznej zawartości
            time.sleep(2)

            # Zrobienie zrzutu ekranu
            driver.save_screenshot(output_path)

            # Przetworzenie zrzutu
            with Image.open(output_path) as img:
                # Przycięcie do zadanych proporcji
                width, height = img.size
                crop_height = int(width / self.crop_ratio[0] * self.crop_ratio[1])
                cropped_img = img.crop((0, 0, width, min(crop_height, height)))

                # Zmiana rozmiaru
                resize_width = 800
                resize_height = int(resize_width / self.crop_ratio[0] * self.crop_ratio[1])
                cropped_img = cropped_img.resize((resize_width, resize_height), Image.LANCZOS)
                cropped_img.save(output_path)

            logging.info(f"Zrzut ekranu zapisany: {output_path}")
            return output_path

        except Exception as e:
            logging.error(f"Błąd podczas robienia zrzutu ekranu: {e}")
            return None

        finally:
            # Zamknięcie przeglądarki
            if driver:
                driver.quit()

    def capture_multiple(self, urls: list) -> list:
        """
        Zrobienie zrzutów ekranu dla wielu stron.

        Args:
            urls (list): Lista adresów URL

        Returns:
            list: Lista ścieżek do zrzutów ekranu
        """
        results = []
        for url in urls:
            result = self.capture(url)
            if result:
                results.append(result)
        return results

    def multicapture(
            self,
            urls: list,
            max_workers: int = None,
            timeout: int = 180
    ) -> list:
        """
        Zrobienie zrzutów ekranu dla wielu stron równolegle.

        Args:
            urls (list): Lista adresów URL do zrzutu
            max_workers (int, optional): Maksymalna liczba równoczesnych procesów.
                Domyślnie None (automatyczne ustalenie liczby procesów).
            timeout (int, optional): Maksymalny czas trwania operacji w sekundach.
                Domyślnie 180 sekund (3 minuty).

        Returns:
            list: Lista ścieżek do zrzutów ekranu
        """
        # Import bibliotek do przetwarzania równoległego
        from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

        # Lista do przechowywania wyników
        results = []

        # Użycie ThreadPoolExecutor do równoległego przetwarzania zrzutów
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Mapowanie zadań - każdy URL dostaje własne zadanie capture
            future_to_url = {
                executor.submit(self.capture, url): url
                for url in urls
            }

            try:
                # Iteracja po zakończonych zadaniach
                for future in as_completed(future_to_url, timeout=timeout):
                    url = future_to_url[future]
                    try:
                        # Próba pobrania wyniku
                        result = future.result()
                        if result:
                            results.append(result)
                    except Exception as exc:
                        # Logowanie błędów dla poszczególnych URL
                        logging.error(f'Błąd podczas przechwytywania {url}: {exc}')

            except TimeoutError:
                # Obsługa przekroczenia czasu
                logging.warning(f'Przekroczono maksymalny czas wykonania {timeout} sekund')

                # Anulowanie pozostałych zadań
                for future in future_to_url:
                    future.cancel()

        return results

    def capture_multiple(self, urls: list) -> list:
        """
        Zrobienie zrzutów ekranu dla wielu stron (stara metoda).

        Args:
            urls (list): Lista adresów URL

        Returns:
            list: Lista ścieżek do zrzutów ekranu
        """
        results = []
        for url in urls:
            result = self.capture(url)
            if result:
                results.append(result)
        return results
