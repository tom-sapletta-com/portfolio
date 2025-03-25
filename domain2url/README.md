Zmodyfikuję skrypt, dodając:
1. Logowanie do pliku
2. Zmienne domyślne na początku
3. Obsługę pliku `.env`

Teraz główny skrypt:

### Instrukcja użycia:

1. Zainstaluj wymagane biblioteki:
```bash
pip install -r requirements.txt
```

2. Utwórz plik `.env` (opcjonalnie, używa wartości domyślnych):
```
# Przykładowa zawartość pliku .env
REQUEST_TIMEOUT=7
LOG_LEVEL=DEBUG
LOG_FILE=moj_generator.log
ONLY_AVAILABLE=true
```

### Przykłady użycia:

1. Podstawowe użycie:
```bash
python domain2url/cli.py domains.txt
```

```bash
python domain2url/cli.py portfolio.txt -o portfolio_http.txt
```

2. Z niestandardowym plikiem wyjściowym:
```bash
python domain2url/cli.py domains.txt -o moje_url.csv
```

3. Tylko dostępne URL:
```bash
python domain2url/cli.py domains.txt -a
```

4. Tryb verbose:
```bash
python domain2url/cli.py domains.txt -v
```

5. Zaawansowana konfiguracja logowania:
```bash
python domain2url/cli.py domains.txt --log-level DEBUG --log-file moj_log.log
```

### Główne cechy:
- Konfiguracja przez zmienne środowiskowe
- Zaawansowane logowanie 
- Obsługa błędów
- Elastyczne opcje generowania URL
- Możliwość filtrowania dostępnych URL
- Tryb verbose

### Uwagi:
- Domyślnie sprawdza URL z `http://` i `https://`
- Opcjonalnie dodaje warianty z `www.`
- Konfigurowalny timeout requestów
- Własny user agent

