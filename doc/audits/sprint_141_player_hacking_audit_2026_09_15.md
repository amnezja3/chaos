# Sprint 141.1 — audyt hakowania gracza

Data: 2026-09-15. Kod: `d7d477a` (pkg), drzewo czyste przed audytem.
Status: **AUDYT KODU I IZOLOWANE PRÓBY WYKONANE; pełne 141.1 nadal otwarte**.
Implementacja napraw nie rozpoczęta. [Zakres Sprintu 141](../sprints/sprint_141_player_hacking_end_to_end.md).

Powyżej i w ustaleniach poniżej zapisano stan audytu przed implementacją.
**Aktualizacja 15 IX:** pierwszy pakiet napraw opisuje checkpoint w Sprincie 141:
naprawiono renderer A02, odczyt logów, kwalifikację A05, lokalną bramkę A06
i pełne profile w serializacji dostępu. Pozostałe ustalenia nadal otwarte.
Reprodukcje w `tools/audit_141_*` są przypięte do kodu `d7d477a`, aby zachować
odtwarzalny baseline. Bieżący poprawny stan sprawdzają nowe testy regresyjne.

## Wniosek

Ścieżka wymaga naprawy źródeł danych, kwalifikacji narzędzi, wykonania efektów
i interfejsu. Nie jest to wyłącznie problem responsywności albo ciężkiego profilu.
Odtworzono dwa wyjątki narzędzi, stare współrzędne w odczytach mapy/pickera,
fałszywy sukces nieobsługiwanego narzędzia i brak bramki instalacji w handlerze security.

Próby wykonują funkcje wyodrębnione AST z aktualnego kodu, z syntetycznymi
zależnościami. Nie importują `run.py` ani `database.py`, nie otwierają bazy gry.
JS używa minimalnego zastępnika DOM. To dowód przebiegu funkcji, nie pełnego
requestu przez middleware, zapisu do SQLite, wyglądu w przeglądarce ani produkcji.

## 1. Mapa przepływu

| Ogniwo | Implementacja | Istotna zależność |
| --- | --- | --- |
| Teleport terminal/BlackNet/picker | `api_blacknet_cta_teleport` | `player_position_store.upsert` → intrusion → `record_map_player_actor_delta` → odpowiedź z wersją |
| Teleport biletem | `apply_googleplex_product_effect`, installer travel bridge | Osobny istniejący receipt zakupu; zachować historyczną naprawę własnej mapy |
| Aktorzy na mapie | `map_player_actors` → `build_player_actor` | Profile wszystkich kont, geometria i strategiczna widoczność |
| Picker | `build_victim_picker_player_candidates` | Kontakty/recent intruders/aimed target → pełny profil kandydata |
| Wybór celu | `mark_player_target`, warianty aim/hack | Relacja, security i `set_player_aimed_target`; stary profil nadal w łańcuchu |
| Przełamanie | `gonna_win`, `gonnaWinRequestQueue` | Procent security, cztery actions, `operation_only`, action receipt |
| Dostęp | `PlayerHackAccessStore.grant_access` | Próg ≥70% i wszystkie cztery actions true w gałęzi capture; potem clear target |
| Panel | `serialize_player_hack_access`, `refreshPlayerHackAccess` | Dwa pełne profile, cały katalog pro-system, countdown JS |
| Użycie | `api_player_hack_tool_use`, security update/preset | Pięć executorów, różne kontrakty zapisu i dedupe |
| Wynik | `usePlayerHackTool` → pięć okien | Result type, odświeżenie panelu, ograniczona obsługa błędów |

Nie przywracać pełnych profili ani legacy mirroru jako wspólnego rozwiązania.
Kontrakty źródłowe i hardbugfixy są zebrane w sekcji 3 sprintu; ponownie
sprawdzono szczególnie naprawę teleportu po 130.12, marker identity i stores.

## 2. Ustalenia i priorytety

### A01 — Arsenal Cleaner: wyjątek po wywołaniu usunięcia (krytyczne)

Aktualizacja 15 IX: przyczyna wyjątku naprawiona lokalnie. Zamiast patcha
profilu Cleaner używa canonical uninstall ze wspólną transakcją receiptu.
Regresje HTTP ≥35 MiB, rollback i konkurencja PASS. Historyczna reprodukcja
poniżej opisuje stan sprzed naprawy. Pełny lifecycle/delta/recovery nadal otwarty.

