# Sprint 143 — tabela konsekwencji, recydywa, ograniczenia i więzienia

Status: 143.1 ROZPOCZĘTY 21 IX 2026 na polecenie autora „lecimy dalej”.
Tabela i kartoteka działają już z 142.6; rollout poza main potwierdzony na robot.
Przygotowanie kontraktu 143 nie zastępuje brakujących potwierdzeń odbioru 142.7.
Aktywacja aresztu wymaga uzgodnionych reguł i testów kolejnych etapów.
Rozszerzony audyt wejściowy ukończony przed developmentem; decyzje reuse
i granice obecnego MVP opisuje [raport](../audits/response_consequences_2026_09_16.md).
Sprint realizuje nowe sankcje, nie służy odkrywaniu istniejącego mechanizmu.
Cel: rozszerzyć sprawdzony executor przez wersjonowane rodzaje sankcji,
bez osobnego systemu kar i bez pełnych odczytów profilu.

Zakres zatwierdzony: coraz surowsze kary zależne od przewinienia, eskalacji
i recydywy; blokady ruchu/teleportów/systemu, w tym Cybernera, oraz osadzenie
w więzieniach z zatwierdzonego katalogu. Wylogowanie nie kasuje sankcji.

## 143.1 — wersjonowana tabela konsekwencji i recydywa

Stan prac: [kontrakt 143.1](../runbooks/sprint_143_1_detention_policy.md).
21 IX autor zatwierdził ograniczenia stopni 6–9, losowe więzienie na wyrok,
powrót do pozycji sprzed aresztu i brak nowych kar w areszcie. Zatwierdzono
kaucję 250/500/750 tys./1 mln HC, płatną przez aresztowanego lub innego
gracza, ze zwolnieniem bez kasowania kartoteki. Każdy areszt ma gwarantowaną
jedną wiadomość prywatną Cybernera na cały wyrok, także na stopniu 6;
reconnect nie odnawia limitu. Szczegóły zapisano w kontrakcie 143.1.

Aktualizacja 20 IX 2026: bazowa tabela została zatwierdzona przed 142.6
i zapisana w `config.py: RESPONSE_CONSEQUENCE_TABLE`; przygotowano canonical
kartotekę. Obowiązuje `doc/runbooks/consequence_table_v1.md`. 143 rozszerza
tę samą tabelę i executor, nie tworzy osobnej skali więziennej.

Tabela jest konfiguracją backendu, nie zestawem warunków w frontendzie.
Każda decyzja zapisuje wersję policy, użyte współczynniki i wybrany poziom.

| Wejście | Źródło/zasada |
|---|---|
| Poziom i eskalacja incydentu | Canonical stan i historia incydentu z 142 |
| Liczba incydentów gracza | Unikalne inicjacje przypisane graczowi; bez duplikatów publikacji |
| Kolejne zatrzymania/recydywa | Trwałe receipts zatrzymań, nie liczba requestów detektora |
| Kamery | Liczba wykrytych/wyłączonych, skuteczność i aktualność osłony z 142 |
| Rola gracza | Inicjator/postronny; szansa 80/30 oddzielona od surowości kary |
| Pozostałe modyfikatory | Wyłącznie zweryfikowane reguły współdzielone z aktywnymi częściami/Super Powers |

Zatwierdzona drabina: stopień 1 mandat ×1, 2 mandat ×2, 3 jedno narzędzie,
4 dwa narzędzia, 5 trzy narzędzia + mandat ×3, 6–9 areszt 5/10/15/20 minut.
Początek: L2→1, L3→3, L4→5, L5→6. Każda wcześniejsza wykonana kara dodaje
jeden stopień, wspólny licznik gracza; maksimum 9. Szczegółowy zestaw
ograniczeń aplikacji dla stopni 6–9 zatwierdzono w kontrakcie 143.1.

Recydywa zwiększa surowość według jawnych progów/okna historii i limitów,
bez wielokrotnego liczenia tego samego spotkania. Jedna kara nie może
samoczynnie generować kolejnych zatrzymań w więzieniu. Zatwierdzono licznik
lifetime bez resetu/decay, brak dokładania kar podczas aresztu i maksimum
20 minut online na wyrok; wykorzystać tabelę reuse z 142.

