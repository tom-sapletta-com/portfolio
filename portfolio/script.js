// ==UserScript==
// @name         HTTPS Security Checker
// @description  Sprawdza wszystkie linki na stronie i podświetla te, które nie używają HTTPS
// @version      1.0
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Dodanie stylów CSS dla podświetlania linków
    const style = document.createElement('style');
    style.textContent = `
        .https-insecure {
            color: #ff0000 !important;
            font-weight: bold !important;
            position: relative;
        }

        .https-insecure::after {
            content: "⚠️";
            margin-left: 5px;
            font-size: 0.9em;
        }

        .https-tooltip {
            position: absolute;
            background-color: #fff8f8;
            border: 1px solid #ff0000;
            border-radius: 4px;
            padding: 5px 10px;
            color: #ff0000;
            font-size: 12px;
            z-index: 1000;
            max-width: 250px;
            display: none;
            bottom: 100%;
            left: 0;
            margin-bottom: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
        }

        .https-insecure:hover .https-tooltip {
            display: block;
        }
    `;
    document.head.appendChild(style);

    // Funkcja sprawdzająca, czy link używa HTTPS
    function checkHttpsProtocol() {
        const links = document.querySelectorAll('a[href]');

        links.forEach(link => {
            const href = link.getAttribute('href');

            // Ignoruj linki do zasobów lokalnych, kotwice, tel:, mailto:, etc.
            if (href.startsWith('#') ||
                href.startsWith('tel:') ||
                href.startsWith('mailto:') ||
                href.startsWith('javascript:') ||
                href === '/') {
                return;
            }

            try {
                const url = new URL(href, window.location.href);

                // Sprawdź, czy protokół to HTTP (nie HTTPS)
                if (url.protocol === 'http:') {
                    markLinkAsInsecure(link, "Nieszyfrowane połączenie HTTP");
                }

                // Dodatkowe sprawdzenie dla innych protokołów, które mogą być niebezpieczne
                if (url.protocol !== 'https:' &&
                    url.protocol !== 'http:' &&
                    url.protocol !== 'ftp:' &&
                    !url.protocol.startsWith('data:')) {
                    markLinkAsInsecure(link, `Nieznany protokół: ${url.protocol}`);
                }

                // Opcjonalnie: faktyczne sprawdzenie certyfikatu poprzez fetch API
                // (tylko dla domen należących do tej samej origin lub z CORS)
                if (url.protocol === 'https:' &&
                    (url.hostname === window.location.hostname || confirm(`Czy chcesz sprawdzić certyfikat domeny ${url.hostname}?`))) {
                    checkCertificate(url.href, link);
                }

            } catch (e) {
                // Jeśli URL jest nieprawidłowy, oznacz link jako problematyczny
                markLinkAsInsecure(link, `Nieprawidłowy URL: ${e.message}`);
            }
        });
    }

    // Funkcja oznaczająca link jako niebezpieczny
    function markLinkAsInsecure(link, reason) {
        link.classList.add('https-insecure');

        // Dodaj tooltip z wyjaśnieniem
        const tooltip = document.createElement('span');
        tooltip.className = 'https-tooltip';
        tooltip.textContent = reason;
        link.appendChild(tooltip);
    }

    // Funkcja sprawdzająca certyfikat SSL poprzez fetch API
    function checkCertificate(url, link) {
        fetch(url, { method: 'HEAD', mode: 'no-cors' })
            .catch(error => {
                // Jeśli wystąpił błąd SSL, oznacz link
                if (error.message.includes('SSL') || error.message.includes('certificate')) {
                    markLinkAsInsecure(link, `Problem z certyfikatem SSL: ${error.message}`);
                }
            });
    }

    // Uruchom sprawdzenie po załadowaniu strony
    window.addEventListener('load', checkHttpsProtocol);

    // Dodaj przycisk do ręcznego uruchomienia sprawdzenia (opcjonalnie)
    const button = document.createElement('button');
    button.textContent = 'Sprawdź bezpieczeństwo linków';
    button.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 9999; padding: 10px; background: #f8f8f8; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;';
    button.addEventListener('click', checkHttpsProtocol);
    document.body.appendChild(button);

})();