`run.py`, `api_player_hack_tool_use`, gałąź `arsenalCleaner`:
`victim_record` jest przypisany tylko w innej, wcześniej kończącej się gałęzi
`systemLogReader`. Udana próba Cleaner wywołuje `uninstall_app`, odczytuje
snapshot, następnie używa `victim_record['profile_revision']`.

Próba: zainstalowany Cleaner, aktywny dostęp, jedna usuwalna aplikacja,
wymuszony udany roll. Wynik: `UnboundLocalError`, wywołanie uninstall = 1,
record_tool_usage = 0. Ponieważ store był zastępnikiem, nie twierdzimy, że
usunięto realną aplikację. Kolejność kodu stwarza ryzyko częściowego efektu.

Naprawa musi objąć authority inventory i atomowość/recovery, nie tylko
dopisanie pełnego odczytu `victim_record` przed istniejącym kodem.

### A02 — System Log Reader: renderer rzuca wyjątek (wysokie)

`static/js/terminal.js`, `openSystemLogReaderApp`: dwa wywołania `appFlowTrace`
odwołują się do niezdefiniowanego `id`. Izolowana próba potwierdza
`ReferenceError: id is not defined` po dodaniu okna, przed renderem logów.
Backend może zwrócić sukces, a `usePlayerHackTool` pokaże ogólny błąd komunikacji.
Osobny problem backendu: odczyt logów z mirroru profilu zamiast `SystemMessageStore`.

### A03 — teleport: rozdzielone źródła pozycji (wysokie)

Teleport zapisuje `PlayerPositionStore`. `UserStore.list_profiles()` wykonuje
`SELECT profile_json FROM users ORDER BY id` i parsuje wszystkie dokumenty,
bez overlay pozycji. `map_player_actors` wybiera `current_position`, potem
`curently_possition` z tych dokumentów. Picker oraz mark gracza również
odczytują współrzędne z profilu.

Dwie próby (map actor i picker): profil ma 52.1/21.1, canonical fixture
50.1/19.1. Obie funkcje zwracają 52.1/21.1, bez wywołania store’u pozycji.
To odtwarzalna niespójność odczytu nawet na małym profilu. Ciężki profil może
dodatkowo opóźniać odczyt; wpływu na czas produkcyjny nie zmierzono.

Do sprawdzenia w integracji: snapshot nadpisujący poprawną deltę i brak
notyfikacji obserwatora starego obszaru po teleportacji poza niego.
`record_map_player_actor_delta` zbiera kontakty i właściciela przekazanego
intrusion_area; sam nie wyznacza wszystkich poprzednich obserwatorów.
To ryzyko audience wymagające testu całego call chainu, nie dowód każdego
przypadku znikania/pozostawania aktora na produkcji.

### A04 — mapa, picker i mark nie mają wspólnej bramki celu (wysokie)

`resolve_player_actor_actions` wymaga `combat_relation == hostile`, ale
picker przekazuje tylko kontekst friend/intruder/aimed. Próba z rzeczywistym
`build_player_actor` i resolverem daje nieaktywny `mark_target` intruza.
Mapa wzbogaca kontekst przez `project_territory_actor_visibility`, picker nie.

`mark_player_target` sprawdza self/friend/same clan, ale lokalny handler nie
wykorzystuje tej samej strategicznej widoczności/zasięgu. Dodatkowo mapa może
uznać hostile friend za dopuszczalny cel, podczas gdy mark blokuje friend.
Potrzebne uzgodnienie reguły z historią zmian strategicznej widoczności;
nie uznawać automatycznie jednej gałęzi za prawidłową tylko dlatego, że jest nowsza.
Plan sprintu przewiduje ochronę friend — rozbieżność zapisać i rozstrzygnąć
przed zmianą reguł gameplayu, bez poszerzania dostępu do dowolnego username.

### A05 — cały katalog pro-system udaje narzędzia post-hack (wysokie)

Próba z instalacją wszystkich pozycji: panel otrzymuje 10 enabled narzędzi.
`victimPicker` wysłany do tool/use zwraca sukces-placeholder, mimo braku executora.
Pełna macierz stałego `PRO_SYSTEM_TOOLS` jest poniżej. Bez nowego sklepu ani
usuwania legalnych aplikacji pulpitu; potrzebna jawna kwalifikacja do dostępu.

### A06 — security direct handlers bez kontroli instalacji (wysokie)

