# Sprint 55 - Runtime Synchronization Audit

Data: 2026-07-06

Status: audit in progress

Cel: zebrac dowody o aktualnym cyklu synchronizacji runtime CHAOS bez
przebudowy endpointow, pollerow ani renderow.

Sprint 55 nie proponuje jeszcze rozwiazan. Dokument opisuje:

* co samo sie odswieza,
* jaki endpoint jest wolany,
* co backend robi po drodze,
* co frontend renderuje,
* jaki jest szacowany koszt,
* czy scope jest kandydatem do pozniejszej delty.

## Skala kosztu

```text
★       niski
★★      umiarkowany
★★★     sredni
★★★★    wysoki
★★★★★   bardzo wysoki
```

## Etykiety kandydata

```text
KEEP    polling wyglada uzasadniony w obecnym modelu
DELTA   dobry kandydat do pozniejszego delta feed
ACTION  mozliwe odswiezanie po akcji / zdarzeniu zamiast cyklicznie
REMOVE  potencjalnie zbedne odswiezanie
```

Etykieta nie jest decyzja implementacyjna. Jest wynikiem audytu.

---

## Inwentaryzacja synchronizacji

| Scope | Snapshot / endpoint | Polling / trigger | Backend | Frontend render | Kandydat |
| --- | --- | --- | --- | --- | --- |
| Toolbar / Wallet / Profile | `/api/profile` | manualne wywolania `refreshToolbarProfile()` i `getUserProfile()` | `sync_session_profile()` + `refresh_and_persist_operations()` | `renderToolbarStatus()` | DELTA |
| Desktop / Apps | `/api/profile` | `refreshDesktop()` po install/uninstall/refresh | `sync_session_profile()` | pelne czyszczenie i render ikon desktopu | ACTION / DELTA |
| Storage / File Manager | `/api/profile` | otwarcie File Managera + po uninstall/install | `sync_session_profile()` + storage normalization | storage bar + katalogi + lista plikow | DELTA |
| Googleplex catalog | `/api/profile`, `/resources.json` | otwarcie Browser/Googleplex | `sync_session_profile()` | katalog + wallet | ACTION |
| Ghost Exchange | `/api/ghost-exchange` | otwarcie zakladki Ghost Exchange | `refresh_and_persist_operations()` + `refresh_market_runtime()` | caly dashboard GX | DELTA |
| Mail / Cyberner list | `/api/mail/bootstrap` | `setInterval(refreshThreads, 3000)` | readonly profile + mail_store | lista kanalow/rozmow | DELTA / ACTION |
| Mail / active thread | `/api/chats/messages` | po bootstrapie, po otwarciu, po wyslaniu | readonly profile + mail_store + mark read | wiadomosci aktywnego watku | KEEP / DELTA |
| System Messages | `/system-messages` | `setInterval(..., 10000)` | readonly profile + update `system_messages` | toasty | DELTA / ACTION |
| Launch Queue | `/launch-queue` | rekurencyjny `setTimeout(..., 10000)` | readonly profile + czyszczenie queue | odpalenie aplikacji przez `/command` | ACTION |
| Player Hack Access | `/api/player-hack/access` | start desktopu + akcje player hack | endpoint access | panel player hack | KEEP |
| Operations summary | `/api/operations?summary=1` | mapa co 10 s + dev bug context | readonly profile + operation runtime | panel i markery operacji | DELTA |
| Map player actors | `/api/map/player-actors` | mapa co 5 s | `sync_session_profile(rebuild_territory=False)` + contacts + territory counts | markery graczy | KEEP / DELTA later |
| Map player areas | `/api/map/player-areas` | mapa co 10 s | `sync_session_profile(rebuild_territory=False)` + territory store + conflict detection | czyszczenie i render warstw terytorium | DELTA later |
| Map clan vulnerabilities | `/api/map/clan-vulnerabilities` | mapa co 10 s | `sync_session_profile(rebuild_territory=False)` + vulnerability store | czyszczenie i render markerow | DELTA later |

---

## Sprint 69 - Poller thinning update

