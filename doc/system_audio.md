# CHAOS — system efektów dźwiękowych gry

Status: `READY FOR IMPLEMENTATION`

Zakres: Sprinty `130.8.9.SFX.1`–`130.8.9.SFX.5`.

Dokument jest kanoniczną specyfikacją wdrożeniową systemu audio. Audyt zastanego
kodu i szersze uzasadnienie architektury pozostają w
`doc/game_sound_effects_system.md`.

## 1. Cel i granice systemu

Budujemy jeden klientowy system krótkich efektów dźwiękowych dla całej gry.
Pierwszym odbiorcą jest czterosekundowe show `Secret Path`, ale ten sam silnik ma
następnie obsłużyć przejęcie celu, Cybernera, komunikaty systemowe i OFS.

System audio:

* prezentuje zdarzenia, ale nie rozstrzyga gameplayu;
* nie może blokować bootu, mapy, aplikacji ani requestu;
* nie może przyjmować dowolnej ścieżki audio z payloadu;
* nie odtwarza ponownie zdarzeń odzyskanych z recovery lub backlogu;
* ma jednego właściciela w głównym oknie desktopu;
* działa poprawnie także wtedy, gdy przeglądarka zablokuje autoplay albo asset
  jest niedostępny.

Nie zmieniamy w tych sprintach logiki capture, konfliktów, geometrii terytoriów,
wyników aplikacji ani kolejek operacji.

## 2. Kontrakt docelowy

### 2.1. Jeden właściciel audio

Kanoniczny moduł:

```text
static/js/game_sfx.js
window.GameSfx
```

Jest ładowany w dokumencie desktopu przed `ghost_radio.js` i `terminal.js`.
Mapa w iframe nie tworzy własnego miksera i nie odtwarza plików bezpośrednio.
Wywołuje bezpieczny most do rodzica:

```js
window.parent.GameSfx.play("secret_path.scene_03", {
    event_id: "secret-path:<target-id>:<sequence>",
    source: "map",
    duration_ms: 4000
});
```

Brak rodzica, brak `GameSfx` albo odrzucone `play()` pozostawiają pełną ścieżkę
wizualną i gameplayową.

### 2.2. Publiczne API

```js
GameSfx.init(options)
GameSfx.unlock()
GameSfx.preload(groupOrKeys)
GameSfx.play(eventKey, context = {})
GameSfx.stop(handleOrChannel, options = {})
GameSfx.setEnabled(enabled)
GameSfx.setVolume(value)
GameSfx.getState()
```

`play()` zwraca uchwyt pozwalający zatrzymać głos oraz Promise kontrolowanego
wyniku. Oczekiwane pominięcia nie rzucają nieobsłużonego wyjątku:

```js
{ ok: false, event_key: "...", reason: "muted" }
```

Dozwolone `reason` w MVP:

```text
disabled
muted
duplicate
cooldown
voice_limit
autoplay_blocked
unknown_event
missing_asset
play_failed
```

### 2.3. Manifest jako allowlista

```text
static/audio/sfx/manifest.v1.json
static/audio/sfx/secret_path/
static/audio/sfx/capture/
static/audio/sfx/cyberner/
static/audio/sfx/system/
static/audio/sfx/ofs/
```

Minimalny rekord:

```json
{
  "file": "secret_path/01_target_repaired.mp3",
  "bus": "lore",
  "priority": 70,
  "volume": 0.9,
  "max_duration_ms": 4000,
  "cooldown_ms": 500,
  "duck_radio": 0.42
}
```

Payload gameplayowy wskazuje wyłącznie `event_key`. Ścieżka, głośność,
magistrala i maksymalny czas pochodzą z lokalnego manifestu.

### 2.4. Magistrale

| Magistrala | Zastosowanie | Domyślny limit głosów |
|---|---|---:|
| `lore` | Secret Path i odkrycia | 1 |
| `gameplay` | capture, sukces, porażka | 2 |
| `message` | Cyberner i późniejsze wiadomości | 2 |
| `system` | ostrzeżenia i zdarzenia krytyczne | 1 |
| `ui` | lekkie potwierdzenia interfejsu | 3 |

Wyższy priorytet może zastąpić głos o niższym priorytecie na tej samej
magistrali. `lore` zawsze zastępuje poprzedni głos `lore`.

### 2.5. Ustawienia i autoplay

