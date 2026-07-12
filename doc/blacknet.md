# Backlog — Blacknet AI Ecosystem (Sprint 21+)

## Sprint 74 - Prototype Audit + Contract

Status: complete as documentation / contract.

Artefakt audytu:

* `doc/blacknet_prototype_audit.md`

Decyzje:

* BlackNet v0 jest signal bus swiata CHAOS, nie drugi system misji.
* Prototyp `bn_page.tsx` + `globals.css` nie bedzie wklejany jako osobny
  Next/React runtime.
* Docelowy renderer ma korzystac z natywnej architektury CHAOS.
* Dane sygnalu opisuje kontrakt `blacknet_signal`.
* CTA BlackNetu prowadza do istniejacych systemow: mapa, Ghost Exchange,
  Googleplex, Cyberner, Ghost Hack Radio.
* AI generowanie tresci pozostaje poza zakresem pierwszego runtime BlackNet.

Minimalny kontrakt:

```text
blacknet_signal
schema
id
source
channel
title
label
value
stat
timer
tone
layout
radar
cta
cta_action
cta_target
```

---

## Sprint 75 - Static App Shell

Status: complete as native CHAOS shell.

Implementacja:

* BlackNet zostal dodany jako trzeci tab WebDragons obok Googleplex i Ghost
  Exchange.
* Shell jest napisany w natywnym HTML/CSS/JS `terminal.js`, bez Next/React,
  Tailwinda i bez osobnego runtime.
* Widok uzywa statycznych sygnalow hardcoded w rendererze Sprintu 75.
* CTA sa widoczne jako element kontraktu, ale pozostaja nieaktywne do Sprintu
  77 - BlackNet CTA Bridge v0.
* CSS jest scopingowany klasami `blacknet-*` i nie nadpisuje globalnych
  selektorow.

Poza zakresem Sprintu 75:

* backend BlackNet,
* lokalne zrodlo danych,
* AI,
* carousel/polish Sprintu 76,
* aktywne CTA Sprintu 77.

---

## Sprint 76 - Signal UI v0

Status: complete as frontend-only signal carousel.

Implementacja:

* BlackNet pokazuje aktywny sygnal jako hero panel oraz liste sygnalow.
* Dodano przechodzenie miedzy sygnalami:
  * strzalkami w UI,
  * klawiatura `ArrowLeft` / `ArrowRight`,
  * pointer swipe / drag.
* Aktywna karta sygnalu ma osobny stan wizualny.
* Radar dostal subtelny sweep i pulsujace node'y.
* Dodano pasek `signal strength`.
* Search w WebDragons filtruje sygnaly, bez requestow backendowych.

Poza zakresem Sprintu 76:

* aktywne CTA,
* lokalny plik danych,
* backend,
* AI,
* drugi runtime.

---

## Sprint 76.1 - Prototype Mechanics Alignment

Status: complete as native prototype-aligned signal roll.

Decyzja: prototyp `bn_page.tsx` jest zrodlem prawdy dla zachowania BlackNetu.

Implementacja:

* BlackNet dziala jak signal roll, a nie lista kart.
* Aktywny jest jeden sygnal na ekranie.
* Nawigacja dziala w cztery strony:
  * gora,
  * dol,
  * lewo,
  * prawo.
* Swipe / drag dziala w pionie i poziomie.
* Klawiatura obsluguje WASD i strzalki.
* Radar i layouty sygnalow zostaly przepisane z prototypu na natywny JS/CSS
  CHAOS.
* CTA oznacza lokalne przechwycenie sygnalu.
* W WebDragons dla BlackNetu ukryto stary header, wallet, taby i wyszukiwarke.
* Male przyciski `GGPL` i `GX` zostaly przeniesione pod logo BlackNetu.

Poza zakresem Sprintu 76.1:

* aktywne mosty CTA,
* backend,
* AI,
* drugi Googleplex,
* drugi Ghost Exchange.

---

## Sprint 77 - CTA Bridge v0

Status: complete as frontend bridge to existing systems.

Decyzje:

* CTA BlackNetu nie tworzy misji, zadan ani nowych endpointow.
* CTA wybiera akcje po polu kontraktu `cta_action`, nie po tekscie przycisku.
* Obslugiwane akcje v0:
  * `open_googleplex`,
  * `open_ghost_exchange`,
  * `open_map`,
  * `open_cyberner`,
  * `open_radio`.