Po Sprintach 61-68.5 rozrzedzono tylko pollery, ktore maja juz bezpieczny
delta-feed/recovery:

| Scope | Endpoint | Przed | Po | Status |
| --- | --- | --- | --- | --- |
| Cyberner list | `/api/mail/bootstrap` | 3000 ms | 10000 ms | delta dla unread/thread summary, snapshot recovery zostaje |
| Map player actors | `/api/map/player-actors` | 5000 ms | 30000 ms | delta dla `map.player_*`, snapshot recovery zostaje |

Nie zmieniono:

* `/api/map/player-areas`,
* `/api/map/clan-vulnerabilities`,
* `/api/operations?summary=1`,
* `/system-messages`,
* `/launch-queue`.

Szacunek statyczny dla jednego okna mapy i jednego Cybernera:

```text
68 requestow / min -> 44 requesty / min
```

Live checkpoint po wdrozeniu powinien dopisac realne:

* sredni czas odpowiedzi przed/po,
* max czas odpowiedzi przed/po,
* recovery_count,
* subiektywne lagi mapy/Cybernera.

---

## BlackNet future scope

Sprint 79 dodaje tylko kontrakt przyszlego read modelu
`blacknet_world_digest`.

BlackNet nie dostaje w Fazie G nowego pollera i nie powinien wolac ciezkich
snapshotow tylko po to, zeby wyrenderowac sygnaly.

Bezpieczna sciezka przyszlosci:

```text
istniejace snapshoty / cache / delta-feed
↓
blacknet_world_digest
↓
static/local blacknet_signal contract
↓
renderBlackNet()
```

Zasady:

* digest nie jest zrodlem prawdy,
* digest nie liczy stanu gry w requestcie BlackNetu,
* digest nie odpala `sync_session_profile()`,
* brak albo stary digest wraca do lokalnego `static/blacknet_signals.json`,
* AI generation pozostaje osobnym przyszlym krokiem.

---

## Dowody kodowe

### Profil jako ciezki snapshot

* `static/js/terminal.js:3624` `getUserProfile()` zawsze pobiera
  `/api/profile`.
* `run.py:10029` `/api/profile` wykonuje `sync_session_profile()`.
* `run.py:10035` `/api/profile` dodatkowo wykonuje
  `refresh_and_persist_operations()`.
* `run.py:8345` `sync_session_profile()` w pelnym trybie normalizuje profil,
  przebudowuje dane terytorium i zapisuje czesc danych z powrotem do profilu.

### Mail / Cyberner

* `static/js/terminal.js:7392` `bootstrap()` pobiera `/api/mail/bootstrap`.
* `static/js/terminal.js:7417` `refreshThreads()` pobiera
  `/api/mail/bootstrap`.
* `static/js/terminal.js:7561` refresh listy Cybernera jest wykonywany co 3000
  ms.
* `run.py:12051` `/api/mail/bootstrap` uzywa `load_profile_readonly()`, nie
  pelnego `sync_session_profile()`.
* `static/js/terminal.js:7344` aktywny watek pobiera `/api/chats/messages`.
* `run.py:12172` `/api/chats/messages` rowniez uzywa readonly profilu i oznacza
  watek jako przeczytany.

### Ghost Exchange

* `static/js/terminal.js:2934` `loadExchange()` pobiera `/api/ghost-exchange`.
* `run.py:10200` `/api/ghost-exchange` pobiera profil, wykonuje
  `refresh_and_persist_operations()` i `refresh_market_runtime()`.
* `run.py:10222` endpoint buduje sektorowy payload i dashboard.
* `static/js/terminal.js:2963` frontend renderuje caly dashboard GX przez
  `renderExchange()`.

### Mapa

* `templates/map_template.html:3658` mapa uruchamia pierwsze odswiezenia po
  starcie.
* `templates/map_template.html:3664` player actors odswiezaja sie co 5000 ms.
* `templates/map_template.html:3665` player areas odswiezaja sie co 10000 ms.
* `templates/map_template.html:3666` clan vulnerabilities odswiezaja sie co
  10000 ms.
