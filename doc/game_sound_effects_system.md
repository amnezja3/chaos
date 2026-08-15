# CHAOS Game Sound Effects System

Status: production architecture draft po audycie kodu 2026-08-15.

Pierwszym wdrożeniem systemu jest czterosekundowe show `Secret Path`, uruchamiane
po lekkim oznaczeniu celu przez kliknięcie nazwy w menu hakowania. Dokument
opisuje przede wszystkim sześć scen backdoora, ale kontrakt od początku obejmuje
również przejęcie celu, wiadomości Cybernera i zdarzenia systemowe.

## 1. Wyniki audytu aktualnego kodu

### 1.1. Nie istnieje wspólny silnik efektów dźwiękowych

Projekt ma odtwarzacz Ghost Hack Radio w `static/js/ghost_radio.js`, oparty na
jednym trwałym obiekcie HTML5 `Audio`. Radio ma własny stan odtwarzania,
głośności i wyciszenia oraz przeżywa zamknięcie okna aplikacji. Jest to dobry
wzorzec właściciela audio, ale nie jest mikserem SFX.

Nie ma obecnie:

- rejestru zdarzeń dźwiękowych,
- osobnej głośności efektów,
- limitu równoległych głosów,
- priorytetów i cooldownów,
- deduplikacji dźwięku po `event_id`,
- polityki współpracy efektów z radiem,
- wspólnego preloadu krótkich sampli.

### 1.2. Mapa i pulpit są rozdzielone iframe'em

Mapa jest otwierana jako iframe przez `static/js/terminal.js`. `Secret Path`
powstaje w `templates/map_template.html`, natomiast Ghost Radio i główny runtime
pulpitu żyją w oknie nadrzędnym ładowanym przez `templates/linux.html`.

Silnik SFX musi mieć jednego właściciela w oknie desktopu. Mapa nie powinna
tworzyć własnego odtwarzacza. Powinna zgłaszać semantyczne zdarzenie, np.
`secret_path.scene_03`, do `window.parent.GameSfx`.

### 1.3. Polityka autoplay jest realnym ryzykiem

Kliknięcie nazwy celu jest gestem użytkownika, ale show uruchamia się dopiero po
asynchronicznej odpowiedzi `/api/map/aim-target`. Bez wcześniejszego odblokowania
audio przeglądarka może odrzucić `play()` wywołane po zakończeniu requestu.

Silnik powinien uzbroić audio przy pierwszym `pointerdown` lub `keydown` w
desktopie i w otwartej mapie. Odblokowanie nie odtwarza słyszalnego dźwięku;
przygotowuje `AudioContext` albo cichy bufor do późniejszego użycia.

### 1.4. Istnieją już właściwe hooki przyszłych efektów

- wynik aplikacji zawiera `captured_target`, a frontend publikuje go do otwartych
  map;
- delta feed obsługuje `map.target_captured`;
- Cyberner publikuje kanoniczne `cyberner.message_created` dopiero po zapisie
  wiadomości;
- system ma lokalne komunikaty i delty stanu, z których można wybierać tylko
  zdarzenia faktycznie potwierdzone przez backend.

Dźwięk nie może być emitowany od kliknięcia, jeżeli ma oznaczać wynik gameplayu.
`target_captured` ma grać po autorytatywnym capture, a wiadomość Cybernera po
kanonicznym `message_created`. Secret Path jest wyjątkiem prezentacyjnym: jego
dźwięk oznacza udane otwarcie skrótu, nie udane zhakowanie celu.

## 2. Decyzja architektoniczna

Tworzymy jeden klientowy moduł:

```text
static/js/game_sfx.js
window.GameSfx
```

Moduł jest ładowany przed `ghost_radio.js` i `terminal.js` w głównym dokumencie
desktopu. Nie wykonuje requestów gameplayowych i nie jest zależny od Flaska poza
serwowaniem statycznego manifestu i plików audio.

Mapa oraz pozostałe moduły wysyłają wyłącznie klucz zdarzenia i bezpieczny
kontekst:

```js
window.parent.GameSfx.play("secret_path.scene_03", {
    event_id: "secret-path:<target-id>:<sequence>",
    source: "map",
    duration_ms: 4000
});
```