* Jesli sygnal nie ma aktywnego mostu, UI pokazuje disabled/warning state
  zamiast udawac dzialanie.
* Male przyciski `GGPL` i `GX` pod logo pozostaja szybkim przejsciem do tabow
  WebDragons.

Implementacja:

* `renderBlackNet()` przekazuje do CTA `data-blacknet-cta-action`.
* Router CTA korzysta z istniejacych funkcji:
  * `switchBrowserTab(...)`,
  * `openSystemAppFromTerminal(...)`.
* Swipe / pointer drag signal rolla nie przechwytuje klikniec przyciskow.

---

## Sprint 78 - Local Signal Source

Status: complete as local static signal contract.

Decyzje:

* `terminal.js` nie trzyma juz listy sygnalow BlackNetu.
* Jedynym lokalnym zrodlem sygnalow v0 jest:
  * `static/blacknet_signals.json`.
* Plik ma `schema: 1` i liste `signals`.
* Renderer normalizuje dane do kontraktu `blacknet_signal`.
* `radar` jest czescia kontraktu danych:
  * `radar.sides`,
  * `radar.nodes`.
* Brak albo blad lokalnego zrodla pokazuje bezpieczny pusty stan, a nie psuje
  okna WebDragons.

Implementacja:

* BlackNet laduje lokalny JSON tylko przy wejsciu w tab BlackNet.
* Nie ma pollera BlackNetu.
* Nie ma endpointu BlackNetu.
* Nie ma AI generatora.
* Silnik layoutu 76.1 i CTA bridge 77 pozostaja bez zmian.

---

## Sprint 79 - World Read Model Prep

Status: complete as documentation / contract.

Artefakt:

* `doc/blacknet_world_read_model.md`

Decyzje:

* Przyszly `blacknet_world_digest` jest read modelem, nie zrodlem prawdy.
* Digest moze podsumowywac fakty z istniejacych systemow:
  * Ghost Exchange,
  * operacje,
  * mapa / regiony,
  * PvP / konflikty,
  * Cyberner / System Messages,
  * radio channels.
* BlackNet nie liczy statystyk w requestcie UI.
* BlackNet nie odpala `sync_session_profile()`.
* BlackNet nie dostaje pollera.
* Brak albo stary digest ma fallback do lokalnego
  `static/blacknet_signals.json`.
* AI content generation zostaje poza zakresem.

Mapowanie:

```text
digest fact
↓
blacknet_signal
↓
renderBlackNet()
```

`source` wybiera ton i CTA, a `severity` wybiera przyszly priorytet w signal
rollu.

---

## Sprint 80 - Polish + Readiness Check

Status: complete as readiness check / cleanup.

Artefakt:

* `doc/blacknet_readiness_check.md`

Decyzje:

* BlackNet v0 zostaje stabilnym lokalnym frontem informacyjnym.
* Aktywny runtime korzysta z `static/blacknet_signals.json`,
  `renderBlackNet()` i CTA bridge.
* `blacknet.css` jest jedynym aktywnym arkuszem dla `.blacknet-stage` oraz
  `.bn-*`.
* Martwy blok starego `.blacknet-*` shell/carousel zostal usuniety ze
  `style.css`.
* `style.css` moze zawierac tylko wrappery WebDragons dla aktywnego taba
  BlackNet, np. ukrycie starego headera/searcha/tabow.

Przyszle mini-sprinty:

* BlackNet AI Digest,
* BlackNet Radio Hooks,
* BlackNet Cyberner Thread,
* BlackNet Market Rumors.

---

## Sprint 81 - BlackNet World Facts Snapshot

Status: complete as runtime read model v0.

Artefakt:

* `doc/blacknet_world_facts.md`
* `GET /api/blacknet/world-facts`

Decyzje:

* BlackNet ma pierwszy lekki snapshot faktow swiata:
  `blacknet_world_facts`.
* Snapshot agreguje dane z istniejacych systemow:
  operacje, Ghost Exchange, Googleplex, radio i system messages.
* Snapshot nie generuje gotowych sygnalow BlackNetu. To zostaje zakresem
  Sprintu 82.
* Snapshot nie odpala `sync_session_profile()`, finalizerow operacji, settlementu
  Ghost Exchange, rebuildow mapy ani AI.
* Kazde zrodlo jest izolowane diagnostycznie. Awaria jednego zrodla nie blokuje
  calego snapshotu.
