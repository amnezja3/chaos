Tak — rozpiszmy to jako porządny, kontrolowany plan, żeby Codex nie rozlał tego po całej mapie.

## Sprint 1 — wspólna warstwa `player_actors`

Cel: wszystkie obce avatary widoczne na mapie mają jeden wspólny format danych.

Zakres:

```text
Backend:
- dodać helpery:
  resolve_player_actor_relation()
  resolve_player_actor_actions()
  build_player_actor()

- dodać endpoint:
  GET /api/map/player-actors

Źródła:
- znajomi z mail_store.list_contacts(username)
- intruzi z territory_store.list_recent_area_intruders(username)

Bez:
- self/motocykla
- globalnych neutralnych graczy
- pełnej logiki klanów
- prawdziwych akcji menu
```

Ten sprint robi fundament: backend mówi frontendowi, kim jest dany gracz i jakie akcje są dostępne, ale jeszcze niczego naprawdę nie wykonuje.

## Sprint 2 — render markerów z `player_actors`

Cel: frontend przestaje renderować znajomych i intruzów osobnymi ścieżkami.

Zakres:

```text
Frontend:
- dodać window.playerActorMarkers = {}
- dodać buildPlayerActorIcon(actor)
- dodać refreshPlayerActors()
- dodać renderPlayerActors(actors)

Do wygaszenia:
- refreshFriendMarkers()
- render intruderów wewnątrz refreshPlayerAreas()
```

Ten sprint porządkuje mapę: znajomy i intruz nadal mogą wyglądać inaczej, ale są renderowani przez jedną funkcję.

## Sprint 3 — menu gracza na mapie

Cel: każdy `player_actor` ma swoje menu kontekstowe.

Zakres:

```text
Menu:
- Dodaj do znajomych
- Rozpocznij rozmowę
- Przelej HC
- Oznacz jako cel
- Charakterystyka

Logika:
- opcje aktywne według actor.actions
- disabled pokazuje reason
- akcje poza profilem dają toast “moduł w budowie”
```

Ten sprint dodaje interakcję, ale bez jeszcze podpinania walleta, chatu i hackowania. Dzięki temu testujemy samą architekturę menu.

## Sprint 4 — charakterystyka gracza

Cel: pierwsza prawdziwa akcja z menu.

Zakres:

```text
Frontend:
- modal/panel charakterystyki
- dane: nick, username, relation, source, status, clan jeśli dostępny

Backend:
- opcjonalnie rozszerzyć player_actor.context
- bez osobnego endpointu, jeśli dane mieszczą się w payloadzie
```

Ten sprint daje sensowny efekt użytkowy bez ryzyka rozwalenia mechaniki gry.

## Sprint 5 — znajomi i rozmowa

Cel: podpiąć social loop.

Zakres:

```text
Dodaj do znajomych:
- request/pending
- wiadomość z gestem powitania
- odpowiedź odbiorcy automatycznie akceptuje znajomość

Rozpocznij rozmowę:
- aktywne tylko dla friends
- otwiera komunikator z tym graczem
```

Ten sprint podpina istniejące kontakty i komunikator pod menu mapy.

## Sprint 6 — Wallet HC

Cel: przelew HC z menu gracza.

Zakres:

```text
Nowa aplikacja Wallet:
- saldo
- odbiorca
- kwota
- akcept/anuluj
- minimalna historia przelewów

Menu:
- “Przelej HC” otwiera Wallet
- odbiorca ustawiony z actor.username
```

Ten sprint warto zrobić osobno, bo wallet będzie żył też poza mapą.

## Sprint 7 — oznacz jako cel

Cel: gracz może zostać targetem gry.

Zakres:

```text
Backend:
- player_target
- target_username
- target_mode: "player"
- zasady blokady: friend, same_clan, self

Frontend:
- “Oznacz jako cel”
- marker/status targetu
- bez jeszcze panelu post-hack
```

Ten sprint tylko oznacza gracza jako cel i wpina go w zasady hackowania. Pełne akcje po shackowaniu to osobna gałąź.

## Sprint 8 — post-hack player tools

