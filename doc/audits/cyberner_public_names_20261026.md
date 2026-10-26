# Cyberner — nick gracza zamiast identyfikatora OAuth

Przyczyna: renderer używał sender zarówno do identyfikacji, jak i etykiety.
Konta OAuth mają techniczny username id_..., natomiast nick jest dostępny
w istniejącej projekcji tożsamości jako display_alias/nick.

Dodano osobne sender_display_name oraz display_name kontaktu/wątku.
Historia, odpowiedź wysłania i zdarzenia live pobierają nick z projekcji.
Nagłówki prywatnych rozmów i nowe powiadomienia korzystają z tego samego
źródła. Sender, peer, name, deduplikacja, własność wiadomości i cele blokad
zachowują identyfikatory. Nie zmieniono OAuth ani danych kont.
Odczyt etykiet jest zbiorczy, po 100 kont, bez parsowania profili JSON.
Brak poprawnej projekcji zachowuje dotychczasową nazwę; systemowi autorzy
pozostają systemowymi autorami. Historia uzyska aktualny nick przy odczycie.

Walidacja lokalna: test_cyberner*.py 40 PASS (22.158s), identity_projection
4 PASS (2.662s), node --check terminal.js i git diff --check PASS.
Playwright MCP: izolowany rzeczywisty renderer wiadomości, nick zamiast ID,
własna wiadomość nadal is-own, HTML nicku wyświetlany jako tekst (0 img),
przycisk ustawień kontaktu przekazuje id_other, 0 błędów konsoli. Przeglądarka
i fixture zatrzymane. Nie wykonywano prawdziwego logowania Google ani testu VPS.

Wdrożenie bez migracji: pull, test_cyberner*.py, reload ecosystem.web.config.js
--only chaos --env routing --update-env. Zachować aktywny profil routing;
nie restartować kolektora świata. Po HTTP 200 odświeżyć klienta, aby załadował
nowy JS. Odbiór użytkownika: nick w historii i nowej wiadomości, rozmowa
prywatna nadal trafia do tego samego konta.

## Odbiór VPS — poprawka izolacji testów

2254674 pobrany na VPS, ale 12 testów routingu otrzymało 423
ghostsystem_restart_required/document_epoch_replaced. Sekwencja &&
zatrzymała się przed reloadem i pm2 save. Fixture podmieniał bazy Cybernera,
lecz pomijał ghostsignal_show_db_path, przez co bramka widziała epokę
produkcyjnego świata. Poprawiono tylko fixture: osobny GhostNetworkRepository
w bazie testowej i podmiana ścieżki. Dodano sprawdzenie prawdziwej bramki
(423 bez epoki, 200 z nagłówkiem zgodnym z testową epoką). Nie wyłączono
ochrony restartu w aplikacji ani nie zmieniono świata produkcyjnego.