Ścieżka pliku nie może pochodzić z payloadu gameplayowego. Klucz jest
rozwiązywany przez lokalną allowlistę manifestu.

## 3. Publiczny kontrakt `GameSfx`

Minimalne API:

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

`play()` zwraca uchwyt z `stop()` i Promise stanu startu. Odrzucony autoplay lub
brak pliku nie może przerywać show wizualnego ani rzucać nieobsłużonego błędu.

Wynik startu:

```js
{
  ok: true,
  event_key: "secret_path.scene_03",
  voice_id: "sfx-...",
  reason: null
}
```

Kontrolowane pominięcia zwracają `ok: false` oraz `reason`, np. `muted`,
`cooldown`, `duplicate`, `autoplay_blocked`, `missing_asset`.

## 4. Manifest i katalog plików

Proponowany układ:

```text
static/audio/sfx/
├── manifest.v1.json
├── secret_path/
│   ├── 01_target_repaired.mp3
│   ├── 02_route_open.mp3
│   ├── 03_skill_verified.mp3
│   ├── 04_acceleration.mp3
│   ├── 05_lore_discovered.mp3
│   └── 06_chaos_protocol.mp3
├── capture/
├── cyberner/
└── system/
```

Manifest:

```json
{
  "schema": 1,
  "base_path": "/static/audio/sfx",
  "events": {
    "secret_path.scene_01": {
      "file": "secret_path/01_target_repaired.mp3",
      "bus": "lore",
      "priority": 70,
      "volume": 0.9,
      "max_duration_ms": 4000,
      "cooldown_ms": 500,
      "duck_radio": 0.42
    }
  }
}
```

Na początku wymagany jest MP3. Manifest pozostawia możliwość dodania później
wariantów `ogg`/`webm`, lecz pierwszy sprint nie buduje transkodera.

Wymagania dla sześciu plików:

- długość docelowa 3.6-4.0 s;
- krótki fade-in i fade-out, bez twardego cięcia;
- zbliżona głośność odczuwalna wszystkich próbek;
- brak ciszy dłuższej niż 100 ms na początku;
- pliki bez metadanych lub okładek zwiększających wagę;
- każdy sample samodzielny, bez zależności od poprzedniej sceny.

## 5. Sześć scen Secret Path

Obecne obiekty scen muszą dostać stabilne `scene_id` i `sound_event`. Losowanie
odbywa się raz. Ten sam obiekt steruje tekstem, animacją i dźwiękiem, więc ekran
nie może wylosować sceny 02, a audio sceny 05.

### Scena 01 — Target Repaired

```text
scene_id: target_repaired
sound_event: secret_path.scene_01
```

Brzmienie: uszkodzony sygnał, szybka rekonstrukcja, metaliczne domknięcie tarczy.
Ma komunikować naprawienie kanału celu i gotowość tunelu aplikacji.

### Scena 02 — Route Open

```text
scene_id: route_open
sound_event: secret_path.scene_02
```

Brzmienie: dwa krótkie impulsy nawigacyjne, narastający sweep i otwarcie bramy.
Ma komunikować pominięcie pickera i możliwość wejścia bezpośrednio z terminala.

### Scena 03 — Skill Verified

```text
scene_id: skill_verified
sound_event: secret_path.scene_03
```

Brzmienie: skan biometryczny/operatora, trzy kroki weryfikacji i pozytywny lock.
Ma nagradzać uważne odczytanie interfejsu i odkrycie ukrytej ścieżki.

### Scena 04 — Acceleration

```text
scene_id: acceleration
sound_event: secret_path.scene_04
```

Brzmienie: szybki rytmiczny start, przyspieszający transfer i mocny impuls.
Opisuje skrócenie drogi UI, nie bonus liczbowy do progów ani capture.

### Scena 05 — Lore Discovered

```text
scene_id: lore_discovered
sound_event: secret_path.scene_05
```

Brzmienie: odsłonięcie zaszyfrowanego archiwum, szept danych i krótki akord
odkrycia. Ma komunikować, że znajomość lore daje przewagę informacyjną.

### Scena 06 — CHAOS Protocol 2108

```text
scene_id: chaos_protocol_2108
sound_event: secret_path.scene_06
```