Cel: po shackowaniu gracza pojawia się specjalny panel narzędzi.

Zakres późniejszy:

```text
- przelewy po hacku
- usuwanie znajomych
- przegląd maili systemowych
- pliki i aplikacje
- ustawienia zabezpieczeń profilu
- narzędzia kupowane w Googleplex
- wymagany poziom / koszt / ryzyko
```

Tak, ja bym zrobił dokładnie tak: **każda apka osobny sprint**, a dopiero na końcu przebudowa creatorów pod `pro-system-tools`.

Masz już dobry fundament: katalog `PRO_SYSTEM_TOOLS` istnieje w `run.py`, jest dostęp czasowy po hacku i placeholder `/api/player-hack/tool/use` , a desktop już ma osobne aplikacje i creatory typu AppForge, TermCreator, WindowMaker, ButtonMaker .

Kolejność zrobiłbym tak:

**Sprint 9 — systemLogReader**
Najbezpieczniejsza pierwsza apka. Po aktywnym hacku pokazuje ostatnie 5 komunikatów systemowych ofiary w terminalowym oknie. Mały zakres, łatwy test, zero destrukcji.

**Sprint 10 — securityPanelProxy**
Desktopowa wersja panelu zabezpieczeń ofiary. To ważne, bo masz już logikę zabezpieczeń dla profilu i targetów, więc tu można zrobić sensowny most bez wymyślania wszystkiego od zera.

**Sprint 11 — financialSniffer**
Drobna losowa kradzież HC, zależna od levelu/respectu. Tu trzeba uważać na balans i log transakcji, więc osobny sprint.

**Sprint 12 — friendKicker**
Losowa próba usunięcia jednego znajomego ofiary, bez pokazania listy. To dotyka kontaktów i social flow, więc osobno.

**Sprint 13 — arsenalCleaner**
Losowa próba usunięcia apki/narzędzia z arsenalu ofiary. To dotyka `apps`, `files.tools`, launchera i Googleplexa, więc też osobno.

**Sprint 14 — Googleplex gating**
Dopiero tu spinamy sklep: `category: pro-system-tools`, wymagany level, clan/fraction, cena HC, płatność do admina. Instalator już pobiera kasę i umie płacić twórcy/adminowi, więc rozbudujemy istniejący `/install-app`, a nie zrobimy drugi sklep .

**Sprint 15:** creatorzy jako płatne aplikacje w Googleplex.
Czyli AppForge, TermCreator, WindowMaker, ButtonMaker wypadają z darmowych bazowych ikon i trafiają do sklepu z level/respect/HC.

**Sprint 16:** dopiero zakupione creatory dostają tryb publikowania `pro-system-tools`.
I tu bym dał zasadę: **tylko AppForge może publikować pro-system-tools**, reszta tworzy swoje zwykłe typy aplikacji.

Ja bym tego **nie zamykał w 2–3 sprintach**. GhostLab to już nie jest "kolejna aplikacja". To jest **drugie IDE w grze**. AppForge jest IDE do zwykłych aplikacji. GhostLab będzie IDE do narzędzi systemowych.

Ja bym to rozłożył na około **8 sprintów**, ale każdy z nich jest mały i daje widoczny efekt.

---

# Sprint 17 — GhostLab Workspace

Budujemy środowisko.

```
GhostLab

Projects

Templates

Research

Marketplace

Documentation
```

Nic jeszcze nie tworzy.

Po prostu wygląda jak laboratorium.

---

# Sprint 18 — Project Manager

Pojawia się:

```
New Project

Open Project

Delete

Rename
```

Powstaje:

```
files/projects/pro_system/
```

czyli GhostLab zaczyna mieć własne projekty.

---

# Sprint 19 — Templates

Pojawiają się szablony.

```
Financial Sniffer

Friend Kicker

Security Panel

System Log Reader

Arsenal Cleaner
```

Kliknięcie:

```
Create Project
```

i powstaje pierwszy projekt.

---

# Sprint 20 — Editor

Największy sprint.

Każdy template otwiera własny edytor.

Np.

Financial:

```
Steal %

Detection %

Cooldown

Messages

Rewards
```

