# GhostSignal — opis produktowy 15-minutowego finału

Status: `PRODUCT BRIEF / ŹRÓDŁO DLA SPRINTÓW 139–140`

Data przyjęcia: `2026-09-10`

Dokument opisuje zamierzony odbiór finału. Realizacja została rozdzielona na
dwie bramki wykonawcze:

- `Sprint 139` — natychmiastowy start show, globalna blokada gameplayu,
  kontrolowany restart GhostSystemu i pewna dostępność Signal Registry;
- `Sprint 140` — pełna reżyseria wizualna, dźwiękowa i informacyjna piętnastu
  minut finału.

Sprint 140 nie może rozpocząć produkcyjnego montażu przed zaliczeniem bramki
Sprintu 139. Ładniejsze show nie może maskować opóźnionego startu, nieszczelnej
blokady ani braku restartu.

Dokumenty wykonawcze:

- `doc/sprints/sprint_139_ghostsignal_activation_restart.md`;
- `doc/sprints/sprint_140_ghostsignal_15_minute_finale.md`.

## Główne założenie

Całe około 15-minutowe show GhostSignal powinno wynikać bezpośrednio z idei Ghost Network:

**części → maszyny → sieć → GhostSignal → wysłanie → rozpad starego stanu → rekonstrukcja systemu → nowy cykl.**

Nie powinno to być przypadkowe zestawienie efektów z gry. Wszystkie elementy wizualne, logi, statystyki i dane powinny być podporządkowane właśnie temu przebiegowi.

## Rola Ollamy

Ollama nie powinna podczas show generować nowych narracji dotyczących właśnie zakończonego sygnału.

W momencie trwania prezentacji Ollama przygotowuje już zestaw nowych narracji dla kolejnego GhostSignal. Te około 15 minut przerwy jest właśnie między innymi po to, żeby dać jej czas na wykonanie tej pracy.

W samym show wykorzystujemy więc:

* teksty wcześniej wygenerowane przez Ollamę,
* historyczne narracje z kończącego się sygnału,
* historyczne newsy,
* wcześniejsze komunikaty,
* zapisane opisy eventów,
* inne teksty, które powstały podczas rozgrywki.

Dzięki temu możemy mocno wykorzystać efekty i narrację Ollamy bez dokładania jej nowych zadań w momencie, kiedy przygotowuje już kolejny cykl.

---

## 00:00–03:00 — CZĘŚCI

Show zaczyna się natychmiast po rozpoczęciu procesu GhostSignal.

Głównym elementem są wszystkie 20 części Ghost Network.

Można stworzyć animację, w której części pojawiają się jako jeden układ lub wzór.

Poszczególne części:

* przemieszczają się,
* łączą się ze sobą,
* pojawiają się pomiędzy nimi połączenia,
* jedna część się aktywuje,
* inna zmienia stan,
* kolejne elementy układają się w większą strukturę.

W tle mogą pojawiać się historyczne logi i dane związane z tymi częściami:

* kto je znalazł,
* kto je przejął,
* gdzie były aktywowane,
* jakie terytoria były z nimi związane,
* jakie konflikty występowały,
* historyczne komunikaty Ollamy,
* newsy i wydarzenia związane z ich przebiegiem.

Wszystkie te dane są jednak tłem dla głównej animacji części.

---

## 03:00–06:00 — MASZYNY I GHOST NETWORK

Części zaczynają składać się w maszyny.

Pokazujemy moment, w którym osobne elementy przestają być pojedynczymi częściami i zaczynają tworzyć większy system.

Maszyny łączą się następnie ze sobą i powstaje Ghost Network.

Można wykorzystać:

* linie połączeń,
* glitche mapy,
* efekty BlackNetu,
* efekty Secret Path,
* logi,
* historyczne informacje,
* terytoria,
* aktywacje,
* dane o klanach,
* dane o właścicielach części.

Wszystko powinno wyglądać tak, jakby przez kilka minut cały system składał się w jedną działającą sieć.

---

## 06:00–08:00 — UZBROJENIE I WYSŁANIE GHOSTSIGNAL

