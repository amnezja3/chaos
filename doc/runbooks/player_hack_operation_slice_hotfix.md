# PvP: 409 przy wielu aktywnych operacjach — 20 IX 2026

Zgłoszenie: gracz widoczny i możliwy do oznaczenia po otoczeniu polem,
ale narzędzia zwracają `profile_recovery_required`; autor potwierdził także
problem przy wtargnięciu. Log przeglądarki wskazuje `/gonna-win`.

Odtworzono lokalnie identyczne HTTP 409: 40 aktywnych operacji na innych
celach wystarczało do zablokowania zakończenia włamania do gracza.
W `/hack-action` i `/gonna-win` odczyt limitowany do 32 operacji był błędnie
traktowany jako limit gameplay i powód naprawy profilu (`len >= 32`).
Nie był to warunek geometrii otoczenia; dotyczył obu ścieżek PvP.
Bez logów backendu nie rozstrzygamy innych możliwych przyczyn tego samego
ogólnego komunikatu na konkretnym koncie produkcyjnym.

Naprawa: odczyt do 32 operacji wybranego celu, filtrowany przez istniejący
indeks `(username,target_key)`. Usunięta fałszywa blokada recovery. Odczyt
pozostaje ograniczony; operacje spoza wycinka nadal obejmuje kanoniczna
deduplikacja przy upsert. Nie podnosimy limitu ani nie wczytujemy profili.
Reguły widoczności, relacji graczy, zasięgu i cooldownu pozostają bez zmian.

Regresje: 40 operacji terytorialnych przy kończeniu włamania; 80 operacji
(40 tego samego gracza, 40 innych celów) przy uruchamianiu z mapy i terminala,
ponowne uruchomienie nie tworzy drugiego port_scan.

Walidacja lokalna: 24 testy PASS w izolowanym runnerze
(`test_player_hack_completion`, `test_player_launcher_hot_path`,
`test_player_target_selection`). Przed poprawką nowy test z 40 operacjami
zwracał dokładnie 409/profile_recovery_required; po poprawce przechodzi.

Po deployu zrestartować web przez ecosystem.web.config.js. Zamknąć stare
okna narzędzi, odświeżyć klienta i uruchomić nowe próby (nowe launch receipts).
Sprawdzić wtargnięcie oraz otoczenie: oznaczenie → skaner/sniffer → exploit
→ dostęp PvP, również przy ponad 32 aktywnych operacjach. Powtórzenie skanu
nie powinno tworzyć drugiej aktywnej operacji tego samego narzędzia i celu.
Gameplay PASS pozostaje do potwierdzenia po wdrożeniu.