* `templates/map_template.html:3667` active operations odswiezaja sie co
  10000 ms.
* `templates/map_template.html:3482` `refreshPlayerAreas()` czysci kilka warstw
  i renderuje je od nowa.
* `run.py:11237` `/api/map/player-areas` wykonuje sync profilu bez rebuild
  terytorium, odczytuje territory store i uruchamia conflict detection dla
  `source_event="map_reload"`.

### System messages / launch queue

* `static/js/terminal.js:7739` `pollSystemMessages()` pobiera
  `/system-messages`.
* `static/js/terminal.js:7757` system messages sa sprawdzane co 10000 ms.
* `run.py:12253` `/system-messages` uzywa readonly profilu, zwraca tylko nowe
  komunikaty i usuwa status `new`.
* `static/js/terminal.js:7759` `pollLaunchQueue()` pobiera `/launch-queue`.
* `static/js/terminal.js:7804` launch queue planuje kolejny poll po 10000 ms.
* `run.py:12668` `/launch-queue` uzywa readonly profilu i czysci queue po
  pobraniu.

---

## Karty scope

### Wallet / Toolbar

| Pytanie | Odpowiedz |
| --- | --- |
| Co wywoluje zmiane? | zakup produktu/aplikacji, auto-sale GX, transfer wallet, operacje przyznajace HC |
| Kto zapisuje zmiane? | endpointy ekonomii, Googleplex, Ghost Exchange runtime |
| Kto dzis ja wykrywa? | `getUserProfile()` / `refreshToolbarProfile()` przez `/api/profile`, czasem odpowiedzi endpointow akcji |
| Kto renderuje? | `renderToolbarStatus()` i lokalne aktualizacje wallet w Browserze |
| Czy trzeba odswiezac caly obiekt? | do samego HC nie |

Koszt backend: ★★★★

Koszt frontend render: ★★

Payload: ★★★★

Czestotliwosc / liczba wywolan: ★★★

Expected savings: request ★★, payload ★★★, CPU ★★, render ★★

Kandydat: DELTA

### Storage / File Manager

| Pytanie | Odpowiedz |
| --- | --- |
| Co wywoluje zmiane? | zapis pliku, auto-sale, install/uninstall, storage upgrade |
| Kto zapisuje zmiane? | finalizery plikow, Ghost Exchange runtime, Googleplex, uninstall |
| Kto dzis ja wykrywa? | `/api/profile` przy otwarciu File Managera albo po akcjach |
| Kto renderuje? | File Manager storage bar i katalogi |
| Czy trzeba odswiezac caly obiekt? | do paska storage nie |

Koszt backend: ★★★★

Koszt frontend render: ★★★

Payload: ★★★★★

Czestotliwosc / liczba wywolan: ★★

Expected savings: request ★★, payload ★★★★, CPU ★★, render ★★★

Kandydat: DELTA

### Apps / Desktop

| Pytanie | Odpowiedz |
| --- | --- |
| Co wywoluje zmiane? | install/uninstall/generate app, desktop settings |
| Kto zapisuje zmiane? | Googleplex, uninstall, app generator, desktop save |
| Kto dzis ja wykrywa? | `refreshDesktop()` przez `/api/profile` |
| Kto renderuje? | desktop icons, toolbar launchers, menu Start |
| Czy trzeba odswiezac caly obiekt? | przy pojedynczej aplikacji zwykle nie |

Koszt backend: ★★★★

Koszt frontend render: ★★★★

Payload: ★★★★

Czestotliwosc / liczba wywolan: ★★

Expected savings: request ★, payload ★★, CPU ★★, render ★★★★

Kandydat: ACTION / DELTA

### Ghost Exchange

| Pytanie | Odpowiedz |
| --- | --- |
| Co wywoluje zmiane? | nowe pliki, queue, dwell time, settlement, auto-sale |
| Kto zapisuje zmiane? | `refresh_market_runtime()` i operacje plikow |
| Kto dzis ja wykrywa? | wejscie w `/api/ghost-exchange` |
| Kto renderuje? | `renderExchange()` caly dashboard |
| Czy trzeba odswiezac caly obiekt? | do summary/transakcji nie zawsze |

