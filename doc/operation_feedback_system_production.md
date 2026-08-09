# Operation Feedback System — artefakt produkcyjny

Status: `IMPLEMENTATION CONTRACT — OFS-SPIKE-01 GO`

Wersja kontraktu: `1.0.0`

Data decyzji: `2026-08-09`

Stan implementacji: sprinty `130.8.6.1–130.8.6.3` domknęły domyślnie wyłączony
spike `scan_ports`. Potwierdzono choices, lokalny presentation state, content
autora, trzy profile przebiegu i payload priority. Wynik `GO` pozwala rozpocząć
generalizację 6.4; nie jest to produkcyjny cutover.

Raport spike'a: `doc/operation_feedback_spike_01_results.md`.

Dokument źródłowy: `doc/Operation_Feedback_System.md` — materiał burzowy,
niebędący kontraktem implementacyjnym.

## 1. Decyzja

Operation Feedback System, dalej `OFS`, jest frontendową warstwą prezentującą
czas oczekiwania na autorytatywną odpowiedź backendu dla aplikacji operacyjnych
CHAOS.

OFS:

* uruchamia się równolegle z requestem `/gonna-win`;
* przedstawia operację jako serię krótkich, semantycznie poprawnych scen;
* wykorzystuje treść i charakter aplikacji przygotowane przez jej twórcę;
* kończy się natychmiast po otrzymaniu prawdziwego payloadu albo błędu;
* nie oblicza gameplayu i nie zapisuje stanu;
* nie zastępuje istniejących interfejsów aplikacji;
* nie obejmuje aktywnego czasu operacji pokazywanego w Centrum Operacji;
* nie przejmuje fazy wyboru narzędzia wykonywanej przez `/hack-action`.

Backend pozostaje jedynym źródłem prawdy.

## 2. Problem produkcyjny

Obecny frontend posiada kilka niezależnych mechanizmów oczekiwania:

* spinner `Poczekaj chwilę...`;
* globalny `APP_WAIT_LOG_MESSAGES`;
* `startAppWaitLog()` losujący komunikaty bez kontekstu operacji;
* sztuczny pasek `progressbar_random`;
* osobne oczekiwanie w `window`, `terminal` i `button_choices`;
* mapowy spinner `/hack-action`.

Globalna pula może podczas skanowania portów wyświetlać narrację o portfelu,
GhostNetwork, mapie albo workerze. OFS zastępuje wyłącznie oczekiwanie wewnątrz
uruchomionej aplikacji, zachowując działające requesty i wynik końcowy.

## 3. Zakres wersji 1.0

Obsługiwane `action_key`:

1. `scan_ports`
2. `exploit`
3. `sniff`
4. `trace`
5. `trace_gps`
6. `trace_device`
7. `mic_sniff`
8. `atm_logs`
9. `install_sniffer`
10. `camera_stream`
11. `camera_shutdown`
12. `car_hack`

Pierwszy cutover produkcyjny obejmuje tylko `scan_ports`. Pozostałe profile są
włączane osobnymi flagami po walidacji wspólnego silnika.

Poza zakresem 1.0 pozostają:

* decyzje narracyjne zmieniające gameplay;
* komunikacja zwrotna wyborów narracyjnych do backendu;
* zastępowanie Centrum Operacji;
* prognozowanie wyniku albo czasu zakończenia backendu;
* przebudowa kontraktu aplikacji i AppForge;
* zmiana `/hack-action`, `/gonna-win`, receiptów lub idempotencji.

## 4. Granice integracji

### 4.1. `/hack-action`

Faza mapowa nadal:

* wysyła wybór akcji i celu;
* pokazuje krótki spinner na mapie;
* odbiera listę pasujących aplikacji;
* kończy spinner po odpowiedzi endpointu.

OFS nie uruchamia się w tej fazie.

### 4.2. `/gonna-win`

OFS startuje bezpośrednio przed istniejącym requestem `/gonna-win` i działa w
viewporcie aplikacji. Request nie czeka na boot, scenę ani decyzję narracyjną.

Integracja korzysta z jednego wrappera wokół istniejących punktów wysłania:

* `terminal` owija obecny natychmiastowy `notifyGonnaWin()`;
* `window` i `button_choices` startują OFS dopiero po wyborze gameplayowym;
* `progressbar_random` przy aktywnym OFS nie opóźnia requestu fikcyjnymi krokami;
* flag-off i fallback zachowują dotychczasowy runtime.

Wrapper nie tworzy drugiego requestu i zachowuje istniejące flow, receipt,
expected target, kolejkę oraz idempotencję.

Po odpowiedzi:

1. sesja anuluje aktywną scenę, countdown i timery;
2. istniejący kod natychmiast publikuje prawdziwy wynik i wykonuje aktualizacje
   toolbara, celu, operacji oraz auto-close;
3. renderer może równolegle pokazać krótkie `completion` albo `failure`;
4. completion nie opóźnia handlera payloadu i może zostać przerwane cleanupem.

### 4.3. Aktywna operacja

Jeżeli `/gonna-win` utworzy operację trwającą np. godzinę, OFS kończy się po
potwierdzeniu utworzenia. Dalszy czas pokazuje wyłącznie Centrum Operacji.

## 5. Istniejący interface a presentation mode

`interface` pozostaje kontraktem aplikacji:

