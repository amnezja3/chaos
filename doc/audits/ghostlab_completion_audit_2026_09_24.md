# GhostLab — audyt niedokończonej ścieżki

Data: 2026-09-24. Zakres: lokalny kod, dokumentacja historyczna, dwa istniejące testy kontraktu i izolowana diagnostyka helperów. Bez zmian runtime, danych graczy i wdrożenia. Nie wykonano testu zakupu ani użycia aplikacji na serwerze.

## Wniosek

GhostLab ma rozbudowaną ścieżkę tworzenia projektu, edycji blueprintu, walidacji, budowania snapshotu, eksportu i publikacji do Googleplexu. Niedokończony jest **runtime narzędzi utworzonych przez gracza**: opublikowana aplikacja dostaje `pending_custom_runtime`, a jej blueprint nie jest wykonywany przez Player Hack Access.

To nie jest kwestia włączenia flagi. Obecny endpoint wykonawczy rozpoznaje zamknięty katalog wbudowanych narzędzi, nie identyfikatory aplikacji GhostLaba. Przed dołączeniem wykonania trzeba również uszczelnić identyfikację aplikacji i zgodność publikowanego buildu z projektem.

## Co faktycznie odłożono

- `doc/gameplay/action_player.md`, Sprint 21 „Build System”: Validate → Compile → Preview → Export; następny etap to Publisher. Nie znaleziono tu potwierdzenia zamrożenia całego GhostLaba.
- `doc/history/project_journal_13082026.md:2572`, Sprint 28 „GhostLab Pro Tools Contract”: kontrakt publikacji ukończony; przy `:2610` jawnie pozostawiono `pending_custom_runtime` jako świadome ograniczenie. To najlepiej pasuje do wspomnianej niedokończonej końcówki.
- `doc/gameplay/app_contract.md:556`: instalacja wspólną ścieżką Googleplexu, docelowe wykonanie przez Player Hack Access, brak własnych typów operacji bez przyszłego runtime.
- `doc/history/project_journal_13082026.md:5636`, Sprint 60.6: odłożono osobny Async Operation Runner. Jedynym bezpiecznym kandydatem był compile GhostLaba; koszt runnera uznano za nieuzasadniony dla jednej akcji. To osobna decyzja, nie warunek uruchomienia narzędzi.

Nie znaleziono dosłownego uzasadnienia „młody kod” dla zatrzymania custom runtime. Dokumenty potwierdzają samo świadome odłożenie wykonania.

## Mapa funkcjonalności

| Odcinek | Stan w kodzie | Uwagi |
| --- | --- | --- |
| Workspace, projekty, nazwy, usuwanie | Zaimplementowane | Projekty w `profile.files.pro_system_projects`; legacy zapis profilu. |
| Pięć szablonów i edytor | Zaimplementowane | Financial Sniffer, Friend Kicker, Security Panel Proxy, System Log Reader, Arsenal Cleaner. |
| Validate / Preview | Zaimplementowane częściowo | Walidacja pól i opis rezultatu; brak wykonania/symulacji efektu na graczu. |
| Compile / historia buildów | Zaimplementowane jako snapshot | `build_ghostlab_artifact` zapisuje blueprint i kontrakt, nie kompiluje kodu wykonywalnego. |
| Export `.glab` | Zaimplementowane | Eksport JSON; nie znaleziono odpowiadającego endpointu importu. |
| Publisher / Googleplex | Zaimplementowane z usterkami | Wspólny katalog, cena, wymagania, jakość, rozmiar, autor. |
| Zakup / instalacja | Wspólny kontrakt aplikacji | Dwa testy potwierdzają kształt danych; brak audytu E2E zakup → instalacja w tej sesji. |
| Faktyczna akcja wygenerowanego narzędzia | Niedokończona | `pending_custom_runtime`; generowane ID nie przechodzi resolvera narzędzi Player Hack. |
| Research | Placeholder | Locked, progres 0, bez zapisu postępu i unlocków. |
| Ghost Exchange w IDE | Biblioteka / fundament | Community i wymiana blueprintów pozostają planem; nie mylić z istniejącym rynkiem paczek danych. |
| AI, Plugin SDK, rollback, dependency graph | Roadmapa v2 | Nie są wymagane do domknięcia wykonania pięciu obecnych szablonów. |

Źródła: `run.py:17724–18090`, `run.py:28602–28925`, `static/js/terminal.js:14465–15646`.

## Ustalenia wymagające naprawy

### 1. Wysoki priorytet: kolizja aplikacji różnych autorów

`run.py:17947` buduje ID jako `ghostlab_<slug>_<version>` bez autora lub globalnie unikalnego ID projektu. Slug jest unikalny tylko w projektach jednego gracza. Publisher (`run.py:28831`) zastępuje rekord o tym samym ID, bez sprawdzenia właściciela istniejącej publikacji. Kontrola duplikatu nazwy pomija właśnie rekord o tym samym ID.

Diagnostyka dwóch autorów `audit_a` i `audit_b` potwierdziła identyczne ID oraz różne `purchase_account`. Z kodu endpointu wynika możliwość zastąpienia cudzej aplikacji i zmiany odbiorcy kolejnych zakupów. Nie wykonywano takiego nadpisania na produkcji ani testu HTTP tego scenariusza.

Wymagane: trwała tożsamość projektu/aplikacji niezależna od nazwy i wersji, kontrola autora przy aktualizacji, obsługa istniejących ID bez zerwania zainstalowanych aplikacji.

### 2. Wysoki priorytet: publikacja starego buildu po edycji

Zapis blueprintu ustawia `draft`, lecz zachowuje poprzedni artefakt. Publisher sprawdza poprawność aktualnego blueprintu i obecność artefaktu, bez porównania ich rewizji. Builder preferuje snapshot artefaktu.