Brzmienie w trzech aktach: tarcza, ostrze, wyładowanie. Ostatni impuls powinien
zgrać się z najmocniejszym glitchem sygnetu i końcem show.

## 6. Synchronizacja czterosekundowego show

`showSecretPathLore()` powinno:

1. wylosować jeden rekord sceny;
2. wstawić tekst i uruchomić animację;
3. wywołać `GameSfx.play(scene.sound_event, ...)`;
4. przy ponownym Secret Path zwiększyć `sequence`, zatrzymać poprzedni głos i
   rozpocząć nową scenę;
5. po 4000 ms schować overlay i łagodnie zatrzymać niedokończony sample.

Audio nie ustala czasu show. Autorytatywny czas prezentacji pozostaje 4000 ms.
Brak lub błąd MP3 pozostawia pełne show wizualne.

## 7. Mikser i współpraca z Ghost Radio

Proponowane magistrale:

| Bus | Przeznaczenie | Głosy | Polityka |
|---|---|---:|---|
| `lore` | Secret Path, odkrycia | 1 | zastępuje poprzedni lore |
| `gameplay` | capture, sukces, porażka | 2 | priorytet i cooldown |
| `message` | Cyberner, poczta | 2 | krótko, bez spamowania |
| `system` | ostrzeżenia runtime | 1 | najwyższy priorytet |
| `ui` | lekkie kliknięcia | 3 | niski priorytet |

Secret Path może ściszyć radio do około 42% bieżącej głośności na czas próbki.
Nie wolno zmieniać zapisanej głośności użytkownika. Ghost Radio powinno dostać
osobny przejściowy mnożnik `duck_gain`, a po zakończeniu SFX wrócić do wartości
sprzed efektu. Nakładające się żądania duckingu wymagają licznika/stacku.

## 8. Ustawienia użytkownika

Pierwszy kontrakt:

```text
chaos_sfx_enabled = 1 | 0
chaos_sfx_volume = 0.0 .. 1.0
```

MVP może przechowywać je w `localStorage`, tak jak autostart radia. Panel
Ustawień powinien dostać:

- przełącznik Efekty gry;
- suwak Głośność efektów;
- przycisk testowy odtwarzający neutralny krótki sample.

Docelowa synchronizacja między urządzeniami może rozszerzyć
`desktop_settings`, ale wymaga zmiany backendowej normalizacji i endpointu.
Nie należy dokładać tego pola ukradkiem, ponieważ obecny backend jawnie
normalizuje dozwolone ustawienia pulpitu.

Wyciszenie SFX nie wycisza radia. Wyciszenie radia nie wycisza SFX.

## 9. Preload, cache i wydajność

- manifest jest pobierany raz po uruchomieniu desktopu;
- sześć backdoorowych próbek może być preloadowane po pierwszej interakcji;
- preload nie blokuje bootu profilu ani mapy;
- kolejne grupy są ładowane leniwie przed pierwszym użyciem;
- błędny asset przechodzi na cooldown diagnostyczny, aby nie generować requestu
  przy każdej delcie;
- jeden sample jest dekodowany raz i współdzielony przez kolejne odtworzenia;
- silnik wystawia liczniki `loaded`, `active_voices`, `blocked`, `failed` tylko do
  diagnostyki konsoli, bez pollingu backendu.

## 10. Deduplikacja i bezpieczeństwo zdarzeń

Każde zdarzenie pochodzące z delty powinno mieć stabilne `event_id`. Silnik
zapamiętuje krótki zbiór ostatnio odtworzonych identyfikatorów. Ponowne
przetworzenie tej samej delty po recovery nie odtwarza dźwięku ponownie.

Przykłady:

```text
target-captured:<target_id>:<capture_version>
cyberner:<message_id>
system:<message_id>
secret-path:<target_id>:<local_sequence>
```

Manifest jest allowlistą. Payload serwera nie może przekazać dowolnego URL,
ścieżki pliku, głośności większej od 1 ani nieograniczonego czasu odtwarzania.

## 11. Następne obszary integracji

### 11.1. Moment zhakowania