## 143.2 — trwały model sankcji i czas odbywania

22 IX 2026: gotowy wewnętrzny store i testy zegara/limitu wiadomości;
[kontrakt integracji](../runbooks/sprint_143_2_sanction_store.md).
Podpięcie workera/logoutu i rzeczywistego wykonania pozostaje do integracji
z blokadami oraz transportem. Areszt nadal nieaktywny w runtime.

Mały canonical store: sanction_id, actor, encounter/receipt, rodzaj, powód,
starts_at, duration_seconds, remaining_seconds, rozliczony czas obecności,
status, wersja, parametry oraz historia zmian. Sam wall-clock expires_at
nie wystarcza: wylogowanie na 2–3 h nie może automatycznie odbyć wyroku.
Zatwierdzona realizacja: serwerowe rozliczanie czasu online, pauza offline,
kontynuacja po powrocie; granice heartbeat/timeout i wiele kart wymagają
jednoznacznej reguły. Nie ufać timerowi ani deklaracji online klienta.
Indeks aktywnych sankcji po graczu; typy movement_block,
teleport_block, incarceration, communication_block i ograniczenia aplikacji.
Idempotentne nałożenie, przedłużenie według jawnej reguły i zwolnienie.

## 143.3 — egzekwowanie ruchu i teleportów

22 IX 2026: zaimplementowano wspólną bramkę canonical/legacy pozycji,
atomową płatność biletu i przejazd oraz obsługę odmowy na mapie.
[Inwentaryzacja writerów i walidacja](../runbooks/sprint_143_3_movement_gate.md).
Brak aktywacji nakładania aresztów; transport serwerowy i jego podłączenie
pozostają w 143.4.

Jedna backendowa bramka we wszystkich drogach zmiany pozycji: jazda,
ustawienie pozycji, bilety/teleport, CTA BlackNet/GN, narzędzia i inne
przeniesienia. Najpierw zinwentaryzować wszystkie writery pozycji.
Kontrola przed zakupem/pobraniem kosztu oraz przed commit; zero utraty
biletu/HC po odmowie, race z nakładaniem sankcji rozstrzygany atomowo.
Odróżnić dobrowolny ruch od uprawnionego transportu do/z więzienia:
wewnętrzna capability serwera, nigdy flaga bypass z klienta.
UI: wspólny powód blokady i czas; serwer egzekwuje też bez UI.

## 143.4 — więzienia i zwolnienie

22 IX 2026: zaimplementowano transport, odliczanie online, odzyskiwanie
wyroków i atomową kaucję. [Kontrakt i odbiór 143.4](../runbooks/sprint_143_4_detention_transport.md).
Flaga nakładania aresztów pozostaje wyłączona do 143.5; odbiór produkcyjny
jeszcze przed nami.

Katalog v1 dodany 16 IX 2026: `response_network/prison_catalog.py` zawiera
10 więzień z zatwierdzonej listy autora, z zachowaniem ID, nazw, typów
i współrzędnych. `fullName` ujednolicono do `full_name`; alias zachowany.
`list_prisons()` i `get_prison(id)` zwracają niezależne słowniki bez odczytów
profilu/bazy. Nieznany ID oznacza KeyError, bez losowego zastępstwa.
Katalog nie nakłada sankcji, nie publikuje markerów ani nie teleportuje.
Zatwierdzono zwolnienie do zapisanej pozycji sprzed aresztu — współrzędne
katalogu są miejscami osadzenia, nie miejscami powrotu.
W jednej transakcji zapisać sankcję, miejsce powrotu, przemieszczenie,
zatrzymanie jazdy/tras i outbox mapy. Nie resetować przypadkowo PvP/cooldownów.
Backendowy stan pozostałej kary, odporny na zmianę zegara klienta, restart
i disconnect. Jeden idempotentny mechanizm zwolnienia, bounded worker i kontrola
przy wznowieniu sesji. Bez kar dla nieobecnych z zaległych wykryć.

