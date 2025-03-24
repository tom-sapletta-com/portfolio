#!/bin/bash

# Nazwy plików
INPUT_FILE="portfolio.txt"
OUTPUT_FILE="existing.txt"

# Sprawdź czy plik wejściowy istnieje
if [ ! -f "$INPUT_FILE" ]; then
    echo "Błąd: Plik $INPUT_FILE nie istnieje."
    exit 1
fi

# Przygotuj pusty plik wynikowy
> "$OUTPUT_FILE"

# Policz liczbę domen
TOTAL_DOMAINS=$(grep -c "." "$INPUT_FILE")
echo "Sprawdzanie $TOTAL_DOMAINS domen..."

# Licznik dla postępu
COUNTER=0

# Sprawdź każdą domenę
while read -r DOMAIN || [ -n "$DOMAIN" ]; do
    # Pomiń puste linie
    if [ -z "$DOMAIN" ]; then
        continue
    fi

    # Zwiększ licznik
    ((COUNTER++))

    # Sprawdź czy domena istnieje używając komendy 'host'
    if host "$DOMAIN" > /dev/null 2>&1; then
        echo "[$COUNTER/$TOTAL_DOMAINS] $DOMAIN - istnieje"
        # Dodaj domenę do pliku wynikowego
        echo "$DOMAIN" >> "$OUTPUT_FILE"
    else
        echo "[$COUNTER/$TOTAL_DOMAINS] $DOMAIN - nie istnieje"
    fi
done < "$INPUT_FILE"

# Policz istniejące domeny
EXISTING_COUNT=$(grep -c "." "$OUTPUT_FILE")

echo ""
echo "Sprawdzanie zakończone!"
echo "Znaleziono $EXISTING_COUNT istniejących domen z $TOTAL_DOMAINS."
echo "Istniejące domeny zostały zapisane w pliku: $OUTPUT_FILE"