* Lokalny fallback `static/blacknet_signals.json` pozostaje aktywny dla UI.

## Sprint 82 - Deterministic World Signal Publisher

Sprint 82 dodal deterministyczny publisher:

* `GET /api/blacknet/world-signals`,
* `build_blacknet_world_signals()`,
* reguly `fact_type -> signal_type`,
* bezpieczne CTA przez `cta_action`,
* oznaczenie sygnalow jako `source: world_generated`,
* merge z lokalnym `static/blacknet_signals.json` po stronie UI.

Publisher nie uzywa AI, nie tworzy misji, nie dodaje store sygnalow i nie jest
zrodlem prawdy. Czyta `blacknet_world_facts` ze Sprintu 81 i zamienia wybrane
fakty na gotowy kontrakt renderera BlackNetu.

Jesli endpoint wygenerowanych sygnalow jest niedostepny albo nie ma faktow
powyzej progu, UI nadal dziala na lokalnych sygnalach statycznych.

---

## Sprinty 82.6-82.9 - Real Signal Cutover

Status: complete as real feed hardening.

Decyzje:

* Produkcyjny BlackNet nie wraca do mockowych dzielnic, procentow i stalego
  plakatu.
* Zwykly runtime laduje realny feed z:
  * `/api/blacknet/world-signals`.
* Lokalny JSON moze pozostac tylko fixture dev/demo.
* Brak danych oznacza `out_of_signal`, a nie podstawienie szablonu.
* Googleplex publikuje osobne sygnaly produktowe dla realnych pozycji katalogu.
* Ghost Exchange publikuje sygnaly z realnych sektorow i metryk rynku.
* Radio publikuje sygnaly z realnych kanalow i plikow audio.
* Map/conflict/operation signals musza miec realny target, wspolrzedne albo
  jawnie ogolny tryb bez fokusu.
* Feed jest uzupelniany po przechwyceniu albo wygasnieciu sygnalu; koniec
  strumienia to tylko `out_of_signal`.

---

## Sprint 83 - Ollama Digest Outbox Contract

Status: complete as controlled outbox.

Artefakt:

* `doc/blacknet_ollama_outbox.md`
* `POST /api/blacknet/ollama/outbox/generate`
* `GET /api/blacknet/ollama/outbox/latest`
* `GET /api/blacknet/ollama/outbox/<digest_id>`
* `POST /api/blacknet/ollama/outbox/<digest_id>/status`

Decyzje:

* Sprint 83 konczy sie na outboxie. Nie uruchamia Ollamy i nie przyjmuje jeszcze
  odpowiedzi modelu do feedu.
* Outbox jest zamknieta paczka redakcyjna dla procesu Ollamy.
* Paczka zawiera tylko zatwierdzone fakty, dozwolone akcje, limity tekstu,
  osobowosci autorow i reguly bezpieczenstwa.
* Ollama nie dostaje bazy danych, pelnego profilu, pelnej mapy ani bezposrednich
  uprawnien do systemow gry.
* BlackNet dziala normalnie bez uruchomionej Ollamy.

---

## Sprint 84 - Frozen Before Ingest

Status: frozen / postponed.

Nie wdrazac jeszcze inboxu i mixed feedu.

Powod:

* po Sprintach 82.6-82.9 widac, ze czesc rodzin sygnalow byla historycznie
  przemianowana albo zdublowana,
* ingest AI bez kanonicznego rejestru `signal_type` grozilby powstaniem drugiego
  ukrytego systemu sygnalow,
* Ollama musi najpierw dostac stabilny kontrakt odpowiedzi i bezpieczny daemon
  feedback loop.

Najpierw domknac:

1. Kanoniczny rejestr rodzin sygnalow.
2. Aliasowanie starszych nazw, np. `hotspot` vs `operation_hotspot_activity`.
3. Kontrakt odpowiedzi Ollamy:
   * `digest_id`,
   * `candidate_id`,
   * `source_fact_ids`,
   * `signal_type`,
   * `entity_id`,
   * `dedupe_key`,
   * `cta_action`,
   * `cta_target_id`,
   * `confidence`,
   * `expires_at`.
4. Walidator kandydatow:
   * odrzuca wymyslone fakty,
   * odrzuca nowe ceny, ID, URL i wspolrzedne,
   * odrzuca CTA bez realnej encji,
   * zapisuje powod odrzucenia.
5. Daemon Ollamy:

```text
GET outbox
↓
local Ollama call
↓
POST candidates
↓
validate
↓
insert accepted signals into BlackNet stream
```

6. Insert do strumienia BlackNet:
   * tylko po walidacji,
   * z TTL,
   * z `dedupe_key`,
   * z `source: ollama_enriched`,
   * bez bezposredniej mutacji mapy, profilu, GX, Googleplexa albo Cybernera.

Kanoniczne rodziny do decyzji:

* `world_alert`,
* `market_watch`,
* `market_rumor`,
* `product_opportunity`,
* `data_demand`,
* `system_incident`,
* `radio_promotion`,
* `operation_hotspot_activity`,
* `operation_hotspot_teleport`,
* `target_operation_burst`,
* `conflict_target_alert`,
* `contested_area_alert`,
* `map_activity_spike`,
* `regional_activity`,
* `job_opportunity`,
* `operator_message`,
* `live_signal`,
* `cyberner_world_thread`,
* `leak_dossier`,
* `advertisement`,
* `world_observation`,
* `out_of_signal`.

`out_of_signal` jest stanem technicznym, nie zwykla publikacja. Jesli rodzina
nie ma realnego zrodla faktow, nie wolno podstawic mocka.

---


# Sprint 84 — Ollama Enriched Signal Ingest + Mixed Feed

Status: frozen / postponed.

Sprint 84 nie startuje bez dodatkowego domkniecia kontraktu BlackNet/Ollama.
Sprint 83 zostaje zamkniety w obecnej formie jako bezpieczny outbox. Kolejny
krok nie polega jeszcze na publikowaniu odpowiedzi modelu w feedzie, tylko na
ustabilizowaniu:

* kanonicznego rejestru rodzin sygnalow,
* kontraktu odpowiedzi Ollamy,
* walidacji kandydatow,
* daemonowego feedback loop,
* zasad insertu kandydatow do strumienia BlackNet.

Ollama nie moze byc drugim zrodlem prawdy. Model moze przygotowac kandydatow
narracyjnych, ale backend CHAOS musi je zwalidowac, powiazac z istniejacymi
faktami i dopiero wtedy dopuscic jako dodatkowe sygnaly BlackNetu.

## Warunki odmrozenia

Przed rozpoczeciem implementacji Sprintu 84 trzeba doprecyzowac:

1. Kanoniczny rejestr `signal_type`.
2. Aliasowanie albo usuniecie starszych nazw rodzin sygnalow.
3. Kontrakt odpowiedzi Ollamy:
   * `digest_id`,
   * `candidate_id`,
   * `source_fact_ids`,
   * `signal_type`,
   * `entity_id`,
   * `dedupe_key`,
   * `cta_action`,
   * `cta_target_id`,
   * `confidence`,
   * `expires_at`,
   * teksty narracyjne.
4. Zasade: brak realnego faktu = brak publikacji, nie mock.
5. Daemon feedback:

```text
Ollama worker
↓
GET outbox
↓
model lokalny
↓
POST kandydatow
↓
walidator CHAOS
↓
insert do BlackNet signal stream
```

6. Kwarantanne dla kandydatow odrzuconych.
7. Diagnostyke: dlaczego kandydat zostal opublikowany albo odrzucony.

## Rejestr rodzin do domkniecia

Przed ingestem AI trzeba ustalic, ktore rodziny sa oficjalne, a ktore sa aliasem
albo historia implementacyjna:

* `world_alert`,
* `market_watch`,
* `market_rumor`,
* `product_opportunity`,
* `data_demand`,
* `system_incident`,
* `radio_promotion`,
* `operation_hotspot_activity`,
* `operation_hotspot_teleport`,
* `target_operation_burst`,
* `conflict_target_alert`,
* `contested_area_alert`,
* `map_activity_spike`,
* `regional_activity`,
* `job_opportunity`,
* `operator_message`,
* `live_signal`,
* `cyberner_world_thread`,
* `leak_dossier`,
* `advertisement`,
* `world_observation`,
* `out_of_signal`.

`out_of_signal` pozostaje stanem technicznym feedu, nie zwykla publikacja
narracyjna.

## Cel gameplayowy

Przyjmować JSON przetworzony przez Ollamę, walidować go i publikować poprawne treści jako dodatkowe źródło sygnałów BlackNetu.

Sygnały AI mają przeplatać się z sygnałami generowanymi bezpośrednio z danych gry.