Gotowa sieć przechodzi w stan GhostSignal.

To powinien być jeden z najmocniejszych momentów całego show.

Połączenia pomiędzy maszynami dochodzą do pełnej aktywacji, system się uzbraja i rozpoczyna transmisję.

Sam moment wysłania sygnału musi być bardzo wyraźny.

Powinien pojawić się mocny efekt:

* błysk,
* glitch,
* zakłócenie całego interfejsu,
* reakcja mapy,
* reakcja pulpitu,
* reakcja Ghost Network,
* odpowiedni asset SFX,
* charakterystyczny pisk lub inny mocny efekt dźwiękowy związany z transmisją.

To nie może wyglądać jak zwykłe osiągnięcie 100% na pasku.

Ma być jasne:

**GhostSignal właśnie został wysłany.**

---

## 08:00–12:00 — REKONSTRUKCJA SYSTEMU

Po wysłaniu sygnału rozpoczyna się drugi duży etap show.

System zaczyna się przebudowywać.

Teraz można pokazać faktyczne konsekwencje zakończenia GhostSignal.

Pojawiają się terytoria.

System pokazuje:

* które terytoria pozostały,
* które zostały usunięte,
* które zostały skonsumowane,
* które brały udział w konfliktach,
* jak zmienił się układ świata.

Następnie pojawiają się nagrody.

Pokazywane są wypłaty i efekty zakończenia cyklu.

W tym momencie mogą zacząć pojawiać się również gracze:

* nicki,
* klany,
* profesje,
* supermoce,
* udział w Ghost Network,
* wyniki,
* osiągnięcia,
* zdobyte terytoria,
* udział w konfliktach,
* pozostałe statystyki dostępne w systemie.

---

## 12:00–14:00 — ODTWARZANIE CHAOS

System zaczyna odbudowywać pozostałe elementy gry.

Pojawiają się:

* narzędzia z Googleplexu,
* Pro Tools,
* terminal,
* komendy,
* aplikacje,
* pliki,
* rodzaje plików,
* dane,
* logi,
* BlackNet,
* newsy,
* pozostałe systemy CHAOS.

Nie muszą być one głównym elementem fabularnym. Mogą tworzyć tło rekonstrukcji systemu.

Chodzi o pokazanie, że po wysłaniu GhostSignal cały CHAOS zaczyna się ponownie składać i przygotowywać do dalszego działania.

Można tu wykorzystać jak najwięcej istniejących efektów, assetów i historycznych materiałów Ollamy, żeby ekran cały czas żył.

---

## 14:00–15:00 — RANKING I NOWY CYKL

Na końcu z wszystkich zebranych danych buduje się wynik zakończonego GhostSignal.

Pojawia się ranking:

* graczy,
* klanów,
* terytoriów,
* wyników,
* pozostałych statystyk zakończonego cyklu.

To jest końcowe podsumowanie świata, który właśnie został zamknięty.

Następnie system kończy rekonstrukcję.

Interfejs zostaje zamknięty i następuje restart.

Po restarcie:

* uruchamia się kolejny cykl Ghost Network,
* dostępna jest aplikacja ze statystykami poprzedniego sygnału,
* Ollama ma już przygotowane lub kończy przygotowywanie narracji dla nowego sygnału.

## Cała idea show

To nie powinien być 15-minutowy ekran oczekiwania.

To ma być pokazanie procesu:

**20 części składa się w maszyny → maszyny tworzą Ghost Network → sieć uzbraja GhostSignal → sygnał zostaje wysłany → stary świat zostaje rozliczony → terytoria są konsumowane i redukowane → wypłacane są nagrody → pojawiają się gracze i ich wyniki → CHAOS rekonstruuje swoje systemy → powstaje ranking → rozpoczyna się kolejny cykl.**

Pozostałe elementy gry — BlackNet, newsy, terminal, Googleplex, Pro Tools, pliki, logi, mapę, glitche, Secret Path i historyczne teksty Ollamy — wykorzystujemy jako warstwę wizualną i informacyjną wokół tego głównego procesu.