MVP używa lokalnych ustawień:

```text
chaos_sfx_enabled = 1 | 0
chaos_sfx_volume = 0.0 .. 1.0
```

Audio zostaje uzbrojone po pierwszym `pointerdown` lub `keydown` w desktopie.
Mapa może zgłosić gest do rodzica, ale nie utrzymuje drugiego stanu unlock.
Preload zaczyna się dopiero po interakcji i nie należy do krytycznej ścieżki
bootu.

### 2.6. Ghost Radio

Radio zachowuje własne `volume` i `muted`. SFX używa wyłącznie przejściowego
mnożnika `duck_gain`. Nakładające się żądania duckingu są rozliczane uchwytami
albo licznikiem; zakończenie jednego efektu nie może wyłączyć duckingu wymaganego
przez drugi. Po ostatnim zwolnieniu radio wraca dokładnie do poprzedniego stanu.

## 3. Sześć scen Secret Path

Losowany jest jeden rekord sceny. Ten sam rekord wybiera tekst, animację i MP3.

| `scene_id` | `sound_event` | Sens sceny |
|---|---|---|
| `target_repaired` | `secret_path.scene_01` | naprawiono uszkodzony kanał celu |
| `route_open` | `secret_path.scene_02` | otwarto skróconą drogę do aplikacji |
| `skill_verified` | `secret_path.scene_03` | operator odkrył ukrytą ścieżkę |
| `acceleration` | `secret_path.scene_04` | skrócono drogę interfejsu, bez bonusu liczbowego |
| `lore_discovered` | `secret_path.scene_05` | znajomość lore daje przewagę informacyjną |
| `chaos_protocol_2108` | `secret_path.scene_06` | tarcza, ostrze i wyładowanie protokołu CHAOS |

Pliki:

```text
secret_path/01_target_repaired.mp3
secret_path/02_route_open.mp3
secret_path/03_skill_verified.mp3
secret_path/04_acceleration.mp3
secret_path/05_lore_discovered.mp3
secret_path/06_chaos_protocol.mp3
```

Każdy plik trwa docelowo `3.6–4.0 s`, ma łagodny początek i koniec, nie zawiera
długiej ciszy wejściowej i ma zbliżoną głośność odczuwalną. Czas wizualnego show
pozostaje autorytatywnie równy `4000 ms`.

---

# Sprint 130.8.9.SFX.1 — fundament

## Cel

Zbudować bezpieczny, niezależny od gameplayu silnik SFX i przygotować go do
pierwszej integracji. Po tym sprincie żadna akcja gry nie wydaje jeszcze nowego
dźwięku.

## Zakres

1. Dodać `static/js/game_sfx.js` i załadować go raz w głównym desktopie.
2. Dodać parser oraz walidację `manifest.v1.json`.
3. Zaimplementować API z rozdziału 2.2 i kontrolowane wyniki błędów.
4. Zaimplementować unlock autoplay na pierwszym geście użytkownika.
5. Dodać cache/preload nieblokujący bootu oraz ujemny cache błędnych assetów.
6. Dodać magistrale, priorytety, limity głosów, cooldown i dedupe `event_id`.
7. Dodać lokalny stan `enabled` oraz `volume`, z clampem `0..1`.
8. Rozszerzyć Ghost Radio o przejściowy, wielokrotny ducking bez zmiany zapisanej
   głośności użytkownika.
9. Wystawić lekką diagnostykę `loaded`, `active_voices`, `blocked`, `failed`.

## Strażniki

* moduł nie wykonuje requestów do backendu;
* init i preload nie są awaitowane przez boot pulpitu ani mapy;
* błędny manifest nie zatrzymuje `terminal.js`;
* kontekst `play()` nie może nadpisać ścieżki, magistrali ani limitów manifestu;
* żadne istniejące ustawienie Ghost Radio nie zmienia semantyki.

## Testy

* parser manifestu i odrzucenie nieznanego eventu;
* mute, volume clamp, cooldown, dedupe i voice limit;
* priorytet i zastępowanie głosu;
* `play()` reject, brak pliku i brak autoplay bez wyjątku globalnego;
* preload nie jest częścią boot gate;
* dwa nakładające się duckingi zwalniają radio we właściwej kolejności;
* `node --check` dla zmienionych plików JS.

## Poza zakresem

Secret Path, capture, Cyberner, OFS, synchronizacja ustawień z profilem i
transkodowanie audio.