Izolowane `api_player_hack_security_update` z aktywnym dostępem, bez providera
instalacji, akceptuje zmianę i wywołuje guarded patch. Także preset nie ma
lokalnej kontroli narzędzia. Nie wyłączać CAS; dodać wspólną bramkę wykonania.
Pełny request z middleware i kontrolą generacji/precommit pozostaje do testu.

### A07 — effects, receipts i grant (wysokie; analiza kolejności)

- Friend Kicker: has-usage → wybór/roll → usunięcie kontaktów/powiadomienia
  → record usage. Sam lock podczas zapisu usage nie chroni wcześniejszego efektu.
- Cleaner: analogiczna późna rejestracja użycia, plus A01 i mieszanie inventory
  z profile patch. Potrzebna spójność aplikacji, plików, storage i live launcherów.
- Financial Sniffer: istnieje rezerwacja pending, stabilny transfer key i
  complete usage. Zachować je. Powiadomienie detected jest po complete usage;
  gałąź duplicate nie odtwarza tego powiadomienia. Test crash/replay musi
  sprawdzić, czy przerwanie pomiędzy tymi krokami nie gubi ostrzeżenia.
- Grant: store używa upsertu nadpisującego czasy; nie jest samodzielnie
  idempotentny względem źródłowej akcji. Zewnętrzny action receipt istnieje,
  ale okno awarii grant → finish receipt wymaga próby integracyjnej.

Nie wykonano współbieżnego ani awaryjnego testu realnych store’ów; powyższe
to ryzyka wynikające z kolejności kodu, poza odtworzonym A01.

### A08 — UI, częściowe odpowiedzi i zegary

Panel: stała szerokość 320 px, odsunięcie bottom 122 px, `overflow: hidden`,
etykiety `nowrap`, brak lokalnego limitu wysokości/scrolla listy. Okna wyników
także mają stałe szerokości, np. Log Reader 520 px i Security Proxy 620 px.
To konkretne reguły CSS do poprawy; nie wykonano pomiaru w przeglądarce.

Timer odejmuje sekundy i po wygaśnięciu planuje ukrycie całego panelu;
callback nie jest związany z tożsamością dostępu. Refresh nie porównuje wersji
grantu/celu. Globalny session bridge chroni konto/generację, ale nie zastępuje
izolacji dwóch grantów w tej samej sesji. Brak lokalnego in-flight w użyciu
narzędzia, wspólny catch dla transportu i błędów renderera. Sprawdzić późne
odpowiedzi, A → B → A, tło/obrót i stare timeouty przy nowym dostępie.

## 3. Macierz katalogu

Wszystkie poniższe ID należą do stałego katalogu `PRO_SYSTEM_TOOLS` przy HEAD.
Cena to zakup, nie dodatkowa opłata każdego użycia. LVL/RSP z katalogu nie
są dowodem ich egzekwowania przy każdej mutacji. Domyślne 5 min dostępu i 3 h
cooldown pochodzą z config.py i mogą być zmienione env; stan serwera nieznany.

| ID | Cena / LVL / RSP | Executor i efekt | Decyzja |
| --- | --- | --- | --- |
| systemLogReader | 900 / 2 / 20 | Logi; brak operacji/pliku; A02 i zły read store | Zostawić, naprawić odczyt i renderer |
| securityPanelProxy | 3000 / 10 / 180 | Security read/update/preset; guarded profile mutation | Zostawić, projekcja + bramki i CAS |
| financialSniffer | 2500 / 8 / 120 | Próba HC, wallet transfer i usage; ryzyko 2 | Zostawić, odchudzić i przetestować crash/replay |
| friendKicker | 2200 / 7 / 100 | Losowy kontakt, MailStore i usage; ryzyko 3 | Zostawić, atomowy efekt/recovery |
| arsenalCleaner | 3500 / 12 / 220 | Losowa dozwolona aplikacja; ryzyko 4; inventory + błędny patch | Zostawić, naprawić A01 i pełny lifecycle |
| victimPicker | Wymagania własnej aplikacji | Wybór celu, brak executora tool/use | Wyłączyć z post-hack, zachować launcher |
| territoryControl | Wymagania własnej aplikacji | Kontrola terytoriów | Wyłączyć z post-hack, zachować launcher |
| operationControl | Wymagania własnej aplikacji | Kontrola operacji | Wyłączyć z post-hack, zachować launcher |
| ghostnetworkSuite | Wymagania własnej aplikacji | GhostNetwork | Wyłączyć z post-hack, zachować launcher |
| agi2108Console | Wymagania własnej aplikacji | Analiza właściciela | Wyłączyć z post-hack, zachować launcher |