Zatwierdzono losowanie więzienia raz na wyrok, powrót do zapisanej pozycji
sprzed aresztu i brak dokładania kar podczas osadzenia. Odliczanie korzysta
z potwierdzonej obecności i generacji sesji po stronie serwera.
Odrzucona wcześniejsza propozycja: automatyczne upływanie wyroku w czasie
offline. Brak nowych kar offline nie usuwa wcześniej nałożonych sankcji.
Cykl publicznego incydentu jest niezależny od odbywania kary: uwięzienie ani
wylogowanie inicjatora nie usuwa publicznego miejsca i jego odbiorców.

## 143.5 — ograniczenia systemowe i komunikacja

22 IX 2026: zaimplementowano bramki HTTP/commit, wspólny limit wysłania
Cybernera, filtrowanie World i interfejs statusu/kaucji. Szczegóły oraz
scenariusz odbioru: [runbook 143.5](../runbooks/sprint_143_5_detention_capabilities.md).
Odbiór w grze pozostaje do wykonania; 143.5a jest osobnym zadaniem.
23 IX: autor potwierdził transport/powrót stopnia 6, zamrożenie czasu offline,
World read-only i wspólny limit jednej wiadomości na stopniu 7, odbiór odpowiedzi
oraz zwolnienie za kaucją. Stopnie 8–9 wymagają jeszcze odbioru w grze.
Po odbiorze zmieniono UX: więzienie/timer/progres w miejscu CEL, kaucja tylko
przy wiadomości z adnotacją cenzury i potwierdzeniem CHAOS. Opłaty trafiają do
skarbca `admin`; przygotowano idempotentną korektę wcześniejszej kaucji.
Wdrożenie i testy: [kaucja, Cyberner i skarbiec](../runbooks/sprint_143_bail_cyberner_treasury.md).
Po spięciu 143.5 ustawiono `CHAOS_RESPONSE_DETENTION_ENABLED=true` we
wszystkich ecosystemach; wcześniejsza blokada aktywacji z 143.4 jest zdjęta.

Przygotować rejestr typów sankcji i jeden kontrakt capability. Tabela określa
dostęp do ruchu, teleportów, Cybernera oraz pozostałych aplikacji. Dla
najostrzejszego poziomu gameplay pozostawia Web Dragona i radio, a od 143.5a
także mapę jako zablokowany widok więzienia; obsługa
sesji, wyroku, komunikatów systemowych i bezpiecznego wyjścia nadal działa.
Backend blokuje niedozwolone akcje z mapy, terminala, desktopu i bezpośredniego
API, także z wcześniej otwartego okna. UI pokazuje powód i pozostały czas.
World: stopień 6 pełny dostęp, 7 odczyt, 8–9 blokada. Wszystko poza World
jest prywatne: jeden wspólny limit wysłania na wyrok; odbiór i czytanie
zawsze dostępne, także na stopniu 9. Zachować uprawnienia do rozmów/klanów.
Nie tworzyć furtki przez inny launcher. Zweryfikować rzeczywistą tożsamość
aplikacji Web Dragon w katalogu.

## 143.5a — efekty mapowe przy nadaniu konsekwencji

Aktualizacja wizualna autora 24 IX 2026 (nadrzędna wobec wcześniejszego opisu
show): kompozycja Super Powers, duży PNG centralnie i drżący tytuł pod nim
(`chaos-ghost-ability-title`, animacja `ghost-ability-text-quake`). Tło samego
show przyciemnia mapę do **80%**. Stały widok więzienia nadal ma 60%; podczas
show dodatkowe 50% daje łącznie 80%, bez podwójnego przygaszenia. SFX oraz
timing pozostają bez zmian. Układ pionowy skaluje asset do wysokości okna.