Źródło: potwierdzony `captured_target` albo kanoniczna delta
`map.target_captured`. Nie odtwarzać na same cztery kropki ani na lokalną
animację oczekiwania. Inny dźwięk może mieć zwykły obiekt, filar konfliktu i
rozwiązanie całego konfliktu.

### 11.2. Cyberner

Źródło: `cyberner.message_created`. Dźwięk tylko dla nowej wiadomości od innego
użytkownika. Własna wysłana wiadomość może mieć cichy osobny `message.sent`.
Recovery historii i pierwsze otwarcie kanału nie mogą odegrać całego backlogu.

### 11.3. Komunikaty systemowe

Źródło: kanoniczne komunikaty z przypisaną klasą `info`, `warning`, `critical`.
Systemowe efekty mają cooldown i priorytet; powtarzający się polling bez nowego
`message_id` nie może generować dźwięku.

### 11.4. OFS i aplikacje

OFS może później emitować semantyczne `app.choice`, `app.success`, `app.failure`,
ale tylko renderer sceny wybiera moment. Content autora nie dostaje prawa do
podania dowolnego pliku audio; może wskazać wyłącznie dozwolony klucz eventu.

## 12. Telemetria i diagnostyka

Logi developerskie:

```text
[GAME_SFX] play event=secret_path.scene_03 voice=... source=map
[GAME_SFX] skip event=cyberner.message reason=duplicate event_id=...
[GAME_SFX] fail event=... reason=autoplay_blocked
```

Nie logujemy każdego `timeupdate`. Produkcyjny brak dźwięku nie może powodować
500, zatrzymać mapy ani zablokować gameplayu.

## 13. Testy kontraktowe

### Moduł audio

- jeden manifest i allowlista ścieżek;
- clamp głośności do `0..1`;
- mute, cooldown, priority i max voices;
- deduplikacja `event_id`;
- graceful fallback dla `play()` reject i brakującego pliku;
- poprawne zatrzymanie oraz zwolnienie duckingu.

### Secret Path

- dokładnie sześć stabilnych `scene_id` i sześć `sound_event`;
- jedna decyzja losowa steruje obrazem oraz MP3;
- `GameSfx.play()` występuje dopiero po sukcesie `/api/map/aim-target`;
- show trwa 4000 ms niezależnie od stanu audio;
- ponowne odpalenie nie pozostawia dwóch głosów ani starego timera;
- brak `GameSfx` nie psuje oznaczenia celu.

### Integracje przyszłe

- capture gra raz po autorytatywnym wyniku;
- recovery mapy nie powtarza capture SFX;
- backlog Cybernera pozostaje cichy;
- nowa obca wiadomość gra raz;
- własna wiadomość nie używa efektu incoming.

## 14. Proponowane sprinty

### Sprint SFX.1 — fundament

- `game_sfx.js`, manifest v1, unlock autoplay, preload i ustawienia lokalne;
- magistrale, dedupe, cooldown, voice limit;
- podstawowy kontrakt duckingu Ghost Radio;
- testy modułu bez podpinania gameplayu.

### Sprint SFX.2 — sześć scen Secret Path

- stabilne identyfikatory scen;
- sześć dostarczonych MP3;
- wspólne losowanie obrazu i audio;
- synchronizacja 4 s, restart sceny i fallback bez audio;
- kontrolki SFX w Ustawieniach.

### Sprint SFX.3 — capture

- zwykły capture, filar, konflikt resolved;
- dedupe po target/version;
- weryfikacja z worker recovery i delta feed.

### Sprint SFX.4 — Cyberner i system

- incoming, sent, warning i critical;
- cisza przy hydratacji/backlogu;
- priorytety i antyspam.

### Sprint SFX.5 — OFS i polish

- semantyczne hooki aplikacji;
- normalizacja głośności assetów;
- testy mobile, wielu okien, radia i długiej sesji.

## 15. Kryterium gotowości pierwszego wdrożenia

Backdoor jest gotowy, gdy każda z sześciu scen ma własny MP3, obraz i dźwięk są
losowane jako jeden rekord, show pozostaje dokładnie czterosekundowe, radio
wraca do poprzedniej głośności, a zablokowane audio nie wpływa na ustawienie
celu. Dopiero po spełnieniu tego kontraktu system powinien zostać rozszerzony na
capture i Cybernera.