Friend:

```
Success %

Detection %

Targets

System messages
```

Security:

```
Allowed switches

Presets

Rules

Conflict matrix
```

To już nie jest formularz.

To są dedykowane edytory.

---

😂 Dokładnie. GhostLab jest studnią bez dna. W pewnym momencie trzeba powiedzieć **"v1.0 jest wystarczająco dobre"**, bo inaczej jeszcze przez miesiąc będziemy dodawać kolejne zakładki.

Ja bym zamknął **GhostLab v1.0** w **5 sprintach** i koniec. Reszta trafi do roadmapy gry.

---

# Sprint 21 — Build System

**Cel:** pierwszy "compiler", ale jeszcze bez publikacji.

Powstają:

```
Validate
Compile
Preview
Export
```

### Compile

* sprawdza blueprint
* buduje artefakt
* zapisuje go w projekcie

np.

```json
builds: [
    {
        "version": 1,
        "created_at": "...",
        "status": "compiled"
    }
]
```

Jeszcze NIE tworzy aplikacji.

Export:

```
ghost_project.glab
```

czyli snapshot projektu.

---

# Sprint 22 — Publisher

To już koniec IDE.

Pojawia się:

```
Publisher
```

Nie "Publish".

Publisher ma pipeline:

```
Blueprint

↓

Compile

↓

Artifact

↓

Publisher

↓

Googleplex
```

Publisher:

* sprawdza build
* sprawdza Validate
* generuje prawdziwy:

```
pro-system-tool
```

* zapisuje do katalogu Googleplex

Na tym kończy się IDE.

---

# Sprint 23 — Ghost Exchange

Nie Marketplace.

Ghost Exchange.

Sekcje:

```
Official

Community

Blueprints

Templates
```

Na razie:

Official.

Community jako placeholder.

To jest odpowiednik:

Visual Studio Marketplace.

---

# Sprint 24 — Research

Nie rozwijamy narzędzi.

Rozwijamy GhostLaba.

Powstaje:

```
Finance

Intel

Security

Social

Apps
```

Ale jeszcze bez mechaniki.

Research tylko:

```
locked

↓

coming soon
```

czyli przygotowanie pod przyszłe wersje.

---

# Sprint 25 — GhostLab v1.0 Polish

Ostatni sprint.

Nie dodajemy funkcji.

Robimy polish.

* animacje
* ikony
* tooltipy
* onboarding
* statusy
* changelog
* loadingi
* UX
* skróty klawiaturowe
* lepszy wygląd IDE

Na końcu:

```
GhostLab

v1.0
```

---

## I to jest koniec.

Dalsze rzeczy:

```
Research Tree

Compiler Optimizer

Ghost Marketplace Community

AI Templates

Plugin SDK

Blueprint Sharing

AI Assistant

Versioning

Rollback

Dependency Graph
```

to już **GhostLab v2.0**.

---

## Czyli finalnie:

| Sprint | Nazwa                | Efekt                                |
| ------ | -------------------- | ------------------------------------ |
| **21** | Build System         | Compile, Preview, Export             |
| **22** | Publisher            | Publikacja do Googleplex             |
| **23** | Ghost Exchange       | Biblioteka szablonów i blueprintów   |
| **24** | Research Foundation  | Fundament drzewa badań               |
| **25** | GhostLab v1.0 Polish | UX, wygląd, onboarding, dopracowanie |

💚 I to bym naprawdę zamknął jako **GhostLab v1.0**. Jest kompletna ścieżka życia narzędzia:

```
Googleplex
        ↓
kup GhostLab
        ↓
Workspace
        ↓
Projects
        ↓
Templates
        ↓
Editor
        ↓
Validate
        ↓
Compile
        ↓
Publisher
        ↓
Googleplex
        ↓
Instalacja
        ↓
Player Hack Access
        ↓
Użycie
```

Na tym etapie GhostLab jest pełnoprawnym IDE. Wszystkie kolejne pomysły (AI, pluginy, społeczność, rozbudowane badania, zależności między modułami) mogą spokojnie poczekać na kolejne wersje gry, zamiast blokować rozwój innych systemów.