## DoD

Silnik można uruchomić i przetestować neutralnym eventem developerskim, ale nie
jest on podpięty do gameplayu. Awaria całej warstwy audio pozostawia desktop,
mapę, radio i aplikacje funkcjonalne.

---

# Sprint 130.8.9.SFX.2 — sześć scen Secret Path

## Cel

Podłączyć pierwsze produkcyjne użycie `GameSfx`: osobny dźwięk dla każdej z
sześciu czterosekundowych scen Secret Path.

## Zakres

1. Nadać sześciu rekordom scen stabilne `scene_id` i `sound_event`.
2. Dodać sześć MP3 oraz komplet sześciu wpisów manifestu.
3. Losować scenę dokładnie raz i przekazywać ten sam rekord warstwie obrazu,
   tekstu oraz audio.
4. Przy geście kliknięcia nazwy uzbroić audio, a po sukcesie
   `/api/map/aim-target` wywołać audio przez właściciela w desktopie.
5. Zsynchronizować start audio z wejściem overlayu, zachowując stałe `4000 ms`
   dla prezentacji.
6. Przy następnym Secret Path anulować poprzedni timer, głos i ducking.
7. Dodać w Ustawieniach przełącznik, suwak i neutralny odsłuch testowy.
8. Zachować pełny efekt wizualny, gdy audio jest wyłączone lub niedostępne.

## Idempotencja

```text
event_id = secret-path:<target_id>:<local_sequence>
```

`local_sequence` zwiększa się dla świadomego ponownego uruchomienia show. Retry
tego samego wywołania nie może grać podwójnie.

## Testy

* dokładnie sześć par `scene_id`/`sound_event` bez duplikatów;
* obraz, tekst i audio zawsze pochodzą z jednego rekordu;
* brak dźwięku przed pozytywnym wynikiem ustawienia celu;
* negatywny wynik aim-target nie uruchamia show ani SFX;
* show kończy się po 4 s niezależnie od długości i wyniku audio;
* kolejne show nie pozostawia starego głosu ani duckingu;
* test z mapą w iframe, desktopem, mobile i wyłączonym autoplay;
* ustawienia SFX nie zmieniają ustawień radia.

## Poza zakresem

Dźwięk kliknięcia zwykłej pozycji menu, dźwięki narzędzi, capture i zmiana
gameplayowej przewagi Secret Path. Skrót pozostaje przewagą interfejsową.

## DoD

Każda scena ma własny, zgodny semantycznie sample. Dźwięk uruchamia się tylko po
udanym Secret Path, radio wraca do poprzedniego stanu, a brak audio nie wpływa na
kanoniczne ustawienie celu.

---

# Sprint 130.8.9.SFX.3 — autorytatywny capture

## Cel

Dodać dźwięki przejęcia bez wiązania ich z lokalnymi kropkami, paskiem postępu
ani optymistyczną animacją.

## Zdarzenia

Minimalny katalog:

```text
capture.target
capture.conflict_pillar
capture.conflict_resolved
```

Rozszerzenie o `capture.conflict_inner` jest dozwolone tylko wtedy, gdy backend
lub kanoniczna delta jednoznacznie rozróżnia tę rolę. Frontend nie zgaduje roli z
ikony albo położenia markera.

## Zakres

1. Emitować SFX dopiero z potwierdzonego `captured_target` albo kanonicznej delty
   `map.target_captured`.
2. Wyznaczyć jeden punkt odpowiedzialny za odtworzenie, aby odpowiedź aplikacji
   i późniejsza delta nie grały dwa razy.
3. Użyć stabilnego identyfikatora:

   ```text
   target-captured:<target_id>:<capture_version>
   ```

4. Dodać wariant filaru oraz rozwiązania konfliktu bez zmian w domenie konfliktu.
5. Recovery mapy i ponowne otwarcie iframe traktować jako synchronizację stanu,
   nie nowe zdarzenie audio.
6. Capture o wyższym priorytecie może przerwać efekt UI, ale nie alarm krytyczny.

## Strażniki

* cztery kropki i `100%` nie są źródłem capture SFX;
* worker nie odtwarza dźwięku i nie zapisuje klientowego stanu audio;
* nie dodajemy rebuildów do requestu mapy;
* przejęcie naprawione przez worker nie może wywołać serii historycznych efektów;
* SFX nie wpływa na CAS, receipt, właściciela ani kolejkę terytoriów.

