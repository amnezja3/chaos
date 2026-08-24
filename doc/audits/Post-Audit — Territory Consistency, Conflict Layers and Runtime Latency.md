# Post-Audit — Territory Consistency, Conflict Layers and Runtime Latency

Status:

`GO remains blocked`

Zakres:

* lifecycle filarów i innerów po konfliktach,
* ownership i abandon,
* engagement geometry,
* nakładające się warstwy konfliktów,
* worker reconciliation,
* SQLite writer contention,
* regresja latency w mapie i aplikacjach.

Audyt nie wprowadzał hotfixów.

---

# 1. Executive summary

Audyt potwierdził, że obserwowane problemy nie są przypadkowymi błędami renderera.

Istnieją trzy powiązane regresje konstrukcyjne:

1. obiekty przejęte w wyniku konfliktów nie przechodzą przez ten sam kanoniczny lifecycle ownership co obiekty powstałe ze skanu;

2. lifecycle engagementu jest obecnie utożsamiony z lifecycle widocznej geometrii, przez co stare warstwy `changing` pozostają renderowane równolegle z nowymi;

3. web i worker konkurują o jeden SQLite writer lock, a `busy_timeout=15000` bardzo dobrze odpowiada obserwowanym opóźnieniom rzędu 15–20 sekund.

Nie znaleziono dowodu na jedną prostą pętlę:

`publication → worker → rebuild → publication`

Efekt „lawiny” warstw wynika raczej z obecnego kontraktu identity/hysteresis engagementów oraz tego, że frontend nadal traktuje `changing` jako aktywną geometrię.

---

# 2. Finding A — niespójny lifecycle obiektów pokonfliktowych

## Objaw

Obiekty powstałe bezpośrednio ze skanu zachowują się poprawniej niż obiekty odziedziczone po konfliktach.

Dla filarów i innerów przejętych po konflikcie obserwowano:

* brak menu `ZABEZPIECZ / PORZUĆ`,
* menu pojawiające się wybiórczo,
* brak usunięcia markera po `PORZUĆ`,
* brak przebudowy terytorium,
* marker znikający chwilowo i wracający po refreshu,
* różnice pomiędzy stanem bieżącego frontendu a stanem po ponownym pobraniu snapshotu.

## Przyczyna

W systemie istnieją obecnie dwie różne ścieżki abandon.

### Mapa

Mapa używa atomowego usunięcia z:

`captured_targets`

oraz kolejki workera.

Reference:

`run.py:19046`

### Territory Control

Territory Control nadal:

* usuwa obiekt po współrzędnych,
* modyfikuje profil,
* synchronicznie przebudowuje terytorium w requestcie.

Reference:

`run.py:22717`

Są to dwa różne kontrakty dla tej samej operacji gameplayowej.

---

# 3. Finding B — transfer ownership po konflikcie jest niepełny

Przejęcie całego otoczonego klastra:

* usuwa obiekt poprzedniemu właścicielowi,
* zapisuje go nowemu właścicielowi w `captured_targets`,
* ale nie wykonuje analogicznego transferu CAS w:

`territory_target_ownership`.

Reference:

`run.py:6877`

Przejęcie pojedynczego filaru korzysta natomiast z registry oraz reconciliation set.

W efekcie jeden obiekt pokonfliktowy może jednocześnie posiadać:

* nowego właściciela w `captured_targets`,
* starego albo brakującego właściciela w ownership registry,
* nadal istniejący wpis filaru konfliktowego,
* inną reprezentację w profilu.

To wyjaśnia wybiórcze zachowanie obiektów po konflikcie.

---

# 4. Wniosek dla ownership

Musi istnieć **jeden kanoniczny transfer ownership** niezależnie od tego, czy obiekt:

* pochodzi ze skanu,
* jest filarem konfliktu,
* jest innerem,
* został przejęty jako pojedynczy filar,
* został przejęty jako element całego klastra.

Nie mogą istnieć osobne reguły ownership zależne od źródła obiektu.

Docelowo source of truth dla ownership musi być spójny z aktualnym post-130 registry/CAS.

