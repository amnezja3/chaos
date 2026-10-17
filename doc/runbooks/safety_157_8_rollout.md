# 157.8 — wdrożenie ochrony komunikacji i przygotowanie 16+

Status: instrukcja przygotowana lokalnie, nie wykonana na produkcji. Dwa niezależne wdrożenia: ochrona kontaktu oraz późniejsza polityka wieku. Dokumenty prawne pozostają DRAFT.

## Flagi

- `CHAOS_COMMUNICATION_SAFETY_ENABLED=0` domyślnie. Włączenie wymaga migracji, odbioru, operatora moderacji i ustalenia zasad przetwarzania zgłoszeń.
- `CHAOS_AGE_POLICY_ENABLED=0` domyślnie. Wyłącznie ta nowa flaga steruje polityką 16+; stara flaga nie aktywuje nowego progu.
- Zachować `CHAOS_ADULT_POLICY_ENABLED=0`. Nie włączać nowej polityki wieku w ramach wdrożenia komunikacji.
- Utrwalić wybrane wartości w rzeczywistej konfiguracji PM2, bez sekretów w repo. Sam restart z `--update-env` nie zastępuje konfiguracji startowej.

## Przygotowanie i migracja

Zapisać commit i stan PM2 do prywatnego katalogu z `umask 077`. Nie udostępniać pełnego `pm2 jlist`, może zawierać sekrety.

```bash
.venv/bin/python tools/safety_157_8_migrate.py --db data/game.sqlite3
```

Oczekiwane dry_run, integralność i FK OK, dane istniejące niezmienione. Następnie zatrzymać piszące procesy CHAOS zgodnie z zapisanym stanem; wykonać backup bazy i sesji.

```bash
.venv/bin/python tools/safety_157_8_migrate.py --db data/game.sqlite3 --backup "$SAFETY_BACKUP/game.sqlite3"
tar -czf "$SAFETY_BACKUP/flask-session.tar.gz" -C data flask_session
.venv/bin/python tools/safety_157_8_migrate.py --db data/game.sqlite3 --apply
.venv/bin/python tools/safety_157_8_migrate.py --db data/game.sqlite3 --check --baseline "$SAFETY_BACKUP/game.baseline.json"
.venv/bin/python tools/safety_157_8_migrate.py --db data/game.sqlite3 --apply
```

`SAFETY_BACKUP` musi wskazywać wcześniej utworzony, nowy prywatny katalog. Wykonywać kroki kolejno, zatrzymując się przy błędzie. Oczekiwane: migrated, baseline_matches, already_migrated. Uruchomić tylko wcześniej działające procesy, początkowo z obiema nowymi flagami OFF.

Migracja dodaje tabele blokad, zaproszeń, limitów, raportów, działań moderatorskich, ukryć, sankcji komunikacyjnych, wstrzymanych źródeł i historii blokad wieku. Nie zmienia kont, zaakceptowanych znajomości, postępów ani sesji. Stare blokady wieku dostają wpis `legacy_review` z nieustalonym progiem i przyczyną; pozostają zablokowane.

## Odbiór komunikacji

Po decyzji operatora włączyć wyłącznie ochronę komunikacji. Użyć kont testowych:

1. Obcy gracz nie wysyła DM. Zaproszenie, jawna akceptacja i DM działają.
2. Odrzucenie, limit ponawiania, blokada z obu kierunków, odblokowanie bez automatycznej znajomości.
3. Ukrywanie wypowiedzi w WORLD/KLAN; systemowe informacje i PvP nadal dostępne.
4. Odtworzenie komunikacji z synchronizacji nie ujawnia zablokowanego tekstu.
5. Zgłoszenie wiadomości, profilu i publikacji. Moderator widzi dowód; druga strona nie widzi zgłaszającego.
6. Decyzja, czasowe ograniczenie komunikacji, przywrócenie i odwołanie.
7. BlackNet: ukrycie publikacji, wstrzymanie źródła, wznowienie. Wstrzymanie jest według `source_scope`, może obejmować więcej niż jeden kanał. Nie anuluje już trwającego wywołania modelu; zatrzymuje nowe pobrania zadań i publikację.
8. Desktop/mobile/PWA, PL/EN, konto po wylogowaniu i ponownym logowaniu.

Panel: Cyberner → Kontakt i bezpieczeństwo, albo Konto i bezpieczeństwo → Kontakt i bezpieczeństwo. Panel otwiera się wewnątrz okna CHAOS. Moderacja dostępna dla istniejącego administratora `admin`; brak nowej roli moderatora.

## Blokady wieku i późniejsza aktywacja

Przed uruchomieniem 16+ zatwierdzić regulamin i prywatność, ustalić wersję finalnych dokumentów oraz odpowiadające jej `TERMS_VERSION`. Obecny identyfikator `157-16-v1` jest kontraktem technicznym DRAFT. Nie zmieniać treści już zaakceptowanej wersji bez nowego identyfikatora.

Starego „poniżej 18” nie interpretować jako „poniżej 16”. Rozstrzygnięcie operatora wymaga uzasadnienia:

```bash
.venv/bin/python tools/identity_18_access.py --db data/game.sqlite3 --username LOGIN --confirm-username LOGIN --reason 'Uzasadnienie rozstrzygnięcia' release
```

Nazwa narzędzia zachowana dla kompatybilności. `restrict` opcjonalnie przyjmuje `--threshold 16` lub `18`; nieznanego progu nie zgadywać. Nie umieszczać dokumentów ani zbędnych danych w uzasadnieniu. Zwolnienie z blokady nie zapisuje zgody; wymagana nowa świadoma akceptacja.

## Wycofanie i awarie

Nie przywracać starej bazy po wznowieniu świata. Zachować nowe tabele i zgłoszenia. Kod sprzed ochrony komunikacji nie respektuje blokad — nie jest bezpiecznym automatycznym rollbackiem po aktywacji. Nie wyłączać ochrony jako sposobu naprawy błędu, który otworzyłby zablokowany kontakt; ograniczyć wysyłkę na czas poprawki.

Brak schematu przy ON ma zamknąć chronioną ścieżkę. Wstrzymane źródła są respektowane przez workerów na podstawie bazy, również poza kontekstem HTTP. Nie usuwać tych rekordów w rollbacku bez decyzji moderatora.

## Decyzje wymagane przed uruchomieniem

Obsada i czas reakcji moderacji, pilne zagrożenia, odwołania, retencja dowodów i backupów, procedura usunięcia danych z dowodów, wykaz dostawców i przepływów AI, publiczne pola profilu, odpłatność, kwalifikacja prawna usługi i zakres obowiązków wobec osób 16–17 oraz potwierdzenie adresu operatora. Nie zakładać, że checkbox rozstrzyga te kwestie. Google OAuth nie jest uzasadnieniem ograniczenia 18+.