* `window`
* `terminal`
* `button_choices`
* `progressbar_random`

OFS dodaje niezależny `presentation_mode`:

* `terminal`
* `button_choice`
* `window`

Renderer korzysta z istniejącego viewportu. Nie tworzy nowego okna.

`progressbar_random` jest w cutoverze mapowany na prezentację `window`. Pasek
procentowy nie jest wyświetlany, jeżeli backend nie dostarcza prawdziwego
postępu.

## 6. Tożsamość sesji

Stabilny klucz lokalnej sesji:

```text
flow_id + launch_receipt + app_id + request_sequence
```

Sesja otrzymuje również bezpieczną projekcję uruchomionej aplikacji: nazwę,
opis, `interface`, wybrany poziom oraz content przygotowany przez autora. Content
jest wejściem prezentacji, ale nie częścią tożsamości ani idempotencji requestu.

`security_state` jest niemutowalnym snapshotem lokalnym z
`toolbarProfile.aimed_target.security`, pobranym przy starcie sesji wyłącznie
po potwierdzeniu zgodności aktualnego celu z `expected_target` launch context.
Do sesji trafiają tylko kanoniczne klucze i wartości `true`, `false`, `unknown`.
Brak lub niedopasowanie oznacza `unknown`. Snapshot nie trafia do body
`/gonna-win`, DOM ani telemetry i nie jest odświeżany podczas sesji.

Sesja nie używa nazwy celu, geometrii ani indeksu okna jako identyfikatora.

Jedno okno może posiadać maksymalnie jedną aktywną sesję. Nowy request w tym
samym oknie anuluje poprzednią prezentację, ale nie anuluje requestu backendu,
jeżeli obecny runtime nie przewiduje takiej operacji.

## 7. Model stanu sesji

Dozwolone stany:

```text
idle
starting
running
awaiting_payload
completing
failed
cancelled
disposed
```

Przejścia:

```text
idle -> starting -> running
running -> awaiting_payload -> running
running|awaiting_payload -> completing -> disposed
running|awaiting_payload -> failed -> disposed
starting|running|awaiting_payload -> cancelled -> disposed
```

`disposed` jest terminalny. Po jego osiągnięciu callback nie może zmienić DOM.

## 8. Lifecycle

### Start

Session otrzymuje:

```text
session_id
action_key
presentation_mode
app_id
flow_id
launch_receipt
target_snapshot
security_state
renderer_host
```

Następnie:

1. waliduje profil;
2. tworzy kontroler anulowania;
3. zapisuje stan `starting`;
4. uruchamia request bez opóźnienia;
5. renderuje pierwszą scenę;
6. przechodzi do `running`.

### Payload

Payload ma zawsze pierwszeństwo. Session:

* kończy bieżące oczekiwania;
* blokuje lokalne przyciski narracyjne;
* czyści interwały;
* nie interpretuje `success` poza wyborem completion/failure;
* przekazuje oryginalny payload istniejącemu handlerowi.

### Zamknięcie okna

Zamknięcie aplikacji wywołuje `dispose(reason="window_closed")`. Żaden timer,
Promise wyboru ani callback renderera nie może pozostać aktywny.

### Równoległe aplikacje

Każde okno ma własną sesję. Anti-repeat jest współdzielony tylko jako mała
pamięć historii i nie przechowuje payloadów ani danych celu.

## 9. Bezpieczeństwo semantyczne

Zdarzenia dzielą się na dwie klasy.

### Narracyjne

Mogą być dobierane losowo w granicach profilu:

* probe;
* enumerate;
* bypass attempt;
* alternate route;
* verification pending;
* channel selection;
* temporary mask;
* decoding;
* correlation.

Nie potwierdzają zmiany stanu.

### Transportowe

Wymagają rzeczywistego sygnału runtime:

* `response_delayed` — przekroczony próg czasu;
* `http_error` — odpowiedź HTTP non-2xx;
* `invalid_payload` — odpowiedź niezgodna z kontraktem;
* `network_error` — odrzucony fetch;
* `aborted` — rzeczywisty abort;
* `offline` — `navigator.onLine === false` albo potwierdzony błąd sieci;
* `retry` — wyłącznie gdy request faktycznie ponowiono.

Nie wolno losować fałszywego `connection lost`, `timeout`, `packet loss`,
`worker restart` ani `reconnect`.

## 10. Zabezpieczenia

Kanoniczne klucze:

```text
stealth_mode
scan_detection
exploit_protection
vpn_enabled
browser_protection
os_hardening
log_guardian
process_monitor
firewall
log_integrity
network_anomaly_detection
spoofing_protection
activity_monitor
player_tracking
system_visibility
firewall_core
kernel_guard
system_integrity_check
heap_protection
memory_lock
background_injection
memory_guard
vpn_blocker
```

OFS korzysta wyłącznie z bezpiecznego snapshotu znanego frontendowi. Brak
klucza oznacza `unknown`, nie `disabled`.

Dozwolone określenia przed payloadem:

```text
detected
probe started
bypass attempt
verification pending
route selected
response observed
```

Zabronione bez potwierdzenia backendu:

```text
disabled
captured
owned
security removed
target compromised
operation successful
```

## 11. Mapowanie operacji

