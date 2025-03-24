Rozumiem, potrzebujesz skryptu, który można uruchomić w konsoli. Przygotuję dla Ciebie skrypt w Bashu, który wykorzystuje narzędzia konsolowe do sprawdzenia istnienia domen.

Ten skrypt bash sprawdza istnienie domen z pliku portfolio.txt i zapisuje tylko te istniejące do pliku existing_domains.txt.

### Jak używać:

1. Zapisz powyższy skrypt jako np. `existing.sh`
2. Nadaj mu uprawnienia do wykonania: `chmod +x existing.sh`
3. Upewnij się, że masz plik `portfolio.txt` z listą domen w tym samym katalogu
4. Uruchom skrypt: `./existing.sh`

Skrypt używa komendy `host` do sprawdzania istnienia domen. Jest to standardowe narzędzie w większości dystrybucji Linux i macOS. Jeśli komenda `host` nie jest dostępna, możesz zainstalować pakiet `bind-utils` (dla systemów bazujących na Red Hat/Fedora) lub `dnsutils` (dla systemów bazujących na Debian/Ubuntu):

```
# Dla Debian/Ubuntu:
sudo apt install dnsutils

# Dla Red Hat/Fedora:
sudo dnf install bind-utils
```

Jeśli wolisz używać innego narzędzia do sprawdzania domen (np. `dig` lub `nslookup`), mogę zmodyfikować skrypt odpowiednio.