GhostLab: `runtime_status=pending_custom_runtime` jest osobną klasą rekordów
katalogu; nie ma automatycznego executora w tool/use. Nie przypisywać po nazwie
template’u do pięciu executorów. Audyt nie otwiera lokalnego/serwerowego
`json_resources`, więc nie stanowi listy konkretnych opublikowanych custom ID.
Przed kwalifikacją migracyjną potrzebny ograniczony eksport samego katalogu.

Narzędzia przełamania security są wybierane z ogólnego katalogu według
map_actions/target/security, nie z powyższej piątki post-hack. Pełne pokrycie
ich kombinacji i progów w `gonna_win` pozostaje bramką integracyjną 141.1.

## 4. Koszt profilu i wymagane projekcje

Próba serializera z syntetycznym providerem JSON:

| Profil atakującego / ofiary | Wywołania pełnego providera | Zdekodowane bajty fixture |
| --- | ---: | ---: |
| mały / mały | 2 | 114 |
| 35 MiB / mały | 2 | 36 700 274 |
| mały / 35 MiB | 2 | 36 700 274 |
| 35 MiB / 35 MiB | 2 | 73 400 434 |

To koszt wywołań funkcji przy podstawionym providerze, nie produkcyjna metryka
`[HOT_PATH]`, czas requestu, query count SQLite czy writer wait. Pełny baseline
endpointów/workera pozostaje niewykonany. Już ten zwykły odczyt nie spełnia zera.

Priorytet projekcji: identity/capability obu kont; aktualna pozycja i przestrzenna
widoczność aktorów bez list_profiles; bounded security read; installed tools
z inventory; 5 ostatnich logów z SystemMessageStore; access/usage projection.
Pozostałe read calle w tool/use dodają kolejne profile do kosztu serializera.
Write wyjątek może dotyczyć canonical security; samo sprawdzanie narzędzia,
nicka, levelu i czasu dostępu nie jest takim wyjątkiem.

## 5. Weryfikacja i granice audytu

Wykonano:

- `python -B tools/audit_141_player_hack_probes.py`: próby opisane A01/A03–A06
  oraz cztery warianty kosztu serializera zakończyły się oczekiwanymi obserwacjami.
- `node tools/audit_141_player_hack_frontend.js`: reprodukcja A02.
- `node tests/js/test_map_target_hitbox.js`: PASS.
- `node tests/js/test_session_generation_isolation.js`: PASS.

Skrypty audytu celowo rozpoznają stan wadliwy. Ich powodzenie nie oznacza
poprawności mechaniki; po naprawie zamienić przypadki na regresje poprawnego
zachowania. Python WindowsApps wymagał uruchomienia poza sandboxem;
próby nadal nie importowały aplikacji ani nie korzystały z DB.

Nie wykonano: pełnego Flask E2E, realnych transakcji/integrity/CAS/LKG,
reprodukcji wyścigów i awarii procesu, pomiaru writer locków, testów widoczności
na dwóch prawdziwych sesjach, wizualnego desktop/mobile i audytu produkcji.
Istniejące testy startowe: `test_territory_conflict_map_cutover.py` (map actors),
`test_victim_picker.py`, `test_wallet_runtime_cutover.py`,
`test_target_persistence.py`, profile hot path i session precommit.
Nie uruchamiano ich przez nieizolowany import `run.py`.

## 6. Kolejność dalszej pracy

1. Uzupełnić izolowany harness pełnych requestów i transakcji oraz baseline
   wszystkich dotkniętych ścieżek, zacząć od A01/A02/A06 i testu dwóch pozycji.
2. 141.2: canonical position → widoczność → delta/snapshot → marker/picker,
   razem z ograniczeniem pełnych skanów i testem opuszczenia starego obszaru.
3. 141.3–141.4: wspólny kontekst celu i kwalifikacja narzędzi; rozstrzygnąć
   friend kontra hostile, grant/replay i unsupported tool bez placeholdera.
4. 141.5: pięć executorów, w pierwszej kolejności częściowy efekt Cleaner,
   bramka Security i render Log Reader; potem receipts/recovery i projekcje.
5. 141.6–141.7: responsywność, izolacja odpowiedzi i pełny odbiór E2E.

Nie dopisywać PASS 141.1 ani zamknięcia 141 na podstawie tego raportu.
Audyt dostarcza konkretnej podstawy do napraw, z jawną listą brakujących dowodów.