| action_key | presentation | główne zabezpieczenia | dozwolone interakcje |
|---|---|---|---|
| scan_ports | button_choice | scan_detection, firewall, firewall_core, system_visibility, network_anomaly_detection, vpn_blocker | probe, detect, enumerate, bypass, route |
| exploit | terminal | exploit_protection, os_hardening, kernel_guard, system_integrity_check, heap_protection, memory_lock, background_injection, memory_guard | probe, bypass, inject, allocate, execute, verify |
| sniff | terminal | vpn_enabled, network_anomaly_detection, spoofing_protection, activity_monitor, system_visibility | intercept, capture, decode, filter, mask |
| trace | window | stealth_mode, player_tracking, activity_monitor, system_visibility, spoofing_protection | locate, correlate, follow, resolve, reconstruct |
| trace_gps | window | player_tracking, system_visibility, spoofing_protection, activity_monitor | locate, triangulate, correlate, resolve |
| trace_device | window | player_tracking, system_visibility, activity_monitor, spoofing_protection | identify, fingerprint, correlate, resolve |
| mic_sniff | terminal | browser_protection, activity_monitor, process_monitor, system_visibility | capture, open_channel, decode, filter |
| atm_logs | terminal | log_guardian, log_integrity, system_integrity_check, activity_monitor | read, extract, verify, reconstruct |
| install_sniffer | button_choice | process_monitor, background_injection, memory_guard, memory_lock | inject, persist, hide, attach, verify |
| camera_stream | window | firewall, firewall_core, system_visibility, activity_monitor | connect, negotiate, decode, stream |
| camera_shutdown | button_choice | system_integrity_check, process_monitor, os_hardening, kernel_guard | interrupt, override, terminate, verify |
| car_hack | button_choice | exploit_protection, system_integrity_check, kernel_guard, memory_guard, process_monitor | connect, inject, override, control, verify |

Tabela określa katalog wysokiego poziomu. Implementacyjny profil operacji nie
może jednak przechowywać zabezpieczeń i interakcji jako dwóch niezależnych list.
Musi definiować jawną macierz `security -> interactions`, na przykład:

```json
{
  "security": {
    "scan_detection": ["probe", "detect"],
    "firewall": ["probe", "bypass", "route"],
    "firewall_core": ["probe", "enumerate"],
    "network_anomaly_detection": ["detect", "probe"]
  }
}
```

Scheduler wybiera najpierw zabezpieczenie, a następnie interakcję wyłącznie z
listy przypisanej do tego zabezpieczenia. Nie istnieje domyślny iloczyn
`security_keys × interaction_types`. Dzięki temu `scan_detection + route` albo
`firewall + detect` nie powstanie, jeśli profil operacji nie zezwala na taką
parę.

## 12. Wybory narracyjne

Wybór OFS ma kontrakt:

```json
{
  "choice_id": "feedback.scan_ports.visibility",
  "effect_scope": "presentation",
  "prompt_key": "scan_visibility",
  "options": [
    {"value": "masked", "label_key": "mask"},
    {"value": "continue", "label_key": "continue"}
  ],
  "timeout_ms": 8000,
  "default_value": "continue"
}
```

Zasady:

* nie używa backendowego `choice_id`;
* nie wywołuje `/gonna-win`;
* nie wpływa na receipt ani idempotencję;
* timeout zawsze wybiera wartość domyślną;
* payload natychmiast przerywa countdown;
* wybór wpływa tylko na kolejne sceny tej sesji;
* wybór może zapisać wyłącznie zadeklarowaną wartość w lokalnym
  `presentation_state`.

Prefix `feedback.` jest obowiązkowy.

Przykładowy stan po wybraniu `MASKUJ`:

```json
{
  "presentation_state": {
    "scan_mode": "masked"
  }
}
```

Kolejne sceny mogą filtrować warianty tekstu po `scan_mode=masked`, np.
`reducing probe interval`, `masked sequence prepared` albo
`low visibility probe active`. Stan:

* istnieje wyłącznie w pamięci sesji OFS;
* nie trafia do body `/gonna-win`, telemetry ani trwałego storage;
* nie wpływa na wynik, czas ani koszt gameplayowy;
* znika przy `dispose`;
* musi mieć klucze i wartości zdefiniowane w profilu wyboru.

## 13. Profile czasu

Scheduler nie zna procentu wykonania. Operuje progami czasu od startu requestu:

| profil | orientacyjny zakres | zachowanie |
|---|---:|---|
| instant | 0–4 s | boot/probe, bez obowiązkowego wyboru |
| short | 4–15 s | 1–2 sceny, najwyżej jeden wybór |
| medium | 15–40 s | security/processing/verification |
| long | 40–90 s | więcej scen, prawdziwe response_delayed |
| very_long | 90 s+ | extended_wait bez fałszywej awarii |

Profil jest adaptacyjny. Session nie deklaruje z góry, ile potrwa backend.

## 14. Scheduler

Scheduler układa historię z klocków i ograniczeń, a nie z gotowego drzewa.

Kolejność wyboru:

```text
operation profile
-> dozwolona rodzina scen
-> content uruchomionej aplikacji zgodny z rolą sceny
-> security znane i dozwolone dla operacji
-> interaction type dozwolony dla wybranego security
-> warunki lokalnego presentation_state
-> wariant treści
-> timing
```

Inwarianty:

* brak dwóch identycznych scen z rzędu, jeśli istnieje alternatywa;
* brak dwóch identycznych komunikatów z rzędu;
* content autora ma pierwszeństwo jako głos aplikacji, jeżeli jest zgodny z rolą
  sceny i regułami bezpieczeństwa semantycznego;
* security event używa wyłącznie pary `security + interaction` jawnie
  dozwolonej przez profil operacji;
* wariant zależny od `presentation_state` nie może zostać wybrany bez
  spełnienia jego warunku;
* scena nie może przekroczyć limitu linii renderera;
* scheduler sprawdza anulowanie przed i po każdym await;
* po payloadzie nie powstaje nowa scena;
* `extended_wait` może działać bezterminowo, ale z ograniczonym rytmem.

## 15. Renderery

### Terminal

* 3–6 widocznych linii;
* `replace`, `clear`, `fade`, `append_short`;
* brak nieskończonego scrolla;
* brak wyborów narracyjnych.

### Button choice

* 2–5 linii kontekstu;
* jedno aktywne pytanie;
* countdown i wartość domyślna;
* payload blokuje przyciski przed przejściem do completion.

### Window

* nagłówek operacji pozostaje stabilny;
* zmienne pola: etap, kanał, źródła, aktywność, status;
* brak fałszywego procentu;
* renderer aktualizuje istniejące elementy zamiast dokładać log bez końca.

Każdy renderer respektuje `prefers-reduced-motion`. W tym trybie wyłącza fade,
pulsowanie i szybkie zmiany, ale zachowuje informacje tekstowe.

## 16. Kontrakt danych

Docelowy plik danych:

```text
static/data/operation_feedback.v1.json
```

Najwyższy poziom:

```json
{
  "schema_version": "1.0.0",
  "content_version": "2026.08.09.1",
  "defaults": {},
  "duration_profiles": {},
  "scene_library": {},
  "security_library": {},
  "transport_library": {},
  "choice_library": {},
  "completion_library": {},
  "failure_library": {},
  "operations": {}
}
```

### 16.1. Odpowiedzialność bibliotek

Warstwy danych mają rozłączne role:

* `scene_library` opisuje dramaturgię i układ sceny: liczbę linii, kolejność
  typów treści, pauzy, przejścia i limity renderera;
* `security_library` dostarcza techniczne warianty treści pogrupowane według
  zabezpieczenia i rodzaju interakcji;
* `operations` określa, których scen oraz których dokładnych par
  `security + interaction` wolno użyć w danej operacji;
* `transport_library` zawiera wyłącznie komunikaty wyzwalane prawdziwym stanem
  transportu;
* `choice_library` definiuje lokalne wybory i dozwolone mutacje
  `presentation_state`;
* `completion_library` oraz `failure_library` opisują wyłącznie prezentację
  potwierdzonego wyniku.
* content uruchomionej aplikacji nadaje prezentacji jej nazwę, styl i teksty
  przygotowane przez autora, ale podlega profilowi operacji i walidacji OFS.

`scene_library` nie zawiera wiedzy o firewallu, skanowaniu ani konkretnym celu.
Przykład:

```json
{
  "security_contact": {
    "sequence": ["operation", "security", "security", "transition"],
    "min_lines": 3,
    "max_lines": 5,
    "pause_ms": [350, 900],
    "transition": "replace"
  }
}
```

`security_library` nie ustala kolejności ekranu. Dostarcza techniczne wypowiedzi
dla konkretnej pary:

```json
{
  "firewall": {
    "interactions": {
      "probe": [
        {"text_key": "firewall.probe.signature"},
        {"text_key": "firewall.probe.ruleset"}
      ],
      "bypass": [
        {"text_key": "firewall.bypass.alternate_route"}
      ],
      "route": [
        {
          "text_key": "firewall.route.masked",
          "when": {"presentation_state.scan_mode": "masked"}
        }
      ]
    }
  }
}
```

W ten sposób dramaturgia odpowiada na pytanie „jak pokazać scenę”, biblioteka
zabezpieczeń — „co technicznie może się wydarzyć”, a profil operacji — „których
połączeń wolno użyć”.

### 16.2. Content aplikacji jako czwarta warstwa

OFS nie może zastąpić autorskiej treści aplikacji jednym globalnym słownikiem.
Globalne biblioteki zapewniają poprawność i fallback, natomiast konkretna
aplikacja powinna zachować głos nadany jej przez twórcę.

Aktualny runtime przechowuje ten content w `levels`:

| interface | istniejący content autora | wykorzystanie w OFS |
|---|---|---|
| `window` | `title`, `list`, `buttons` | tytuł i linie operacyjne; przyciski pozostają wyborami gameplayowymi |
| `terminal` | `command`, `logs` | komenda startowa i autorskie linie terminala |
| `button_choices` | `title`, `text`, `options` | tytuł i opis; options pozostają wyborami gameplayowymi |
| `progressbar_random` | `title`, `steps`, `result_success`, `result_failure` | tytuł, kandydaci na sceny oraz komunikat końcowy po prawdziwym payloadzie |

Istniejące `buttons` i `options` nie mogą zostać automatycznie zamienione na
wybory narracyjne OFS. Ich identyfikatory i efekty należą do obecnego kontraktu
`/gonna-win`. Wybory prezentacyjne zawsze pochodzą z `choice_library`, mają
prefix `feedback.` i osobny `presentation_state`.

#### Projekcja legacy