## Testy

* jeden capture daje jeden dźwięk mimo odpowiedzi i delty;
* retry/replay tego samego `capture_version` pozostaje cichy;
* nowa wersja przejęcia tego samego obiektu może zagrać ponownie;
* recovery i pełny snapshot pozostają ciche;
* zwykły cel, filar i rozwiązanie konfliktu wybierają właściwe eventy;
* brak wersji używa bezpiecznego fallbacku dedupe, a nie losowego czasu klienta.

## DoD

Dźwięk zawsze opisuje zatwierdzony wynik. Nie może wystąpić sytuacja, w której
gracz słyszy przejęcie, a backend odrzucił operację albo cel nadal należy do
poprzedniego właściciela.

---

# Sprint 130.8.9.SFX.4 — Cyberner i komunikaty systemowe

Status: zaimplementowany lokalnie, oczekuje na test assetów i sesji produkcyjnej.

Korekta po testach SFX.3: `max_duration_ms` jest minimalnym watchdogiem
awaryjnym, a nie punktem ucięcia prawidłowego pliku. Po odczytaniu metadanych
silnik pozwala MP3 dojść do naturalnego `ended` (długość assetu + 750 ms),
zachowując twardy bezpiecznik 30 s dla uszkodzonego lub zapętlonego audio.

## Cel

Podłączyć wiadomości i istotne komunikaty bez odgrywania backlogu oraz bez
tworzenia dźwiękowego spamu przez polling, recovery lub wiele otwartych okien.

## Zdarzenia

```text
cyberner.message_incoming
cyberner.message_sent
system.warning
system.critical
```

`system.info` pozostaje domyślnie cichy. Można go dopuścić później dla małej,
jawnej allowlisty komunikatów.

## Zakres

1. Oprzeć incoming na kanonicznym `cyberner.message_created` po zapisie.
2. Odtwarzać incoming tylko dla wiadomości od innego użytkownika widocznej w
   kanale aktualnego odbiorcy.
3. Własne wysłanie może użyć osobnego, cichego eventu `message_sent`.
4. Pierwsza hydratacja, migracyjna historia, reconnect i nadrabianie kursora są
   ciche.
5. Deduplikować po `cyberner:<message_id>` wspólnie dla wszystkich okien.
6. Dla komunikatów systemowych wymagać stabilnego `message_id` i klasy
   `warning` albo `critical`.
7. Ustawić osobne cooldowny kanałowe i globalny antyspam.
8. Ustalić priorytet: `critical` > capture > lore > incoming > sent/UI.

## Testy

* nowa obca wiadomość gra raz;
* własna wiadomość nie używa incoming;
* WORLD, CLAN i rozmowa prywatna nie duplikują tego samego `message_id`;
* otwarcie kanału z historią jest ciche;
* reconnect i drugi poller nie odgrywają wiadomości ponownie;
* seria warningów respektuje cooldown;
* critical może przerwać niższy priorytet i prawidłowo zwalnia radio;
* wyciszony Cyberner lub zamknięte okno nie naruszają kursora wiadomości.

## Poza zakresem

Synteza mowy, dźwięk dla każdej wiadomości systemowej, dźwięki pisania i
indywidualne melodie użytkowników lub klanów.

## DoD

Kanały Cybernera pozostają niezależne od audio, a odłączenie całego `GameSfx`
nie zmienia dostarczania, read cursorów ani unread count. W długiej sesji każda
nowa wiadomość może zagrać najwyżej raz.

## Zrealizowany kontrakt runtime

* `cyberner.message_incoming` jest emitowany tylko podczas live processingu delty
  `cyberner.message_created`; bootstrap, recovery i pierwszy poll po utracie
  połączenia są ciche;
* cichy `cyberner.message_sent` startuje dopiero z odpowiedzi zawierającej
  kanoniczne `message_id` po zapisie;
* oba warianty używają globalnego klucza `cyberner:<message_id>`, niezależnego od
  liczby okien Cybernera i reprezentacji kanału;
* `system.warning` i `system.critical` wymagają stabilnego ID ze
  `SystemMessageStore`; `info` pozostaje bez dźwięku;
* `system.critical` może przerwać aktywne głosy o niższym priorytecie, a każdy
  przerwany głos zwalnia własny uchwyt duckingu radia;
