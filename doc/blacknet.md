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