Dopóki kreatory nie zapisują strukturalnego contentu OFS, adapter może
wykorzystać istniejące `levels` według bezpiecznych reguł:

* `title`, `text`, `description` i `command` zachowują identyfikację aplikacji;
* `list`, `logs` i `steps` mogą wypełniać wyłącznie ogólne sloty `operation` lub
  `transition`;
* `result_success` jest pokazywany dopiero po `success=true`;
* `result_failure` jest pokazywany dopiero po poprawnym payloadzie
  potwierdzającym niepowodzenie gameplayowe; błąd HTTP, sieci albo parsowania
  korzysta z `transport_library` lub `failure_library`;
* tekst legacy nie może sam utworzyć zdarzenia transportowego ani potwierdzić
  przejęcia, wyłączenia zabezpieczenia lub sukcesu przed payloadem;
* wpis odrzucony przez filtr semantyczny jest pomijany, a jego slot wypełnia
  biblioteka globalna.

Legacy projection pozwala od razu wykorzystać pracę autora, ale nie próbuje
zgadywać, z którym zabezpieczeniem lub rodzajem interakcji związana jest
dowolna linia tekstu.

#### Docelowy content strukturalny

Przyszła wersja kreatorów może zapisywać opcjonalne `feedback_content` w rekordzie
aplikacji:

```json
{
  "feedback_content": {
    "schema_version": "1.0.0",
    "tone": "quiet_recon",
    "labels": {
      "session_title": "V-MAP // passive scan"
    },
    "scene_lines": {
      "boot": ["loading local probe profile"],
      "operation": ["enumerating exposed service signatures"],
      "transition": ["switching to verification channel"]
    },
    "security": {
      "firewall": {
        "probe": ["testing ruleset response window"],
        "route": [
          {
            "text": "routing masked probe sequence",
            "when": {"presentation_state.scan_mode": "masked"}
          }
        ]
      }
    },
    "completion": {
      "success": ["service map confirmed"],
      "failure": ["service map rejected"]
    }
  }
}
```

Kolejność źródeł contentu:

```text
zwalidowany feedback_content aplikacji
-> bezpieczna projekcja istniejącego levels
-> globalne biblioteki OFS
```

Zasady dla `feedback_content`:

* nie rozszerza `map_actions`, security ani interakcji dozwolonych przez profil;
* autorskie `security.firewall.route` może być użyte tylko wtedy, gdy profil
  operacji dopuszcza parę `firewall + route`;
* nie zmienia timingów requestu, wyniku, kosztu ani szansy powodzenia;
* nie zawiera HTML ani wykonywalnego kodu;
* może używać wyłącznie jawnej listy bezpiecznych placeholderów;
* completion jest wybierane dopiero z potwierdzonego payloadu;
* brak lub błąd contentu aplikacji uruchamia fallback, a nie blokadę gameplayu.

Kreator powinien pokazywać podgląd minimum trzech wariantów prezentacji oraz
oznaczać, które teksty są autorskie, a które pochodzą z globalnego fallbacku.

### 16.3. Minimalny profil operacji

Minimalny profil operacji:

```json
{
  "action_key": "scan_ports",
  "enabled": false,
  "presentation_modes": ["button_choice"],
  "default_presentation_mode": "button_choice",
  "scene_pools": ["boot", "probe", "security_contact", "verification", "payload_wait"],
  "security": {
    "scan_detection": ["probe", "detect"],
    "firewall": ["probe", "bypass", "route"]
  },
  "choice_pools": ["feedback.scan_ports.visibility"],
  "presentation_state_schema": {
    "scan_mode": ["standard", "masked"]
  },
  "completion_pool": "default",
  "failure_pool": "default"
}
```

Teksty są danymi, nie HTML. Renderer zawsze używa `textContent` albo istniejącej
funkcji escapującej.

## 17. Walidacja pliku

Loader odrzuca profil, jeśli:

* `schema_version` jest nieobsługiwana;
* brakuje `action_key`;
* presentation mode nie ma renderera;
* profil odwołuje się do nieistniejącej sceny, security lub choice;
* operation-security mapping łamie tabelę z sekcji 11;
* interakcja nie istnieje w wybranym wpisie `security_library`;
* profil zawiera niezależne `security_keys` i `interaction_types` zamiast
  jawnej macierzy `security`;
* wybór nie posiada defaultu albo timeoutu;
* `effect_scope` jest inne niż `presentation`;
* wybór zapisuje klucz lub wartość spoza `presentation_state_schema`;
* wariant odwołuje się do niezadeklarowanego klucza `presentation_state`;
* `feedback_content` aplikacji próbuje użyć sceny, security albo interakcji
  niedozwolonej dla jej `action_key`;
* content aplikacji zawiera niedozwolony placeholder, HTML albo kod;
* tekst zawiera HTML;
* timing jest ujemny albo przekracza limity bezpieczeństwa.

Błędny profil nie blokuje gameplayu. System zapisuje diagnostykę i wraca do
dotychczasowego prostego pending UI.

## 18. Obsługa odpowiedzi i błędów

OFS nie zakłada, że każda odpowiedź jest JSON-em.

Handler rozróżnia:

```text
2xx + poprawny JSON -> completion -> istniejący handler wyniku
non-2xx + JSON       -> failure -> istniejący komunikat backendu
non-2xx + non-JSON   -> failure transportowa z kodem HTTP
fetch rejected       -> network_error
abort                -> cancelled albo failure zależnie od źródła
```