* audio nie odczytuje ani nie zapisuje cursorów, unread count ani historii
  kanałów.

---

# Sprint 130.8.9.SFX.5 — OFS i polish

## Cel

Domknąć wspólny język dźwiękowy aplikacji, wyważyć assety i potwierdzić, że
system zachowuje się poprawnie w pełnej, wielookiennej sesji CHAOS.

## Semantyczne hooki OFS

Minimalny katalog:

```text
ofs.intro
ofs.choice_available
ofs.choice_confirmed
ofs.progress_checkpoint
ofs.success
ofs.failure
ofs.runtime_warning
```

Renderer sceny wybiera moment emisji. Content autora może wskazać wyłącznie
allowlistowany `event_key`; nie przekazuje URL, głośności, priorytetu ani czasu.

## Zakres

1. Dodać semantyczne hooki do wspólnego lifecycle OFS bez osobnych odtwarzaczy w
   oknach aplikacji.
2. Nie odtwarzać eventu na każdą linię provisionala ani każdą zmianę progress
   bara. `progress_checkpoint` ma ograniczoną liczbę emisji na sesję.
3. Deduplikować po `ofs:<session_id>:<phase>:<sequence>`.
4. Zapewnić zgodność `button_choice`, `progress_random`, `terminal` i `window`.
5. Sprawdzić kilka równoległych aplikacji: wszystkie używają jednego miksera i
   wspólnych limitów.
6. Znormalizować odczuwalną głośność, początki, końce i długości wszystkich
   assetów dodanych w SFX.1–SFX.5.
7. Dopracować ducking radia, przejścia między magistralami i redukcję ruchu/
   dźwięku na urządzeniach mobilnych.
8. Dodać czytelne, domyślnie wyłączone logi diagnostyczne.
9. Uzupełnić dokumentację dodawania nowego eventu i checklistę assetu.

## Checklista nowego assetu

1. Istnieje semantyczny event, a nie nazwa konkretnego przycisku DOM.
2. Zdarzenie ma kanoniczny moment emisji i stabilny `event_id`.
3. Plik jest lokalny i wpisany do manifestu.
4. Głośność, peak, początkowa cisza i fade zostały sprawdzone.
5. Event ma bus, priority, cooldown, limit czasu i politykę duckingu.
6. Brak pliku i mute zostały przetestowane.
7. Recovery, retry i dwa okna nie powodują replayu.

## Macierz regresji

* desktop i mobile;
* Chrome z autoplay unlocked i blocked;
* radio: wyłączone, grające, wyciszone i ze zmienioną głośnością;
* jedna i kilka aplikacji OFS;
* mapa zamknięta, otwarta i przeładowana;
* Secret Path uruchomiony kilka razy pod rząd;
* capture zwykły, filar i konflikt;
* Cyberner: hydration, incoming, sent i reconnect;
* warning/critical podczas lore, capture i OFS;
* długa sesja bez wzrostu liczby aktywnych głosów, timerów i uchwytów duckingu.

## Poza zakresem

Muzyka adaptacyjna, przestrzenny dźwięk mapy, WebAudio DSP, synteza mowy,
serwerowa synchronizacja preferencji oraz pełny redesign Ghost Radio.

## DoD

Wszystkie integracje używają jednego `GameSfx`, a żaden feature nie odtwarza
pliku bezpośrednio. Głośność jest spójna, radio zawsze odzyskuje stan, backlog i
recovery pozostają ciche, wiele okien respektuje wspólne limity, a wyłączenie lub
awaria audio nie zmienia żadnego wyniku gameplayowego.

---

## 4. Kolejność wdrażania i bramki

Sprinty są sekwencyjne. Nie rozpoczynamy kolejnego bez spełnienia bramki
poprzedniego:

```text
SFX.1 silnik bez gameplayu
  -> SFX.2 sześć scen Secret Path
  -> SFX.3 autorytatywny capture
  -> SFX.4 Cyberner i system
  -> SFX.5 OFS oraz pełna regresja
```

Każdy sprint kończy się co najmniej:

```text
node --check <zmienione pliki JS>
python -m unittest <testy celowane>
git diff --check
```

Zmiany nie wymagają restartu workera terytoriów, dopóki sprint nie modyfikuje
jego kodu. W tych pięciu sprintach taka modyfikacja nie jest planowana.