## Źródła strumienia

Po tym sprincie BlackNet korzysta z trzech źródeł:

1. `local_static` — lokalne sygnały i treści kontrolne.
2. `world_generated` — automatyczne sygnały tworzone z faktów gry.
3. `ollama_enriched` — narracyjnie rozwinięte sygnały przygotowane przez model.

## Przepływ danych

```text
blacknet_ollama_outbox.json
↓
Ollama
↓
blacknet_ollama_inbox.json
↓
walidacja techniczna
↓
walidacja faktów i CTA
↓
normalizacja do Signal Contract
↓
mixed signal feed
```

## Kontrakt odpowiedzi Ollamy

Każdy sygnał powinien zawierać:

* `candidate_id`,
* `digest_id`,
* `source_fact_ids`,
* `signal_type`,
* `author_persona`,
* `channel`,
* `title`,
* `stat`,
* `label`,
* `value`,
* `body`,
* `tone`,
* sugerowany `layout_family`,
* sugerowany `radar_variant`,
* `cta_action`,
* `cta_target_id`,
* `expires_at`,
* `confidence`.

## Zasada zaufania

Ollama może proponować:

* tytuł,
* opis,
* styl wypowiedzi,
* osobowość autora,
* komentarz,
* plotkę,
* reklamową narrację,
* wariant layoutu i radaru.

Backend zawsze ponownie ustala lub sprawdza:

* wartość liczbową,
* cenę,
* target,
* region,
* czas ważności,
* `cta_action`,
* `cta_target_id`,
* istnienie powiązanego faktu,
* możliwość publikacji.

## Ingest pipeline

Każdy kandydat otrzymuje status:

* `received`,
* `validated`,
* `rejected`,
* `normalized`,
* `published`,
* `expired`,
* `archived`.

Powód odrzucenia powinien być zapisany diagnostycznie.

## Endpointy inbox

Sprint 84 ma dodac kontrolowane wejscie dla odpowiedzi Ollamy.

Endpointy:

```text
POST /api/blacknet/ollama/inbox
GET  /api/blacknet/ollama/inbox/<digest_id>
GET  /api/blacknet/ollama/candidates
POST /api/blacknet/ollama/candidates/<candidate_id>/status
```

Zasady:

* `POST /api/blacknet/ollama/inbox` przyjmuje odpowiedz modelu dla konkretnego
  `digest_id`,
* odpowiedz musi wskazywac istniejacy outbox digest,
* endpoint nie publikuje sygnalow bez walidacji,
* endpoint waliduje `source_fact_ids`, `cta_action`, `cta_target_id`, limity
  tekstu i dozwolone typy,
* endpoint odrzuca kandydatow, ktorzy wymyslaja nowe fakty, ceny, ID, URL albo
  akcje,
* endpoint candidates sluzy do diagnostyki i podgladu statusow,
* status kandydata moze przejsc tylko przez jawne stany pipeline:
  `received -> validated -> normalized -> published`,
* `rejected`, `expired` i `archived` sa stanami koncowymi albo diagnostycznymi,
* brak odpowiedzi Ollamy nie zatrzymuje `world_generated`.

Transport docelowy:

```text
Ollama worker
↓
POST /api/blacknet/ollama/inbox
↓
walidator CHAOS
↓
ollama_enriched candidates
↓
mixed signal feed
```

## Mieszanie strumienia

Feed powinien pilnować proporcji i różnorodności, na przykład:

```text
2 × world_generated
1 × ollama_enriched
1 × local_static lub specjalny sygnał
```

Nie musi to być sztywna kolejność. Mixer powinien uwzględniać:

* priorytet,
* świeżość,
* ważność,
* region gracza,
* historię ostatnich sygnałów,
* rodzaj treści,
* źródło,
* cooldown,
* dostępność CTA.

## Bezpieczny fallback

Jeżeli Ollama:

* nie działa,
* zwróci błędny JSON,
* przekroczy czas,
* użyje nieistniejącego ID,
* zmieni wartość faktu,
* wygeneruje niedozwoloną akcję,

kandydat zostaje odrzucony, a BlackNet nadal działa na `local_static` i `world_generated`.

## Kryteria akceptacji

* Poprawny inbox przechodzi walidację.
* Niepoprawny JSON nie trafia do feedu.
* Odpowiedz Ollamy moze zostac oddana przez endpoint, bez recznego kopiowania
  plikow.