Koszt backend: ★★★★★

Koszt frontend render: ★★★

Payload: ★★★★

Czestotliwosc / liczba wywolan: ★★

Expected savings: request ★★, payload ★★★, CPU ★★★★, render ★★

Kandydat: DELTA

### Mail / Cyberner

| Pytanie | Odpowiedz |
| --- | --- |
| Co wywoluje zmiane? | nowa wiadomosc, unread, kontakt, pending, kanal |
| Kto zapisuje zmiane? | `mail_store`, endpointy kontaktow i chatow |
| Kto dzis ja wykrywa? | `/api/mail/bootstrap` co 3000 ms oraz `/api/chats/messages` dla watku |
| Kto renderuje? | lista rozmow i aktywny chat |
| Czy trzeba odswiezac caly bootstrap? | dla unread/pojedynczego watku nie zawsze |

Koszt backend: ★★

Koszt frontend render: ★★★

Payload: ★★★

Czestotliwosc / liczba wywolan: ★★★★

Expected savings: request ★★★, payload ★★, CPU ★, render ★★★

Kandydat: DELTA / ACTION

### System Messages

| Pytanie | Odpowiedz |
| --- | --- |
| Co wywoluje zmiane? | system, operacje, GX, alerty, komunikaty runtime |
| Kto zapisuje zmiane? | helpery append/system message |
| Kto dzis ja wykrywa? | `/system-messages` co 10000 ms |
| Kto renderuje? | toast renderer |
| Czy trzeba odswiezac caly obiekt? | nie, endpoint juz filtruje nowe |

Koszt backend: ★★

Koszt frontend render: ★

Payload: ★

Czestotliwosc / liczba wywolan: ★★

Expected savings: request ★, payload ★, CPU ★, render ★

Kandydat: ACTION / DELTA

### Operations

| Pytanie | Odpowiedz |
| --- | --- |
| Co wywoluje zmiane? | start, postep, finalizacja, anulowanie operacji |
| Kto zapisuje zmiane? | operation runtime/finalizery |
| Kto dzis ja wykrywa? | `/api/operations?summary=1` na mapie co 10000 ms |
| Kto renderuje? | panel aktywnych operacji i markery operacji |
| Czy trzeba odswiezac caly obiekt? | dla pojedynczej operacji nie zawsze |

Koszt backend: ★★★

Koszt frontend render: ★★★

Payload: ★★

Czestotliwosc / liczba wywolan: ★★

Expected savings: request ★★, payload ★★, CPU ★★, render ★★★

Kandydat: DELTA

### Map Player Actors

| Pytanie | Odpowiedz |
| --- | --- |
| Co wywoluje zmiane? | ruch graczy, status kontaktow, relacje, oznaczony cel |
| Kto zapisuje zmiane? | profil gracza, contacts, territory store |
| Kto dzis ja wykrywa? | `/api/map/player-actors` co 5000 ms |
| Kto renderuje? | `renderPlayerActors()` |
| Czy trzeba odswiezac caly obiekt? | ruch pojedynczego aktora nie wymaga calej listy |

Koszt backend: ★★★★

Koszt frontend render: ★★★

Payload: ★★★

Czestotliwosc / liczba wywolan: ★★★★★

Expected savings: request ★★★★, payload ★★★, CPU ★★★, render ★★★

Kandydat: KEEP / DELTA later

### Map Player Areas

| Pytanie | Odpowiedz |
| --- | --- |
| Co wywoluje zmiane? | claim/capture/surround/conflict |
| Kto zapisuje zmiane? | territory store i conflict runtime |
| Kto dzis ja wykrywa? | `/api/map/player-areas` co 10000 ms |
| Kto renderuje? | czyszczenie i pelny render warstw area/conflict/contested |
| Czy trzeba odswiezac caly obiekt? | dla pojedynczego pola nie, ale zakres jest szeroki |

Koszt backend: ★★★★★

Koszt frontend render: ★★★★★

Payload: ★★★★

Czestotliwosc / liczba wywolan: ★★★