Potwierdzony przykład: build z `steal_percent=8`, następnie zapis projektu z `steal_percent=1`; wynik buildera nadal zawiera `8`. Dodatkowo frontend `publishGhostLabProject` (`static/js/terminal.js:15475`) waliduje pola edytora, lecz POST nie zapisuje tych pól i nie kompiluje ich przed publikacją.

Wymagane: jawny stan niezapisanych zmian, rewizja/hash wejścia buildu, publikacja konkretnego niezmiennego buildu i odmowa publikacji niezgodnej z deklarowaną rewizją. UI musi jednoznacznie wskazywać, którą wersję publikuje.

### 3. Bloker funkcjonalny: brak adaptera wykonawczego

`run.py:16751` rozpoznaje tylko `PRO_SYSTEM_TOOLS`; `run.py:17131` zawiera zamknięty `PLAYER_HACK_TOOL_IDS`. `/api/player-hack/tool/use` (`:26462`) odrzuca nierozpoznane ID przed wykonaniem akcji.

Diagnostyka potwierdziła, że wygenerowana aplikacja ma `pending_custom_runtime`, a `get_pro_system_tool(app['id'])` zwraca `None`. Publisher dodaje jedynie terminalowe logi informujące o oczekującym runtime. Nie znaleziono wykonawcy `blueprint_snapshot`.

Wymagane: adapter z zainstalowanego ID GhostLab do zaufanego artefaktu i jednej z pięciu dozwolonych rodzin. Parametry blueprintu muszą przechodzić serwerowe ograniczenia; nie wystarczy dopisać ID do allowlisty ani uruchamiać dowolny tekst komendy. Należy zachować aktualne bramki Player Hack Access, własność/instalację narzędzia, blokady aresztu i idempotencję skutków.

### 4. Przed uruchomieniem efektów: walidacja semantyczna

`validate_ghostlab_blueprint` (`run.py:17774`) dopuszcza `bool` jako liczbę oraz nie odrzuca NaN. Oba przypadki potwierdzono bezpośrednim wywołaniem helpera. Nie badano akceptacji NaN przez HTTP. Pola polityk są w dużej części tylko tekstem o ograniczonej długości, nie zamkniętym zestawem reguł. Nieznany template trafia w gałąź custom notes.

Wymagane: wersjonowany schemat, allowlista szablonów i kluczy, skończone liczby, integer tam, gdzie wymagany, enumy polityk i twarde reguły ochrony narzędzi/systemów. Limity balansowe pozostają serwerowe.

### 5. Spójność zapisu i aktualizacji

Publisher odczytuje cały `app_config`, zapisuje zastąpioną listę, następnie osobno aktualizuje projekt w profilu. Nie ma jednej transakcji obejmującej obie zmiany. CRUD/compile operują na `files` profilu; historia buildów rośnie bez limitu. Z kodu wynika ryzyko częściowej publikacji i utraty aktualizacji przy współbieżnych zapisach, ale nie reprodukowano wyścigu.

Przed runtime trzeba ustalić atomową/idempotentną publikację oraz rewizje projektu. Dedykowany store projektów jest rekomendacją architektoniczną, nie dowiedzionym jedynym rozwiązaniem. Usunięcie projektu obecnie nie usuwa opublikowanego wpisu; potrzebna jawna polityka wycofania i aktualizacji instalacji.

## Weryfikacja wykonana

PASS — dwa istniejące testy uruchomione przez `tools/run_isolated_tests.py`:

```text
tests.test_target_persistence.TargetPersistenceHelpersTest.test_ghostlab_published_tool_has_app_contract
tests.test_target_persistence.TargetPersistenceHelpersTest.test_ghostlab_published_tool_preserves_requirements_and_googleplex_shape
```

Osobny proces diagnostyczny zmienił cwd na katalog tymczasowy przed importem `run`; nie używał bazy gry. Sprawdził helpery buildera, walidatora i resolvera. Wyniki:

```text
runtime_status = pending_custom_runtime
runtime_resolver_found = false
cross_owner_same_app_id = true
purchase_accounts = [audit_a, audit_b]
draft_steal_percent = 1
published_steal_percent = 8
nan_validation.valid = true
bool_validation.valid = true
```

To nie jest PASS kompletnego GhostLaba. Testy kontraktu potwierdzają metadane, nie skuteczność narzędzi ani bezpieczną aktualizację katalogu.

## Zalecana kolejność domknięcia

1. **Projekt i publikacja:** trwałe ID, własność, schemat, rewizje, aktualność artefaktu, zapis odporny na retry i współbieżność. Regresje dla dwóch autorów i edycji po compile.
2. **Pierwsza kompletna ścieżka:** System Log Reader jako ograniczony odczyt systemowych komunikatów. Projekt → compile → publish → zakup → instalacja → aktywny Player Hack Access → rzeczywisty wynik. Bez dostępu do prywatnych rozmów.
3. **Pozostałe cztery rodziny:** istniejące serwerowe wykonawce jako baza, z kontrolowanymi parametrami blueprintu; wspólna księga HC, spójne zmiany kontaktów/zabezpieczeń/inwentarza, cooldown i deduplikacja.
4. **Testy domykające:** brak dostępu, wygasły dostęp, reinstall, konfiskata, areszt, reconnect, retry i równoczesne użycie; aktualizacja aplikacji nie może podmieniać wykonywanego artefaktu w trakcie akcji.

Research, Community, AI i osobny async runner pozostawić poza zakresem pierwszego domknięcia. Audyt nie tworzy ani nie uruchamia nowego sprintu; dostarcza zakres do jego zaplanowania.