Treść HTML z reverse proxy nie jest parsowana jako JSON i nie trafia do DOM.

Idempotent replay, `duplicate`, `superseded_by_capture`, `invalid_target` i
`target_state_changed` pozostają interpretowane wyłącznie przez istniejący
runtime aplikacji.

## 19. Telemetria

OFS rozszerza istniejący `APP_FLOW`, bez osobnego systemu logowania.

Minimalne zdarzenia:

```text
feedback_session_started
feedback_profile_loaded
feedback_scene_started
feedback_choice_shown
feedback_choice_selected
feedback_choice_timed_out
feedback_extended_wait_entered
feedback_payload_received
feedback_failed
feedback_cancelled
feedback_disposed
```

Pola:

```text
flow_id
session_id
app_id
action_key
presentation_mode
scene_id
content_source
elapsed_ms
http_status
completion_reason
```

`content_source` przyjmuje wyłącznie `app_structured`, `app_legacy` albo
`global_fallback`. Telemetria nie zapisuje samej treści autora.

Zakazane w telemetry:

* pełny payload;
* security celu;
* współrzędne;
* dane profilu;
* treść wyboru gracza wykraczająca poza lokalny enum.

## 20. Wydajność

Budżet jednej sesji:

* maksymalnie jeden główny timer sceny;
* maksymalnie jeden timer countdownu;
* brak `requestAnimationFrame` loop bez aktywnej animacji;
* maksymalnie 12 elementów dynamicznych w viewportcie;
* jedna współdzielona, cache'owana kopia JSON;
* brak requestów sieciowych wykonywanych przez scheduler;
* pełne cleanup po `dispose`.

OFS nie może wydłużać requestu ani blokować obsługi payloadu.

## 21. Feature flags i fallback

Flagi:

```text
CHAOS_OPERATION_FEEDBACK_ENABLED
CHAOS_OPERATION_FEEDBACK_SCAN_PORTS
CHAOS_OPERATION_FEEDBACK_DEBUG
```

Frontend otrzymuje bezpieczną projekcję flag. Domyślnie wszystkie są `false`.

Fallback następuje, gdy:

* system jest wyłączony;
* profil jest niepoprawny;
* JSON nie został załadowany;
* renderer nie istnieje;
* host aplikacji został usunięty;
* wystąpił błąd silnika.

Fallback uruchamia dotychczasowy pending UI i nigdy nie blokuje `/gonna-win`.

## 22. Implementacyjny spike 130.8.6.1–130.8.6.3

CHAOS realizuje proof kompozycji jako ograniczony implementacyjny spike za
domyślnie wyłączonymi feature flags:

```text
OFS-SPIKE-01 — scan_ports composition proof
```

Zakres:

* `130.8.6.1`: session, lifecycle, integracja z istniejącym `/gonna-win`,
  cancellation i minimalny renderer;
* `130.8.6.2`: roboczy fragment `operation_feedback.v1.json`, composer,
  security matrix i profile czasu;
* `130.8.6.3`: choices, `presentation_state`, content autora, trzy przebiegi i
  decyzja `GO / REVISE`;
* objąć wyłącznie `scan_ports` do czasu decyzji `GO`;
* przygotować dwa warianty contentu aplikacji obsługujących `scan_ports`, aby
  ten sam profil techniczny zachował dwa różne autorskie głosy;
* zdefiniować minimum dwie sceny dramaturgiczne;
* zdefiniować minimum trzy zabezpieczenia z jawnymi interakcjami;
* dodać jeden wybór modyfikujący lokalny `presentation_state`;
* wygenerować przez engine trzy wyraźnie różne, technicznie sensowne
  przebiegi;
* przeprowadzić deterministyczną próbę dla odpowiedzi szybkiej, średniej i
  długiej przez wstrzykiwany zegar oraz kontrolowane Promise testowe;
* sprawdzić, czy żaden przebieg nie wymaga specjalnego tekstu wpisanego na
  sztywno do scenariusza.

Spike jest częścią runtime, ale pozostaje nieaktywny bez flag i nie jest zgodą
na produkcyjny cutover. Artefaktem sprintu są: minimalny engine, próbka JSON,
trzy transkrypty, lista luk w schema oraz decyzja `GO / REVISE`.

Warunki `GO`:

1. trzy przebiegi są różne, ale wszystkie rozpoznawalne jako `scan_ports`;
2. każda linia techniczna pochodzi z poprawnej pary
   `security + interaction`;
3. wybór `MASKUJ` wpływa na kilka kolejnych scen bez wpływu na backend;
4. dramaturgię można zmienić bez edycji treści technicznej;
5. treść techniczną można rozszerzyć bez edycji definicji sceny;
6. payload może zakończyć każdy przebieg w dowolnym punkcie;
7. dwie aplikacje korzystające z `scan_ports` brzmią odmiennie bez duplikowania
   profilu operacji i schedulera.

Wynik `GO` pozwala rozpocząć generalizację w `130.8.6.4`. Status dokumentu
zmienia się z `PRODUCTION ARCHITECTURE DRAFT` dopiero po zapisaniu wyników
spike'a i zsynchronizowaniu kontraktu z rzeczywistą implementacją. `GO` nie
włącza automatycznie OFS na produkcji.

