/**
 * image-preloader.js - Skrypt do wstępnego ładowania miniatur
 * Ten skrypt pomaga w zarządzaniu obrazami w portfolio, obsługuje błędy ładowania
 * i zapewnia płynne przejścia między obrazem, iframe i fallbackiem SVG.
 */

// Funkcja uruchamiana po załadowaniu strony
document.addEventListener('DOMContentLoaded', function() {
    // Funkcja sprawdzająca, czy URL istnieje i jest dostępny
    function checkImageExists(url, callback) {
        const img = new Image();
        img.onload = function() { callback(true); };
        img.onerror = function() { callback(false); };
        img.src = url;
    }

    // Funkcja próbująca załadować iframe, gdy obrazek nie jest dostępny
    function tryLoadingIframe(imgElement, iframeUrl, fallbackSvg) {
        // Utwórz iframe
        const iframe = document.createElement('iframe');
        iframe.src = iframeUrl;
        iframe.className = 'thumbnail-iframe';
        iframe.setAttribute('sandbox', 'allow-same-origin allow-scripts');
        iframe.setAttribute('loading', 'lazy');

        // Dodaj klasę do kontenera obrazu
        const container = imgElement.parentNode;
        container.classList.add('iframe-active');

        // Ukryj obraz i wstaw iframe przed nim
        imgElement.style.display = 'none';
        container.insertBefore(iframe, imgElement);

        // Obsługa awarii ładowania iframe (po timeout)
        setTimeout(function() {
            try {
                if (iframe.contentDocument &&
                    (!iframe.contentDocument.body ||
                     iframe.contentDocument.body.innerHTML === '')) {
                    useImageFallback(iframe, imgElement, fallbackSvg);
                }
            } catch (e) {
                // Error może wystąpić przy różnych domenach (CORS)
                // W tym przypadku również używamy fallbacku
                console.log('Iframe nie mógł być załadowany z powodu CORS lub innego błędu:', e);
                useImageFallback(iframe, imgElement, fallbackSvg);
            }
        }, 4000);

        // Dodatkowy event listener dla iframe
        iframe.onerror = function() {
            useImageFallback(iframe, imgElement, fallbackSvg);
        };
    }

    // Funkcja pokazująca obraz fallbackowy SVG, gdy iframe zawiedzie
    function useImageFallback(iframe, imgElement, fallbackSvg) {
        iframe.remove();
        imgElement.style.display = 'block';
        imgElement.src = fallbackSvg;
        imgElement.parentNode.classList.remove('iframe-active');
    }

    // Przeskanuj wszystkie elementy z klasą "portfolio-item" i wstępnie załaduj obrazy
    const portfolioItems = document.querySelectorAll('.portfolio-item');

    portfolioItems.forEach(function(item) {
        const img = item.querySelector('.thumbnail');
        const domain = item.getAttribute('data-domain');
        const url = img.parentNode.nextElementSibling.querySelector('a').getAttribute('href');

        // Pobierz inicjały i kolor dla SVG fallback
        const initials = domain.split('.')[0].substring(0, 2).toUpperCase();
        let color = '';

        // Generowanie koloru na podstawie domeny (prosty hash)
        let hash = 0;
        for (let i = 0; i < domain.length; i++) {
            hash = domain.charCodeAt(i) + ((hash << 5) - hash);
        }
        color = Math.abs(hash).toString(16).substring(0, 6);

        // Przygotuj fallback SVG
        const fallbackSvg = `data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='200' viewBox='0 0 300 200'><rect fill='%23${color}' width='300' height='200'></rect><text fill='%23fff' font-family='Arial' font-size='30' font-weight='bold' text-anchor='middle' x='150' y='110'>${initials}</text></svg>`;

        // Sprawdź, czy obraz istnieje
        checkImageExists(img.src, function(exists) {
            if (!exists && !img.hasAttribute('data-tried-iframe')) {
                img.setAttribute('data-tried-iframe', 'true');
                tryLoadingIframe(img, url, fallbackSvg);
            }
        });
    });

    console.log('Image preloader został uruchomiony dla', portfolioItems.length, 'elementów portfolio.');
});