`captured_targets`, profile projection oraz presentation layer mają wynikać z kanonicznego wyniku, a nie stanowić konkurencyjnych źródeł prawdy.

---

# 5. Wniosek dla PORZUĆ

Musi istnieć **jeden kanoniczny endpoint / command abandon**.

Operacja powinna korzystać z:

`registry / ownership CAS`
→ `canonical removal`
→ `reconciliation queue`
→ `worker rebuild`
→ `publication`
→ `map refresh/delta`

Nie powinny istnieć równolegle:

* abandon przez atomowe registry,
* abandon przez współrzędne,
* abandon modyfikujący profil bez kanonicznego ownership,
* synchroniczny rebuild w jednym endpointcie i asynchroniczny rebuild w drugim.

---

# 6. Finding C — engagement `changing` pozostaje aktywną geometrią

Aktualny kontrakt engagementów powoduje utrzymywanie starych warstw.

`list_active()` nadal zwraca engagementy w stanie:

`changing`

Reference:

`database.py:3029`

Jeżeli nowa geometria nie przecina bbox poprzedniej:

1. powstaje nowy `engagement_id`,
2. poprzedni engagement przechodzi do `changing`,
3. stary engagement jest rozwiązany dopiero przy kolejnym braku publikacji.

Reference:

`database.py:3214`

Frontend usuwa tylko:

* `resolved`,
* `closed`.

Reference:

`map_template.html:2641`

W konsekwencji `changing` nadal jest renderowane.

---

# 7. Skutek dla konfliktów

W jednym momencie mogą być widoczne:

* aktualna geometria,
* poprzednia geometria oznaczona jako `changing`,
* kolejna geometria wynikająca z nowego rebuilda.

Przy konflikcie wieloosobowym liczba zmian geometrii jest większa, dlatego efekt staje się szczególnie widoczny.

Konflikty `1v1` również mogą akumulować warstwy, ale zmiany są mniej gwałtowne.

To tłumaczy obserwację:

`multi-conflict = lawina warstw`

oraz:

`1v1 = mniej warstw, ale nadal ślady nakładania`.

---

# 8. Test utrwala obecny problem

Istniejący test:

`test_split_creates_parallel_engagement...`

oczekuje dwóch aktywnych engagementów.

Oznacza to, że obecny suite potwierdza kontrakt, który z punktu widzenia mapy powoduje regresję wizualną.

Zielony test nie oznacza tutaj poprawnego zachowania gameplayowego.

---

# 9. Decyzja — rozdzielić lifecycle engagementu od lifecycle geometrii

Engagement może pozostawać logicznie aktywny / przejściowy dla potrzeb:

* audytu,
* historii,
* hysteresis,
* recovery,

ale jego stara geometria nie musi pozostawać renderowalną geometrią mapy.

Należy rozdzielić:

`engagement lifecycle`

od:

`visible geometry lifecycle`.

Stan `changing` nie powinien automatycznie oznaczać:

`render old polygon`.

Po opublikowaniu nowej kanonicznej geometrii poprzednia geometria powinna zostać wycofana z presentation layer bez czekania na kolejny audit cycle.

---

# 10. Finding D — audit interval potęguje widoczny problem

Audit multi-conflict działa domyślnie co około:

`180 s`

Przez ten czas stary engagement może nadal istnieć jako `changing`.

Jeżeli przed kolejnym audytem pojawi się kolejna zmiana geometrii, może dojść następna warstwa.

Nie jest to koniecznie pętla logiczna.

Jest to raczej skutek kombinacji:

* hysteresis,
* opóźnionego resolution,
* `changing` traktowanego jako visible,
* kolejnych rebuildów.

---

# 11. Finding E — wspólny mechanizm latency

Wszystkie procesy korzystają z jednego SQLite.

Konfiguracja:

`timeout = 15`

`busy_timeout = 15000`

Reference:

`database.py:111`

To odpowiada obserwowanym opóźnieniom około:

`15–20 sekund`

w Secret Path.

---

# 12. Secret Path

Po kliknięciu:

