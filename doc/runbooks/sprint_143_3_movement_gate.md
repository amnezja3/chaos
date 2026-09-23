# 143.3 — blokada ruchu i teleportów

Uzupełnienie 143.4: wewnętrzny `DetentionService._move` jest dodatkowym,
autoryzowanym writerem pozycji dla osadzenia i zwolnienia. Wymaga transakcji
wyroku i zapisanej docelowej pozycji. Szczegóły w
[runbooku 143.4](sprint_143_4_detention_transport.md); poniższy audyt opisuje
stan bramek przed dodaniem tego transportu.

22 IX 2026: implementacja bramek dla trwałych sankcji z 143.2. Nie aktywuje
nakładania aresztów. Podłączenie nałożenia/transportu/zwolnienia pozostaje
w 143.4; brak wyroków oznacza dotychczasowy ruch bez ograniczeń.

## Wspólna bramka i inwentaryzacja

`response_network/movement_guard.py` odmawia dla `active` i `release_pending`.
Nie zwalnia na podstawie zegara klienta ani samego zera remaining_ms:
konieczne jest zakończenie transportu powrotnego. Odczyt po indeksie aktora,
bez ładowania profilu. Przed migracją tabeli sankcji brak tabeli oznacza brak
wyroków; inne błędy SQLite są propagowane.

| Droga | Miejsce egzekwowania |
|---|---|
| Jazda i zatwierdzenie trasy `/map-action` | Preflight przed hydracją profilu oraz `PlayerPositionStore.upsert` |
| Teleport BlackNet, terminal i GhostNetwork `/api/blacknet/cta/teleport` | Wspólny `upsert` |
| Bilet Googleplex `/install-app` | Preflight przed zakupem oraz bramka w transakcji płatności i pozycji |
| Wymuszone przeniesienie Intruder Kicker | Bramka pozycji ofiary w tej samej transakcji co receipt i delty |
| Legacy `curently_possition` / `current_position` | `UserStore.save_profile_guarded`, po uzyskaniu blokady zapisu |
| Seed z profilu / migracja canonical pozycji | `PlayerPositionStore.upsert` |
| Rejestracja | Nowe konto bez wyroku; późniejszy seed przez wspólny store |

Audyt wywołań i SQL aplikacji nie wykazał innych runtime writerów tabeli
`player_positions`. Zmiana pozycji operacji/śledzonego celu nie jest zmianą
pozycji gracza. Administracyjne kasowanie/reset i narzędzia offline nie są
alternatywną drogą gameplay.

`upsert` wymaga transakcji dla przekazanego conn; własne połączenie rozpoczyna
`BEGIN IMMEDIATE`. Nałożenie sankcji i ruch serializują się na SQLite writerze.
Parametr `source`, w tym `admin`/`prison_transport`, nigdy nie omija bramki.
Wewnętrzny transport więzienny trzeba zrealizować w 143.4 jako osobną,
uprawnioną operację serwera powiązaną z sankcją, nie flagę żądania klienta.

Legacy może synchronizować pola do canonical pozycji, ale nie przesunąć
aresztowanego ani wyzerować jego położenia. Odmowa zapisu nie trafia już
w fallback `normalize_profile_position_update` zwracający niezatwierdzoną pozycję.
Niepowiązane zapisy profilu nie są blokowane samym istnieniem wyroku.

## Płatność i komunikat

`response_network/travel_purchase.py` wykorzystuje callback transakcji
`WalletBalanceStore.transfer`: płatność i `upsert` pozycji razem commit/rollback.
Wyrok utworzony po preflight nadal uniemożliwia przejazd bez trwałego obciążenia
HC. Powtórka opłaconego biletu nie przenosi drugi raz. Darmowy przejazd ma
osobny trwały receipt z kluczem zakupu. Dotychczasowy zapis szczegółów zakupu
w profilu pozostaje osobnym etapem z retry; nie jest atomową częścią przejazdu.

Odpowiedź 409 `detention_movement_blocked` podaje komunikat, pozostałe sekundy
online i canonical pozycję zalogowanego gracza (nigdy współrzędne ofiary).
Mapa przerywa kolejkę i starą animację, usuwa oczekujące commity/pulsy trasy,
wraca do pozycji serwera i pokazuje powód. Bezpośrednie API podlega tej samej
bramce. Przywracanie stanu po samym nałożeniu wyroku wymaga delt transportu 143.4.

## Walidacja

Testy obejmują wszystkie wartości źródła, `release_pending`, ruch po zwolnieniu,
odmowę biletu bez utraty HC, rollback płatności przy błędzie writera, replay
bez ponownego ruchu, legacy profil bez zmiany rewizji po odmowie oraz HTTP
jazdy/teleportu/biletu/Intruder Kickera. Test JS sprawdza przerwanie działającej
animacji i zachowanie autorytatywnej pozycji. Odbiór gry z rzeczywistym aresztem
wymaga podłączenia 143.4; nie oznaczać obecnego etapu jako produkcyjnego PASS.
