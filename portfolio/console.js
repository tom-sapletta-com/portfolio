/* Wersja CSS + JS do wklejenia bezpośrednio w konsolę */

// Najpierw style CSS
const style = document.createElement('style');
style.textContent = `
.insecure-link {
    color: #ff0000 !important;
    font-weight: bold !important;
    text-decoration: wavy underline #ff0000 !important;
    position: relative;
}

.insecure-link::after {
    content: "⚠️";
    margin-left: 3px;
    font-size: 0.8em;
}

.insecure-tooltip {
    position: absolute;
    background-color: #fff0f0;
    border: 1px solid #ff0000;
    border-radius: 4px;
    padding: 8px;
    font-size: 12px;
    color: #d00;
    font-weight: normal;
    z-index: 9999;
    bottom: 100%;
    left: 0;
    margin-bottom: 5px;
    min-width: 150px;
    max-width: 250px;
    display: none;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}

.insecure-link:hover .insecure-tooltip {
    display: block;
}

#https-status-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: #333;
    color: white;
    padding: 8px 16px;
    font-size: 14px;
    z-index: 10000;
    display: flex;
    justify-content: space-between;
}

.status-secure {
    color: #4caf50;
}

.status-insecure {
    color: #ff5252;
}

.close-button {
    background: none;
    border: none;
    color: white;
    cursor: pointer;
    font-size: 16px;
}
`;
document.head.appendChild(style);

// Funkcja sprawdzająca linki
function checkHttpsLinks() {
    // Liczniki do statystyk
    let totalLinks = 0;
    let insecureLinks = 0;

    // Pobierz wszystkie linki na stronie
    const links = document.querySelectorAll('a[href]');

    links.forEach(link => {
        const href = link.getAttribute('href');

        // Ignoruj wewnętrzne linki, maile, telefony itp.
        if (!href || href.startsWith('#') || href.startsWith('javascript:') ||
            href.startsWith('mailto:') || href.startsWith('tel:')) {
            return;
        }

        totalLinks++;

        try {
            // Spróbuj przekształcić href w obiekt URL
            const url = new URL(href, window.location.href);

            // Sprawdź protokół
            if (url.protocol === 'http:') {
                markAsInsecure(link, "Nieszyfrowane połączenie HTTP");
                insecureLinks++;
            }
            // Sprawdź inne potencjalnie niebezpieczne protokoły
            else if (url.protocol !== 'https:' && !url.protocol.startsWith('data:') &&
                    url.protocol !== 'file:' && url.protocol !== 'ftp:') {
                markAsInsecure(link, `Niestandadrowy protokół: ${url.protocol}`);
                insecureLinks++;
            }
        } catch (e) {
            // Jeśli URL jest niepoprawny, również oznacz
            if (href.startsWith('http:')) {
                markAsInsecure(link, "Nieszyfrowane połączenie HTTP");
                insecureLinks++;
            }
        }
    });

    // Dodaj pasek statusu na dole strony
    addStatusBar(totalLinks, insecureLinks);
}

// Funkcja oznaczająca niebezpieczny link
function markAsInsecure(link, reason) {
    // Dodaj klasę do stylowania
    link.classList.add('insecure-link');

    // Dodaj tooltip z wyjaśnieniem
    const tooltip = document.createElement('span');
    tooltip.className = 'insecure-tooltip';
    tooltip.textContent = reason;
    link.appendChild(tooltip);
}

// Funkcja dodająca pasek statusu
function addStatusBar(total, insecure) {
    // Usuń istniejący pasek statusu, jeśli istnieje
    const existingBar = document.getElementById('https-status-bar');
    if (existingBar) {
        existingBar.remove();
    }

    // Utwórz nowy pasek statusu
    const statusBar = document.createElement('div');
    statusBar.id = 'https-status-bar';

    // Treść paska statusu
    const secureLinks = total - insecure;
    const securePercent = total > 0 ? Math.round((secureLinks / total) * 100) : 0;

    statusBar.innerHTML = `
        <div>
            Sprawdzono <strong>${total}</strong> linków:
            <span class="status-secure">${secureLinks} bezpiecznych (${securePercent}%)</span>,
            <span class="status-insecure">${insecure} niebezpiecznych (${100 - securePercent}%)</span>
        </div>
        <button class="close-button" onclick="this.parentNode.remove()">×</button>
    `;

    // Dodaj pasek do dokumentu
    document.body.appendChild(statusBar);
}

// Uruchom sprawdzanie
checkHttpsLinks();

console.log("✅ Skrypt sprawdzający HTTPS został uruchomiony. Niebezpieczne linki zostały zaznaczone na czerwono.");