* menu natychmiast reaguje,
* stan wizualny przycisku się zmienia,
* właściwy efekt pojawia się dopiero po odpowiedzi backendu.

Overlay powstaje dopiero po odpowiedzi:

`/api/map/aim-target`

Reference frontend:

`map_template.html:2232`

Przed odpowiedzią endpoint:

* zapisuje pełny profil,
* wykonuje synchroniczny hook GhostNetwork.

Reference backend:

`run.py:7664`

Jeżeli request czeka na SQLite writer lock, frontend wygląda jak zawieszony przez kilkanaście sekund.

---

# 13. Pozostałe symptomy latency

Ten sam problem może wpływać na:

* scan terenu,
* oznaczenie targetu,
* teleport,
* uruchamianie profilu,
* WebDragon,
* aplikacje kreatorskie,
* inne requesty wymagające zapisu profilu lub bazy.

To sugeruje problem wspólny dla runtime, a nie pojedynczego UI.

---

# 14. Worker jako źródło contention

Worker:

* regularnie skanuje aktywne konflikty,
* regularnie skanuje engagementy,
* wykonuje rebuild,
* wykonuje reconciliation,
* publikuje wyniki,
* pracuje na tej samej bazie SQLite,
* przy pełnej kolejce może wykonywać joby bez istotnej przerwy.

Dodatkowo część publikacji GhostNetwork może powodować:

* ładowanie wielu profili,
* ładowanie wielu terytoriów,
* dodatkową pracę podczas publication/fan-out.

Nie ma jeszcze serwerowego pomiaru pokazującego procentowy udział każdego elementu.

Diagnoza writer contention jest jednak mocno wsparta przez:

* strukturę kodu,
* wspólną bazę,
* długość `busy_timeout`,
* rzeczywisty czas obserwowanego opóźnienia.

---

# 15. Performance — czego nie robimy

Nie rozwiązujemy problemu przez:

* zwiększenie `busy_timeout`,
* kolejne retry,
* ukrycie lagów spinnerem,
* przeniesienie wszystkich problemów do workera bez pomiaru,
* przypadkowe cache,
* wyłączenie reconciliation.

Najpierw trzeba zmniejszyć czas oraz częstotliwość trzymania writer lock.

---

# 16. Performance — wymagany kierunek

Należy zmierzyć na rzeczywistym runtime:

* czas oczekiwania na SQLite writer lock,
* długość transakcji workera,
* liczbę zapisów na job,
* czas rebuildów,
* czas reconciliation,
* czas publication,
* częstotliwość kolejki przy dużym obciążeniu.

Szczególną uwagę należy zwrócić na operacje, które:

* ładują pełne profile,
* zapisują pełne profile,
* skanują wszystkie konflikty,
* skanują wszystkie engagementy,
* wykonują pełne rebuildy,
* wykonują globalny fan-out.

---

# 17. Latency-sensitive paths

Ścieżki interaktywne gracza powinny wykonywać synchronicznie tylko to, co jest niezbędne do potwierdzenia operacji.

Do przeglądu:

* `/api/map/aim-target`,
* scan,
* target marking,
* teleport,
* profile boot/load,
* WebDragon launch,
* creator apps.

Jeżeli efekt może zostać:

* zapisany jako minimalny canonical state,
* opublikowany,
* dokończony przez worker/reconciliation,

nie powinien blokować response użytkownika bez konieczności.

---

# 18. Regression tests — aktualny wynik

Uruchomiono celowaną regresję obejmującą:

* captured object menu,
* conflict engagement,
* conflict identity,
* map cutover,
* GhostNetwork territory jobs,
* GhostNetwork read-path safety,
* target persistence.

Wynik:

`310 tests — PASS`

Czas:

`94.826 s`

Wniosek:

obecne testy nie wykrywają opisanych regresji, ponieważ część z nich sprawdza kontrakty, które same są źródłem obecnego problemu.

---

# 19. Nowe obowiązkowe testy kontraktowe

Przed zdjęciem blokady GO potrzebne są testy realnych scenariuszy.

## Transfer → abandon

Scenariusz:

`scan`
→ `capture`
→ `conflict`
→ `ownership transfer`
→ `winner receives pillar/inner`
→ `abandon`
→ `worker`
→ `rebuild`
→ `refresh`

Oczekiwane:

* obiekt nie wraca,
* ownership registry jest spójne,
* captured_targets jest spójne,
* marker znika,
* territory rebuild jest poprawny,
* refresh nie przywraca starego stanu.

## Cluster transfer → abandon

Ten sam test dla obiektu odziedziczonego przez przejęcie całego klastra.

## Geometry replacement

Scenariusz:

`geometry A`
→ rebuild
→ `geometry B`

Oczekiwane:

* B jest widoczna,
* A przestaje być widoczna natychmiast po kanonicznej publikacji B,
* brak konieczności czekania na dwa audity.

## Multi-conflict

Seria zmian geometrii nie może zwiększać liczby widocznych historycznych warstw.

## Refresh parity

Stan przed refresh i po refresh musi być semantycznie identyczny.

---

# 20. Warunki odblokowania GO

`GO` pozostaje zablokowane do momentu spełnienia wszystkich poniższych warunków.

1. Jeden kanoniczny transfer ownership dla:

   * pojedynczego filaru,
   * innera,
   * przejęcia całego klastra.

2. Jeden kanoniczny mechanizm abandon oparty o:

   * registry,
   * ownership CAS,
   * reconciliation queue.

3. Brak osobnego synchronicznego lifecycle abandon w Territory Control.

4. Rozdzielenie:

   * engagement lifecycle,
   * visible geometry lifecycle.

5. Stara geometria znika po opublikowaniu nowej kanonicznej geometrii.

6. Test:
   `transfer → abandon → worker → refresh`
   przechodzi dla obiektów pokonfliktowych.

7. Multi-conflict nie akumuluje widocznych historycznych warstw.

8. Zmierzony zostaje rzeczywisty czas writer lock / DB contention na serwerze.

9. Worker nie trzyma writer lock dłużej niż jest to konieczne.

10. Latency-sensitive endpointy nie wykonują pełnych zapisów profilu lub ciężkich hooków synchronicznie, jeśli nie wymaga tego consistency contract.

11. Secret Path, scan, target marking i teleport wracają do akceptowalnej responsywności.

12. Pełna regresja pozostaje zielona po zmianie kontraktów.

---

# 21. Priorytet napraw

Kolejność prac powinna być:

1. ownership consistency,
2. canonical abandon,
3. engagement geometry cleanup,
4. multi-conflict presentation cleanup,
5. server-side DB contention measurement,
6. skrócenie writer transactions,
7. odciążenie latency-sensitive request paths,
8. pełny gameplay regression test.

Najpierw poprawiamy spójność stanu.

Dopiero potem performance.

Nie należy optymalizować runtime, który nadal posiada niespójny ownership.

---

# 22. Granice naprawy

Nie przebudowujemy:

* całego Territory System,
* GhostNetwork,
* Target Registry,
* ownership CAS od zera,
* całego conflict engine,
* SQLite na inną bazę w ramach tej serii prac.

Najpierw wykorzystujemy istniejące mechanizmy post-130 i eliminujemy konkurencyjne legacy paths.

Migracja z SQLite może być rozważona osobno tylko wtedy, jeżeli po skróceniu transakcji i usunięciu zbędnych synchronicznych zapisów nadal pozostanie mierzalnym bottleneckiem.

---

# 23. Final verdict

`GO remains blocked.`

GhostNetwork discovery i podstawowy gameplay części działają, ale aktualny runtime posiada nadal konstrukcyjne regresje w:

* ownership obiektów pokonfliktowych,
* abandon,
* lifecycle widocznej geometrii konfliktów,
* DB contention i latency.

Przed dalszym rozwijaniem systemu należy doprowadzić istniejący runtime do stanu, w którym:

# `canonical state`

# `worker state`

# `map state`

`state after refresh`

oraz interaktywne akcje gracza nie czekają kilkanaście sekund na zwolnienie SQLite writer lock.