## 23. Plan wdrożenia

Przed generalizacją rendererów w `130.8.6.4` realizujemy dwa sprinty spinające
OFS z rzeczywistym launcherem CHAOS:

* `130.8.6.3.1` — mapowy Unified Launch Context i provisional window tworzone
  po read-only discovery, przed wykonawczym `/hack-action`; przy jednej
  pasującej aplikacji backend zwraca jawnego kandydata, picker jest pomijany,
  ale używany jest ten sam selected-app launch flow;
* `130.8.6.3.2` — idempotentna hydration istniejącego okna przez
  `applicationEffect` z `/launch-queue → /command`, bez drugiego okna i bez
  drugiego requestu gameplayowego.
* `130.8.6.3.3` — bazowy lokalny composer scen pre-execution i natychmiastowy
  handoff przy hydration;
* `130.8.6.4` — zakończone: `ofs_provisional`, `terminal`, `button_choice` i
  `window` korzystają ze wspólnego scene envelope bez łączenia schedulerów
  launch i execution; `progressbar_random` mapuje się na `window` bez fikcyjnego
  procentu;
* `130.8.6.5` — zakończone: profile execution/provisional dla 12 action keys,
  izolowany fallback błędnego profilu i timeline skeleton `launch_150s`;
* `130.8.6.6` — produkcyjny pakiet konkretnych scen na minimum 150 sekund,
  neutralny extended wait oraz validator pokrycia czasu i semantyki.

Oba sprinty zachowują legacy launch jako rollback. Discovery bez
`selected_app_id` zostaje ujednolicone dla jednego i wielu kandydatów, ale
sprinty nie zmieniają `/gonna-win`, receiptów, wyniku operacji ani backendu jako
źródła prawdy.

Stan 130.8.6.3.1: zaimplementowany za domyślnie wyłączoną flagą
`CHAOS_PROVISIONAL_APP_LAUNCH_ENABLED`. Provisional registry i auto-select są
gotowe; produkcyjne włączenie czeka na hydration z 130.8.6.3.2, aby późniejszy
`applicationEffect` nie tworzył drugiego klasycznego okna.

### Etap 0 — kontrakt

* schema i validator;
* projekcja istniejącego `levels` i kontrakt przyszłego `feedback_content`;
* pusty loader za flagą;
* brak zmian w UI.

### Etap 1 — prototyp `scan_ports`

* jeden profil;
* renderer `button_choice`;
* 4 rodziny scen;
* 3 wybory prezentacyjne;
* completion/failure;
* pełny cleanup.

### Etap 2 — shadow telemetry

Scheduler układa sceny, ale ich nie renderuje. Porównujemy dobór scen z
`action_key`, security i czasem requestu.

### Etap 3 — wewnętrzny cutover

`scan_ports` włączony dla kont testowych. Dotychczasowy pending UI pozostaje
natychmiastowym rollbackiem.

### Etap 4 — produkcja `scan_ports`

Stopniowe włączenie i obserwacja:

* błędów JS;
* czasu reakcji na payload;
* pozostawionych timerów;
* non-JSON errors;
* liczby extended waits;
* semantycznych powtórzeń.

### Etap 5 — kolejne operacje

Profile włączane pojedynczo. Nie powielamy silnika ani rendererów.

### Etap 6 — wygaszenie legacy wait UI

`APP_WAIT_LOG_MESSAGES`, sztuczny progressbar i lokalne spinnery są usuwane
dopiero po pełnym cutoverze wszystkich obsługiwanych interfejsów.

## 24. Rollback

Rollback nie wymaga migracji danych ani restartu workera.

Procedura:

1. wyłączyć flagę globalną albo flagę operacji;
2. frontend wraca do istniejącego pending UI;
3. requesty, receipty i gameplay działają bez zmian;
4. zachować telemetry do analizy;
5. nie usuwać aktywnych operacji ani stanu celu.

## 25. Testy obowiązkowe

### Unit

* walidacja schema;
* dobór wyłącznie dozwolonych security;
* dobór interakcji wyłącznie z macierzy wybranego security;
* odrzucenie profilu używającego luźnego iloczynu security i interakcji;
* brak powtórzenia sceny;
* deterministic seed w testach;
* timeout wyboru;
* zapis i odczyt lokalnego `presentation_state`;
* odrzucenie niezadeklarowanego klucza lub wartości presentation state;
* payload podczas countdownu;
* payload podczas delay sceny;
* disposal i brak callbacków po disposal;
* prawdziwy transport event kontra event narracyjny;
* fallback uszkodzonego profilu.
* priorytet `app_structured -> app_legacy -> global_fallback`;
* odrzucenie autorskiej pary security/interakcja spoza profilu operacji;
* wynik legacy pokazywany wyłącznie po zgodnym payloadzie;

### Integracyjne frontend

* każdy interface aplikacji;
* wstrzykiwany zegar/timery i kontrolowane Promise bez opóźniania produkcyjnego
  `/gonna-win`;
* kilka równoległych okien;
* zamknięcie okna podczas requestu;
* szybka odpowiedź poniżej 300 ms;
* odpowiedź 5, 30, 90 i 180 s;
* HTTP 400, 409, 429, 500 i 504;
* HTML zamiast JSON;
* offline i abort;
* `duplicate` oraz `superseded_by_capture`;
* brak wpływu wyboru narracyjnego na body `/gonna-win`;
* zachowanie tytułu i bezpiecznego contentu autora we wszystkich interfejsach;
* brak kolizji istniejących `buttons/options` z wyborami `feedback.*`;
* reduced motion;
* mobilny desktop.