Rozszerzenie autora 23 IX 2026: mapa pozostaje dostępna również na stopniu 9.
Podczas aresztu jest widokiem więzienia: ciemne tło 60%, najbliższy podstawowy
zoom mapy (pierwszy poziom, `baseZoom`, bez bonusów supermocy), stały fokus na
zapisanej pozycji więzienia, brak oddalania i przesuwania. Po zwolnieniu wraca
obsługa mapy i autorytatywna pozycja powrotu; dawny cel nie wraca. Dostęp do mapy
nie odblokowuje skanowania, hakowania, celowania, podróży ani supermocy.

Nie zasłaniać mapy komunikatem „aplikacja niedostępna”. Okno CHAOS wyroku/kaucji
podaje rzeczywisty czas i nazwę zakładu: „Zostałeś skazany na X min więzienia
w zakładzie karnym Y. Twoje prawa zostały ograniczone na czas odbywania kary”,
prawo do jednej wiadomości (lub informację o wykorzystaniu), czas online i kaucję.
Belka więzienia otwiera to samo okno; przycisk zapłaty tylko przy wystarczającym HC.

Implementacja: prywatna delta `response.consequence_executed` zapisana w tej
samej transakcji co kara; endpoint claim przyznaje prezentację tylko właścicielowi
wykonanego receipt, maksymalnie 60 s po wykonaniu, raz w całej bazie. Powtórki,
historia i początkowa synchronizacja nie odtwarzają show. Widoczny desktop bez
otwartej mapy pomija PNG/SFX, ale pokazuje okno wyroku; nie odkłada show do później.
Karty w tle nie przejmują prezentacji. Zamknięcie mapy zatrzymuje trwający efekt.
Dziewięć mapowań i fallbacki długości są w `static/js/consequence_show.js`,
SFX w istniejącym manifeście. Audio `playing`/`ended` steruje efektem; brak startu
w 1,5 s anuluje audio i uruchamia fallback bez późnego replay. Komunikaty kary
nie dublują systemowego SFX. Odbiór wizualny na wdrożeniu pozostaje wymagany.

Ustalenie autora 23 IX 2026: osobna ciemna warstwa tła ma alpha **60%**
(`rgba(0,0,0,0.6)`), aby mapa przebijała przez tło. Nie obniżać opacity
całego show ani tekstu/PNG. **Cały czas show = czas jego SFX**: wspólny
start i koniec, animacje wewnątrz długości audio, bez dodatkowego hold
i narzuconego minimum. Przy mute/autoplay/błędzie audio używać długości
tego samego pliku z metadanych lub zapisanego fallbacku, bez późnego replay.
Komplet i pomiary: [audyt assetów 143.5a](../runbooks/sprint_143_5a_asset_audit.md).

Zakres dodany przez autora 22 IX 2026. Wszystkie stopnie konsekwencji 1–9,
od mandatów po najwyższy areszt, otrzymują osobny asset uruchamiany na mapie
w momencie skutecznego nadania kary. Chodzi o stopień przyznanej konsekwencji,
nie sam poziom incydentu L1–L5 ani wykrycie przez patrol.

Oprawę i sposób odtwarzania adaptować z istniejących rozwiązań Secret Path
oraz Super Powers: zachować styl CHAOS, spójność animacji, typografii i
kompozycji. Przed implementacją sprawdzić istniejące mechanizmy i wykorzystać
je zamiast tworzyć niezależny system efektów.

Assety powstaną osobno. Zadaniem implementacji jest konfigurowalne mapowanie
stopnia/rodzaju wykonanej kary na dostarczony asset oraz uruchomienie efektu.
Katalog na PNG: `static/images/consequences/show/`; nazwy dziewięciu plików
i wskazówki eksportu zawiera [README assetów](../../static/images/consequences/show/README.md).
Do każdego stopnia dochodzi osobny SFX MP3 w `static/audio/sfx/consequences/`.
[README SFX](../../static/audio/sfx/consequences/README.md) określa nazwy,
charakter i zalecane długości. Odtwarzanie przez wspólny GameSfx, zsynchronizowane
z obrazem po commit kary, z respektowaniem ustawień dźwięku i dedupe receipt.
Nie dublować dźwięku przez komunikat systemowy; brak MP3/autoplay nie blokuje
show ani kary. Dziewięć eventów `consequence.stage_1`–`consequence.stage_9`
zarejestrowano w manifeście i podłączono do wykonanych konsekwencji.
Przewidzieć warianty mandatu/kary finansowej, konfiskaty narzędzi, kary
łączonej oraz wniosku sądu o areszt. Stopnie 1 i 2 mają odrębne assety,
podobnie 3, 4, 5 oraz każdy z 6–9. Wariant aresztu podaje czas wynikający
z rzeczywiście zapisanego wyroku (obecnie 5/10/15/20 minut). Kwoty, liczby
narzędzi i czas czerpać z wyniku backendu; nie wyliczać ponownie w animacji.
Nazwa wizualna „wniosek sądu o areszt” nie dodaje osobnego losowania ani
nowego etapu zatwierdzania kary.

