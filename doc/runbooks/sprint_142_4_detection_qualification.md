# 142.4 — kwalifikacja spotkania ze służbami

Implementacja lokalna gotowa do odbioru. Bez PASS gameplayu i bez deployu
wykonanego przez agenta. Zmiany 142.3/refresh obecne w workspace zachowane.

## Tryb i dane

We wszystkich czterech ecosystemach jawnie ustawiono
`CHAOS_RESPONSE_QUALIFICATION_MODE: "observe"`. Wartość `disabled` i każda
nieznana wartość zamyka kwalifikację przed odczytami. Tryb egzekucji nie jest
dostępny w 142.4. Wrapper executora również odmawia wykonania przed polityką
i profilem; sam payload `mode: full` nie może tego zmienić.

Endpoint POST `/api/map/incidents/detection-candidates` pozostaje chroniony
istniejącą generacją sesji. Obserwator pochodzi z sesji. Cudze zgłoszenie jest
wyłącznie wskazówką: aktor musi mieć aktualną serwerową sesję, heartbeat,
pozycję i wersję pozycji. Token patrolu sprawdza spójność, nie autoryzuje kary.

Odczyty sesji (`account_login_ownership`), obecności (`mail_presence`) i pozycji
(`player_positions`) są trzema SELECT po indeksowanych kluczach w jednej
transakcji odczytu. Brak profilu i fallbacku. Stan incydentu i patrolu jest
pobierany po ID. Są to obserwacje; atomowy precommit kary należy do wykonawcy
w kolejnych etapach.

## Kwalifikacja

- Sesja logged_out → `actor_offline`; expired → `actor_session_expired`.
- Brak heartbeat/projekcji → deferred. Heartbeat starszy niż 90 s → offline.
- Online z pozycją zmienioną w ostatnich 90 s → online_active; nieruchomy
  online → online_inactive. To klasyfikacja ruchu, nie pomiar klawiatury/AFK.
  Stara data nieruchomej pozycji nie oznacza offline; obowiązuje bieżąca wersja.
- Wymagane position_version, zgodność z projekcją oraz pozycja klienta
  w odległości do 15 m od pozycji canonical. Odległość od służb jest liczona
  wyłącznie z pozycji canonical i serwerowej pozycji NPC.
- Czas zgłoszenia: do 15 s wstecz / 3 s w przyszłość; po bieżącym logowaniu.
  Bez odtwarzania zaległych kar po reconnect. Brak lub zły czas → odrzucenie.
- Aktywny incident/capsule, zgodne powiązanie, wersja ruchu i seed. Cooling
  po terminie, zamknięty incident lub wygasły patrol → odrzucenie. Stary
  expires_at aktywnego incydentu nie skraca jego rzeczywistego lifecycle.
- Inicjator pochodzi z trwałych suspect_refs, także po końcu operacji;
  pozostali to bystander. Własna aktywna operacja nie jest wymagana.
- Poprawne spotkanie: `status: observed`, `qualified: true`, `mode: observe`,
  actor_role, presence_class, position_version. Na markerze `OBS`.
  `consequence_executed` i `penalty_executed` zawsze false.
- Potwierdzone obserwacje są zapisywane w obecnym audycie. Klucz 10 s służy
  wyłącznie deduplikacji obserwacji; nie jest jednostką encounter/losowania 142.5.

## Walidacja lokalna

29 testów PASS: response_qualification, detection_feedback_shadow,
response_npc_frontend_contract, response_network_safety. Dodatkowe odczyty
SQLite bez tabeli profilu i spoofing offline: cały moduł qualification
11 testów PASS. Runner izolowany `tools/run_isolated_tests.py`.
Test endpointu używa autoryzowanej generacji sesji i wymusza błąd przy próbie
odczytu profilu lub uruchomienia executora. Stary validator pozostaje dla
historycznych testów MVP, ale endpoint produkcyjny już go nie wywołuje.

## Deploy i odbiór

Po wdrożeniu uruchomić `pm2 startOrRestart <ecosystem> --update-env` dla
web, territory-worker, ollama-worker i narrative-publisher, następnie
`pm2 save`. Odświeżyć klienta i otworzyć mapę ponownie (nowy payload wersji).

1. Podejść motocyklem do patrolu przy aktywnym incydencie: oczekiwane OBS
   i odpowiedź `observed/qualified: true`. Brak pobrania HC/usunięcia narzędzi.
2. Powtórzyć graczem postronnym: actor_role bystander, bez własnej operacji.
3. Wylogować aktora i obserwować go z drugiego konta: actor_offline; po samym
   zamknięciu przeglądarki uwzględnić okno heartbeat 90 s. Brak kary offline.
4. Po ponownym logowaniu nowa obserwacja może przejść, stare zgłoszenie nie.
5. Dla nieruchomego online dopuszczalne online_inactive; po ruchu stara wersja
   pozycji jest odrzucana, nowa może się zakwalifikować.
6. Odtworzenie starego requestu / zgłoszenie po końcu cooling lub patrolu
   nie jest pozytywną kwalifikacją. Offline/retry nie tworzy żadnych kar.

142.5: trwałe spotkanie i pojedynczy rzut 80/30. Naprawa atomowego wykonawcy,
canonical inventory/wallet i ponowne dopuszczenie kar nie są deklarowane
jako ukończone w 142.4. Więzienia i nowe ograniczenia pozostają w 143.