### Regresja gameplay

* wszystkie 12 map actions;
* target standardowy, player, vulnerability i territory contest;
* filar, inner, 1v1 i multi-conflict;
* pierwszy capture i replay;
* kilka aplikacji na jednym celu;
* aktualizacja toolbara;
* tworzenie operacji;
* auto-close;
* aimed target i actions allowed;
* brak dodatkowego requestu gameplayowego.

### Test semantyczny

Dla każdego profilu generujemy co najmniej 100 planów ze stałymi seedami.
Automatyczny audyt potwierdza, że:

* operacja nie używa obcego security ani interaction type;
* transport event nie pojawia się bez sygnału;
* żadna scena przed payloadem nie deklaruje sukcesu;
* liczba kolejnych powtórzeń mieści się w limicie.

Następnie człowiek ocenia minimum 10 pełnych przebiegów każdej operacji.

## 26. Kryteria akceptacji

Moduł 1.0 jest gotowy, gdy:

1. request `/gonna-win` rozpoczyna się bez opóźnienia;
2. payload przerywa dowolną scenę w czasie poniżej jednej klatki renderera;
3. OFS nie wykonuje requestu gameplayowego;
4. wybór narracyjny nie trafia do backendu;
5. błędny moduł automatycznie wraca do legacy pending UI;
6. brak fałszywych zdarzeń transportowych;
7. brak fałszywego procentu postępu;
8. brak timerów i renderowania po zamknięciu okna;
9. szybka odpowiedź nie jest sztucznie opóźniana ponad completion;
10. rzeczywisty błąd backendu pozostaje widoczny;
11. wynik aplikacji jest identyczny z wynikiem bez OFS;
12. `scan_ports` przechodzi test produkcyjny przed włączeniem kolejnej akcji.
13. dwie aplikacje tej samej operacji zachowują własny content i charakter;
14. niepoprawny content autora przechodzi na fallback bez przerwania requestu.

## 27. Definition of Done całego cutoveru

* wszystkie 12 akcji posiada zwalidowane profile;
* trzy renderery działają na desktopie i mobile;
* wszystkie profile przechodzą audyt semantyczny;
* legacy global wait log nie jest używany przez obsłużone operacje;
* `progressbar_random` nie pokazuje fikcyjnego procentu;
* telemetry potwierdza cleanup i brak opóźnienia payloadu;
* przeprowadzono regresję gameplay i test produkcyjny;
* zaktualizowano `project_journal.md` oraz dokumentację AppForge;
* kreatory potrafią zapisać, zwalidować i podejrzeć `feedback_content`;
* feature flags i rollback zostały sprawdzone na środowisku produkcyjnym.

## 28. Ręczna edycja `operation_feedback.v1.json`

Plik ma dwie niezależne warstwy prezentacji:

* `provisional_timelines.launch_150s` określa kolejność i czas scen przed
  hydration. Każdy wpis ma unikalne `scene_id`, logiczną `family` oraz
  `start_after_ms` liczone od otwarcia provisional window;
* `provisional_scene_library` zawiera treść wskazaną przez `scene_id`. Scena ma
  `phase`, `transition`, obowiązkowe `cancelable: true` oraz `voices`;
* `scene_library` zawiera sceny wykonawcze po rozpoczęciu requestu;
* `security_library` przechowuje techniczne warianty security/interactions;
* `choice_library` zawiera wyłącznie lokalne wybory narracyjne `feedback.*`;
* `completion_library` i `failure_library` są używane dopiero po rzeczywistym
  payloadzie albo błędzie transportu;
* `operations` mapuje 12 `action_key` na renderer, pule scen, macierz security i
  `provisional_profile`.

W `voices` każda wartość jest listą wariantów, a wariant listą linii:

```json
"module_boot": {
  "phase": "booting",
  "transition": "fade",
  "cancelable": true,
  "voices": {
    "terminal": [["Linia A.", "Linia B."], ["Wariant 2."]],
    "default": [["Neutralny fallback."]]
  }
}
```

Dozwolone głosy: `default`, `terminal`, `button_choices`, `window` i
`progressbar_random`. Dozwolone placeholdery: `{app_title}`, `{description}`,
`{interface}`, `{target_label}`, `{action_label}`. Nie wolno dodawać HTML,
wyniku operacji, fikcyjnych błędów transportu ani danych gameplay/security.
`extended_wait` musi mieć minimum trzy warianty i jest rotowany co 12–20 s.
Zmiana czasu nie może cofnąć kolejności etapów ani skrócić pokrycia poniżej
150000 ms. Błędny profil operacji jest izolowany i wraca do legacy UI.

## 29. Niezmienne zasady

```text
Backend jest źródłem prawdy.
Feedback nie jest wynikiem.
Narracyjny wybór nie jest decyzją gameplayową.
Autor aplikacji nadaje jej głos, ale nie nadpisuje prawdy runtime.
Brak danych nie oznacza braku zabezpieczenia.
Transport error nie jest losowany.
Payload zawsze wygrywa z animacją.
Fallback nigdy nie blokuje gry.
```