Wyzwalaczem jest potwierdzone wykonanie kary, po commit transakcji, z trwałym
identyfikatorem receipt/sankcji. Samo `selected`, obserwacja, `avoided`,
`unsupported` lub rollback nie odtwarzają efektu. Powtórny event, reconnect
i odtworzenie stanu nie mogą ponownie prezentować tej samej kary jako nowej.
Efekt prezentować ukaranemu graczowi, zgodnie z obecnym kontraktem widoczności;
nie publikować automatycznie prywatnych danych kary innym graczom.

Brak assetu lub niedostępna mapa nie blokuje wykonania kary ani komunikatu
systemowego. Przed implementacją ustalić techniczne zachowanie przy zamkniętej
mapie i kilku kartach, zachowując rozróżnienie nowego zdarzenia od historii.
Odbiór wizualny wymaga dostarczenia assetów; samo podpięcie identyfikatorów
nie oznacza ukończenia oprawy.

## 143.6 — testy, migracja, odbiór

- Każda droga ruchu/teleportu odmawia podczas sankcji, działa po końcu;
  próba bezpośredniego POST nie omija blokady.
- Wygaśnięcie dokładnie na granicy czasu, reconnect, restart workera,
  powtórny transport/zwolnienie, brak lub zmiana miejsca powrotu,
  dwie sankcje równolegle, race z zakupem i zmianą pozycji.
- Wylogowanie na 2–3 h: pozostała kara nie zeruje się; publiczny incydent
  nadal podlega własnemu cyklowi, inni gracze widzą miejsce. Wiele kart nie
  przyspiesza odbywania wyroku, fałszywy heartbeat nie zmienia wyniku.
- Granice poziomów 5/10/15/20, recydywa i dedupe zatrzymań, liczby kamer,
  aktywne Super Powers, powody decyzji; Web Dragon/radio dostępne, zabronione
  aplikacje blokowane również przez bezpośrednie API i już otwarte okna.
- Desktop/mobile: timer i wyjaśnienie; mapy innych graczy otrzymują delta
  pozycji zgodnie z widocznością; żadnych nowych wycieków pozycji więźnia.
- Efekty mapowe: właściwy osobny asset dla każdego stopnia 1–9, zgodne
  z backendem parametry kary i czas aresztu; spójność z Secret Path/Super Powers.
  Właściwy MP3 zsynchronizowany z PNG, ustawienia SFX i wyciszenie respektowane;
  brak podwójnego audio przy retry/reconnect i brak zaległego odtwarzania po autoplay.
  Brak efektu przed commit, po rollback i dla niewykonanej kary; dedupe przy
  retry/reconnect oraz poprawne zachowanie bez assetu i przy zamkniętej mapie.
- Profile 35 MB: zero full read/write, bounded liczba zapytań i pracy workera.
- Migracja jawna z backup/verify i flagami per typ; kill switch nowych kar
  nie może uniemożliwiać zwolnienia już uwięzionych.

DoD: canonical efekty i recovery PASS, wszystkie writery zabezpieczone,
uzgodniony balans i reguły wyroków, odbiór autora, runbook ręcznego zwolnienia
z audytem i kontrolą uprawnień, bez kasowania dowodów naliczonych kar.