Expected savings: request ★★★, payload ★★★★, CPU ★★★★★, render ★★★★★

Kandydat: DELTA later

### Map Clan Vulnerabilities

| Pytanie | Odpowiedz |
| --- | --- |
| Co wywoluje zmiane? | raport podatnosci, withdraw, status raportu |
| Kto zapisuje zmiane? | vulnerability store |
| Kto dzis ja wykrywa? | `/api/map/clan-vulnerabilities` co 10000 ms |
| Kto renderuje? | czyszczenie i pelny render markerow podatnosci |
| Czy trzeba odswiezac caly obiekt? | dla pojedynczego raportu nie |

Koszt backend: ★★★

Koszt frontend render: ★★★

Payload: ★★

Czestotliwosc / liczba wywolan: ★★★

Expected savings: request ★★, payload ★★, CPU ★★, render ★★★

Kandydat: DELTA later

### Launch Queue

| Pytanie | Odpowiedz |
| --- | --- |
| Co wywoluje zmiane? | backend dodaje komende/aplikacje do kolejki |
| Kto zapisuje zmiane? | profile launch queue |
| Kto dzis ja wykrywa? | `/launch-queue` co 10000 ms |
| Kto renderuje? | uruchomienie aplikacji przez `/command` |
| Czy trzeba odswiezac caly obiekt? | nie |

Koszt backend: ★★

Koszt frontend render: ★★

Payload: ★

Czestotliwosc / liczba wywolan: ★★

Expected savings: request ★, payload ★, CPU ★, render ★

Kandydat: ACTION / DELTA

---

## Ranking kosztow v0

| Scope | Backend | Frontend render | Payload | Czestotliwosc | Ryzyko |
| --- | --- | --- | --- | --- | --- |
| Map player areas | ★★★★★ | ★★★★★ | ★★★★ | ★★★ | bardzo wysokie |
| Map player actors | ★★★★ | ★★★ | ★★★ | ★★★★★ | wysokie |
| Ghost Exchange | ★★★★★ | ★★★ | ★★★★ | ★★ | wysokie |
| `/api/profile` consumers | ★★★★ | ★★★★ | ★★★★★ | ★★★ | wysokie |
| Mail bootstrap | ★★ | ★★★ | ★★★ | ★★★★ | srednie |
| Operations summary | ★★★ | ★★★ | ★★ | ★★ | srednie |
| System messages | ★★ | ★ | ★ | ★★ | niskie |
| Launch queue | ★★ | ★★ | ★ | ★★ | niskie |

## Wnioski dowodowe bez rekomendacji implementacyjnych

1. Najciezsze scope'y to mapa terytoriow, player actors, Ghost Exchange oraz
   wszyscy konsumenci `/api/profile`.
2. Mail bootstrap po ostatnich poprawkach jest juz readonly, ale nadal odswieza
   liste co 3000 ms i renderuje liste rozmow.
3. Mapa ma najwieksze ryzyko laczone: czesty polling, backend z territory/conflict
   oraz pelne czyszczenie warstw po stronie Leaflet.
4. `/api/profile` jest uzywany jako zrodlo wielu niezaleznych informacji:
   wallet, toolbar, storage, apps, file manager, profile window.
5. Ghost Exchange jest mniej czesty niz mapa/mail, ale endpoint wykonuje realny
   runtime rynku i moze modyfikowac profil przy refreshu.

## Otwarte pytania do dalszego audytu

1. Ile razy w typowej sesji `getUserProfile()` jest wywolywany po pojedynczej
   akcji Googleplex / File Manager / Toolbar?
2. Czy `refreshToolbarProfile()` jest wolany zbyt czesto po endpointach, ktore
   juz zwracaja wystarczajace dane?
3. Jaki jest realny czas `/api/map/player-areas` na profilu z duza liczba pol i
   konfliktow?
4. Jaki jest realny czas renderu `refreshPlayerAreas()` w przegladarce?
5. Czy `/api/ghost-exchange` powinien byc klasyfikowany jako refresh read modelu,
   czy jako kontrolowany runtime tick rynku?