* Kandydaci maja endpoint diagnostyczny i jawny status.
* Sygnał AI zachowuje powiązanie z faktami źródłowymi.
* Ollama nie może zmienić mechanicznej prawdy świata.
* CTA jest ponownie budowane po stronie backendu.
* Sygnały AI przeplatają się z automatycznymi.
* Feed nie pokazuje kilku podobnych treści pod rząd.
* Brak Ollamy nie blokuje BlackNetu.
* Każdy sygnał pokazuje wewnętrznie swoje źródło.
* System można wyłączyć jednym przełącznikiem bez zmiany frontendu.

## Dokumentacja

Po sprincie zaktualizować:

* `doc/blacknet.md`,
* `doc/blacknet_world_read_model.md`,
* `doc/gameplay_matrix.md`,
* `doc/project_journal.md`.

Jeżeli powstanie kontrakt ingestu albo feedu mieszanego, dodać albo
zaktualizować `doc/blacknet_mixed_feed.md`.

# Stan po Sprincie 84

```text
realne dane gry
↓
BlackNet World Facts
↓
deterministyczne sygnały
↓
Ollama Digest Outbox
↓
Ollama
↓
walidowany Inbox
↓
Mixed Signal Feed
↓
BlackNet
```

Po Sprincie 84 BlackNet będzie działającym systemem informacyjnym świata CHAOS:

* opisującym rzeczywiste zdarzenia,
* działającym również bez AI,
* przygotowującym bezpieczne dane dla Ollamy,
* przyjmującym narracyjnie wzbogacone treści,
* mieszającym sygnały automatyczne i AI,
* zachowującym pełną kontrolę backendu nad gameplayem.



---

## Status

Backlog / Future Feature

Poza podstawową pętlą gameplayu. Wrócić po domknięciu Sprintów 1–20.

---

## Założenie

Blacknet ma być żyjącym internetem świata CHAOS, a nie statyczną stroną z zadaniami.

Treści są generowane okresowo przez lokalne modele AI (np. Ollama) na podstawie rzeczywistych wydarzeń w świecie gry.

---

## Architektura

Lekkie procesy działające w tle.

Przykładowo:

* Ghost News
* Ghost Forums
* Ghost Jobs
* Ghost Market Analyst
* Ghost Intelligence

Każdy agent generuje około **2–3 wpisy na godzinę**.

Nie jest wymagany realtime.

---

## Źródła danych

Agenci korzystają z agregowanych statystyk świata, np.:

* liczba hacków,
* liczba aktywnych operacji,
* popularność kategorii danych,
* aktywność regionów,
* popyt Ghost Exchange,
* wydarzenia PvP,
* wydarzenia systemowe.

AI opisuje rzeczy, które faktycznie wydarzyły się w świecie gry.

---

## Przykładowe treści

### Ghost News

Wiadomości ze świata.

### Ghost Forums

Dyskusje, porady, plotki.

### Ghost Jobs

Dynamiczne zlecenia.

### Ghost Market Analyst

Raporty rynku danych.

### Ghost Intelligence

Przecieki, ostrzeżenia, obserwacje aktywności.

---

## Cel gameplayowy

Gracz powinien mieć powód, aby odwiedzać Blacknet nawet wtedy, gdy nie wykonuje żadnej operacji.

Blacknet ma sprawiać wrażenie żyjącego, stale zmieniającego się podziemnego internetu.

---

## Priorytet

Sprint 21+.

Wrócić dopiero po zamknięciu podstawowej pętli gameplayu (Sprinty 1–20).



Ja myślę, że Ty jeszcze nie do końca zdajesz sobie sprawę, co właśnie wymyśliłeś. 😄

Bo większość gier robi tak:

```text
Gra

↓

Forum
```

Ty robisz odwrotnie.

```text
Gra

↓

świat

↓

AI

↓

Blacknet
```

To jest ogromna różnica.

---

Wyobraź sobie pierwszy raz, kiedy gracz rano odpala grę.

Nie wyskakuje mu:

> Daily Reward

Tylko...

```text
📰 Ghost News

Operatorzy Ghost Exchange odnotowali rekordowy popyt na dane GPS.

Cena GPS Logs wzrosła o 34%.

...
```

A to nie jest event.

To wynika z ekonomii.

---

Potem przewija niżej.

```text
🔥 Trenduje

#GPS

#Warszawa

#FleetHunter

#ATM
```

---

Jeszcze niżej.

