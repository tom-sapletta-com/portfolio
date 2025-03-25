#!/usr/bin/env python3
import argparse
import sys
from ScreenshotCapture import ScreenshotCapture


def main():
    """
    Interfejs wiersza poleceń do przechwytywania zrzutów ekranu.
    """
    parser = argparse.ArgumentParser(description='Narzędzie do przechwytywania zrzutów ekranu stron internetowych')

    # Argumenty
    parser.add_argument('urls', nargs='+', help='Jedna lub więcej stron do zrzutu')
    parser.add_argument('-o', '--output', default='screenshots',
                        help='Katalog do zapisu zrzutów (domyślnie: screenshots)')
    parser.add_argument('-w', '--width', type=int, default=1920,
                        help='Szerokość okna przeglądarki (domyślnie: 1920)')
    parser.add_argument('--height', type=int, default=1080,
                        help='Wysokość okna przeglądarki (domyślnie: 1080)')
    parser.add_argument('--crop-width', type=int, default=4,
                        help='Szerokość proporcji przycięcia (domyślnie: 4)')
    parser.add_argument('--crop-height', type=int, default=1,
                        help='Wysokość proporcji przycięcia (domyślnie: 1)')

    # Parsowanie argumentów
    args = parser.parse_args()

    # Utworzenie instancji ScreenshotCapture
    screenshot_capture = ScreenshotCapture(
        output_dir=args.output,
        width=args.width,
        height=args.height,
        crop_ratio=(args.crop_width, args.crop_height)
    )

    # Przechwytywanie zrzutów ekranu
    results = screenshot_capture.capture_multiple(args.urls)

    # Wyświetlenie wyników
    if results:
        print("Zrzuty ekranu zostały pomyślnie utworzone:")
        for result in results:
            print(f"- {result}")
        return 0
    else:
        print("Nie udało się utworzyć zrzutów ekranu.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())