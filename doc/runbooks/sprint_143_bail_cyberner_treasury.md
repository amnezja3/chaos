# 143 — kaucja w Cybernerze i skarbiec HC

Zmiana autora: status aresztu zastępuje CEL na dolnej belce. Pokazuje nazwę
zapisanego więzienia, ikonę krat, czerwone pulsujące kropki i pozostały czas
online wraz z paskiem. Po zwolnieniu wraca zwykły cel. Usunięty techniczny
przycisk w prawym górnym rogu.

Wiadomość wysłana podczas aresztu otrzymuje adnotację cenzury prokuratorskiej
i przycisk kaucji. Adnotacja nie zmienia treści prośby napisanej przez gracza.
Dotyczy World (jeśli stopień pozwala pisać), klanu, znajomych i DM. Wspólny
limit jednej wiadomości poza World pozostaje. Odbiorca i nadawca widzą CTA.
Metadane pochodzą wyłącznie z backendu i są zapisane z wiadomością, także
w kopiach odbiorców. Nie podajemy współrzędnych więzienia ani miejsca powrotu.

Kliknięcie pobiera aktualną kwotę dla nadawcy, sprawdza identyfikator wyroku
i otwiera potwierdzenie CHAOS. Dopiero akceptacja wysyła płatność. Stara
wiadomość nie może opłacić następnego wyroku tej samej osoby. Backend
ponownie weryfikuje stan w transakcji; równoległe wpłaty nie dublują opłaty.

Kaucje, mandaty i starsza konfiskata HC trafiają do `admin`. Obciążenie,
uznanie, historia portfela i zwolnienie są atomowe. Konto admin musi mieć
istniejący kanoniczny portfel; błąd odbiorcy cofa całą operację. Wpłata przez
admina do własnego skarbca jest netto zerowa, przy zachowaniu weryfikacji
środków do opłacenia kaucji. Admin nie kwalifikuje się do spotkań z patrolami.
Jawne transfery gracz–gracz zachowują odbiorcę. Zakupy systemowe już używają
admina jako odbiorcy domyślnego. Nowe opłaty systemowe muszą mieć jawny
wpływ na admina, bez debit-only/sink. Nagrody za grę nie są przekierowywane.

## Wdrożenie

### Własna kaucja przy odmowie akcji

Próba akcji zablokowanej przez areszt (ruch, teleport lub aplikacja/akcja
niedostępna na danym stopniu) otwiera okno CHAOS. Bieżący kanoniczny portfel
jest odczytywany przez backend dla zalogowanego gracza. Przycisk
`ZAPŁAĆ <kwota> HC` pojawia się tylko przy saldzie co najmniej równym kaucji.
Bez środków gracz widzi kwotę i informację o jednej prywatnej wiadomości
w Cybernerze; po jej wysłaniu informacja mówi o wykorzystanym limicie.
Potwierdzenie płatności dotyczy zapisanego ID wyroku. Samo wyświetlenie okna
niczego nie pobiera, a endpoint płatności ponownie sprawdza stan i saldo.
Kilka równoczesnych odmów otwiera jedno okno. Odpytywanie w tle nie pokazuje
okien kaucji. CTA w wiadomościach dla innych graczy pozostaje dostępne.
Tabela ograniczeń poszczególnych stopni nie została rozszerzona tą zmianą.

Walidacja tej zmiany: trzy testy Python (własne saldo/oferta, autorytatywny
płatnik, rollback/brak środków) i trzy testy JS (własna kaucja, kaucja
z wiadomości, most sesji/mapy). Test salda sprawdza próg 249 999 / 250 000 HC.

Po pobraniu zmian uruchomić z katalogu aplikacji:

```sh
pm2 startOrRestart ecosystem.web.config.js --update-env
pm2 startOrRestart ecosystem.territory-worker.config.js --update-env
```

Odświeżyć desktop. Inicjalizacja DB dodaje nullable `chat_messages.delivery_id`;
stare wiadomości pozostają czytelne. Adnotacje są tworzone dla nowych wysłań.

## Korekta wcześniejszych 500 000 HC

Najpierw podgląd tylko do odczytu (nie zmienia sald):

```sh
.venv/bin/python tools/reconcile_bail_treasury.py --sanction-id sanction_18b662e5ec536e55142d784e89b2f72e
```

Oczekiwane: `payer: admin`, `recipient: admin`, `amount_hc: 500000`,
`status: would_credit`. Narzędzie wymaga zgodności pokwitowania wyroku
z rzeczywistym kanonicznym obciążeniem. Po sprawdzeniu wyniku:

```sh
.venv/bin/python tools/reconcile_bail_treasury.py --sanction-id sanction_18b662e5ec536e55142d784e89b2f72e --apply
```

Ponowne uruchomienie zwraca `already_credited`; nie dopisuje drugi raz HC.
Nie przywraca kartoteki ani nie reaktywuje wyroku. Korekta nie została
wykonana na serwerze przez agenta.

## Odbiór w grze

Walidacja lokalna: **77 testów Python i 4 testy JS PASS**. Obejmuje atomowość,
konkurencyjne wpłaty, odtworzenie starego debit-only i jednokrotną korektę,
metadane wiadomości po odczycie historii, ochronę przed ich podszyciem,
migracje/routing Cybernera, anulowanie potwierdzenia i stare identyfikatory
wyroków. Składnia obu zmienionych plików JS i `git diff --check` poprawne.
Wygląd belki i karty kaucji wymaga odbioru na desktopie i telefonie po wdrożeniu.

1. Gracz w areszcie widzi więzienie i timer zamiast CEL; wylogowanie zamraża czas.
2. Wysyła jedną wiadomość prywatną. Odbiorca widzi cenzurę i kwotę również po reloadzie.
3. Anulowanie potwierdzenia nie zmienia salda. Akceptacja obciąża płatnika,
   uznaje admina i zwalnia więźnia. Najpierw można użyć admina z odzyskanym
   saldem — jego wpłata do skarbca nie uszczupli netto środków.
4. Ponowne kliknięcie starej wiadomości nie pobiera HC, także podczas kolejnego wyroku.
5. Po zwolnieniu wracają CEL, zwykłe uprawnienia i pozycja sprzed aresztu.