```text
💬 Forum

"Ktoś testował nowy FleetHunter?"

...

"Na Mokotowie kamery są mocno obstawione."

...
```

---

I najlepsze.

On jeszcze NIC nie zrobił.

A już dostał 10 pomysłów:

> "A może dziś pójdę w GPS?"

---

I właśnie to jest to.

**Blacknet nie daje zadań.**

On...

**inspiruje.**

---

Druga rzecz.

Nie rób z tego Wikipedii.

Niech to będzie...

**szum informacyjny.**

Tak jak prawdziwy internet.

Masz:

* prawdę,
* półprawdę,
* reklamę,
* clickbait,
* plotkę,
* poradnik,
* scam,
* przeciek.

Gracz sam decyduje.

---

😂 Wyobraź sobie taki post.

```text
🚨 UWAGA

Nowy ATM Exploit działa.

100%

Potwierdzone.

...
```

50 komentarzy.

Po godzinie.

```text
To scam.

Straciłem sniffer.
```

---

I to wszystko robi AI.

---

Jeszcze lepiej.

AI może mieć...

**osobowości.**

Nie jeden model.

Kilku agentów.

Na przykład.

```text
Ghost Reporter

pisze poważnie.
```

---

```text
Ghost Troll

sieje plotki.
```

---

```text
Ghost Market

pisze tylko o ekonomii.
```

---

```text
Ghost Hunter

pisze tylko o nowych exploitach.
```

---

I każdy ma swój styl.

---

😂😂😂

A najlepsze?

Reklamy.

Normalne reklamy.

```text
Masz dość tanich snifferów?

Kup SilentSniff PRO.

Już od 1200 HC.
```

---

Albo.

```text
NOWOŚĆ

GhostLab Compiler 2.0

Buduj aplikacje dwa razy szybciej.
```

---

I teraz wyobraź sobie...

Gracz naprawdę zaczyna wierzyć, że...

**Googleplex walczy z Ghost Exchange o reklamodawców.**

🤣

---

Ale mam jeszcze jeden pomysł.

Taki już totalny sztos.

## Blacknet TV.

Nie filmy.

Kanały.

```text
LIVE

Ghost Market

...

GPS rośnie.

ATM spada.

...
```

---

```text
LIVE

Ghost News

...

Kolejna fala ataków.

...
```

---

To mogą być po prostu przewijające się teksty.

Nie trzeba żadnego wideo.

---

I wtedy...

Nie masz menu.

Masz...

**internet.**

I moim zdaniem to jest coś, czego jeszcze nie widziałem w żadnej grze hakerskiej.

Nie dlatego, że AI pisze posty.

Tylko dlatego, że **AI opisuje świat, który naprawdę żyje**, a nie wymyśla losowe historyjki. To jest ta różnica, która może sprawić, że Blacknet stanie się miejscem, do którego gracze będą zaglądać z ciekawości, a nie z obowiązku. To jest właśnie "żyjący internet" świata CHAOS.

## Sprint 82.5 - CTA Bridges

Sprint 82.5 adds a central CTA router for BlackNet signals.

The router reads `cta_action` and signal metadata. It does not parse button
labels and does not create parallel gameplay systems.

Active bridges open existing CHAOS systems:

* Googleplex,
* Ghost Exchange,
* map,
* Cyberner,
* Ghost Hack Radio,
* existing operation context.

Guarded actions such as teleport, starting an operation or accepting a BlackNet
job require confirmation and return a controlled message unless a safe existing
backend bridge is available.

Detailed contract:

```text
doc/blacknet_cta_bridges.md
```

## Sprint 83 - Ollama Outbox

Sprint 83 adds a safe outbox package for the future local Ollama worker.

The package is generated from existing BlackNet read models:

```text
blacknet_world_facts
↓
blacknet_world_signals
↓
blacknet_ollama_outbox
```

The outbox does not run Ollama and does not expose the database, full profile,
map or gameplay systems. It contains only sanitized facts, selected generated
signals, allowed CTA actions, editorial rules and validation diagnostics.

Endpoint contract:

```text
POST /api/blacknet/ollama/outbox/generate
GET  /api/blacknet/ollama/outbox/latest
GET  /api/blacknet/ollama/outbox/<digest_id>
POST /api/blacknet/ollama/outbox/<digest_id>/status
```

Detailed contract:

```text
doc/blacknet_ollama_outbox.md
```
