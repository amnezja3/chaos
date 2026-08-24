# Incydent Trollu2 — utrata profilu, błędy sesji i plan odbudowy

Data zgłoszenia: 2026-08-21.

Severity: `P0 — możliwa utrata trwałego progression i naruszenie izolacji kont`.

Status: `OPEN — IMPLEMENTED LOCALLY; READY FOR MANUAL ACCOUNT-SWITCH TEST; destructive code defect potwierdzony, korelacja incydentu STRONGLY CONSISTENT / HIGH CONFIDENCE; repair zablokowany i należy wyłącznie do Sprintu 130.11 po GO Sprintu 130.10`.

Plan naprawy:

- `doc/sprint_130_10_profile_integrity_session_isolation.md`,
- `doc/sprint_130_11_trollu2_controlled_recovery.md`.

Sprint 131 pozostaje w kolejce do czasu GO obu sprintów incydentowych.

## 1. Przebieg zdarzenia

Gracz `Trollu2` rozpoczął normalną sesję gameplayową.

Na początku posiadał:

* aktywne konto z rozwiniętym profilem,
* około 25–26 LVL,
* prawie 1000 punktów doświadczenia / respektu,
* około 77 000 Hack Coinów,
* rozwinięte terytoria,
* zestaw posiadanych narzędzi i aplikacji.

Na mapie posiadał jedno aktywne terytorium zawierające aktywną część GhostNetwork należącą do jego klanu.

Następnie rozszerzył to terytorium w taki sposób, że w jego granicach znalazły się jednocześnie:

* aktywna część jego własnego klanu,
* zablokowana część należąca do innego klanu.

Oba efekty GhostNetwork nałożyły się na to samo terytorium i na tym etapie nie wystąpił widoczny błąd.

Gracz następnie przemieścił się z Warszawy do Tokio.

W Tokio odnalazł kolejną część należącą do własnego klanu i rozpoczął budowę terytorium wokół niej.

Pierwsze dwa filary zostały utworzone prawidłowo.

Problem wystąpił podczas utworzenia trzeciego filaru.

---

## 2. Moment awarii

Po postawieniu trzeciego filaru wydarzyło się kilka nietypowych rzeczy jednocześnie.

Najpierw dwukrotnie odtworzył się SFX odpowiadający utracie / ponownemu ujawnieniu części GhostNetwork.

Wyglądało to tak, jak gdyby system dwukrotnie uznał, że część została:

* utracona,
* odsłonięta,
* zdezaktywowana,
* albo przeszła nieprawidłową zmianę lifecycle.

Bezpośrednio po tym profil gracza został praktycznie zresetowany.

Zniknęły:

* wszystkie jego terytoria,
* rozwój profilu,
* LVL,
* punkty doświadczenia / respektu,
* avatar (brak), nick uzytkownika (NowyHacker)
* Hack Coiny i inne wartości profilu zależne od progression.

Profil zaczął wyglądać jak profil fallbackowy / startowy:

* LVL 1,
* startowe wartości,
* brak wcześniejszego progression.

Jednocześnie **narzędzia i aplikacje pozostały**.

To jest bardzo istotne, ponieważ wskazuje, że nie cały stan użytkownika został utracony w identyczny sposób.

W trakcie tej samej sesji gracz zainstalował również dwie nowe aplikacje z Googleplexa podczas hakowania i te dane trzeba uwzględnić przy analizie stanu profilu.

---

## 3. Hipoteza dotycząca profilu

Na tym etapie nie traktujemy tego jeszcze jako potwierdzonej przyczyny, ale zachowanie wygląda tak, jakby:

1. właściwy profil został uszkodzony albo niepoprawnie odczytany,
2. parser / loader nie był w stanie wykorzystać pełnego stanu,
3. system zbudował lub zapisał profil oparty o wartości domyślne / fallback,
4. część niezależnych danych, np. narzędzia lub aplikacje, została ponownie dołączona z innego źródła.

Trzeba ustalić, czy rzeczywiście doszło do:

* uszkodzenia JSON,
* częściowego nadpisania profilu,
* zapisania fallbacku jako prawdziwego profilu,
* race condition,
* stale snapshotu,
* błędnego merge,
* błędu podczas GhostNetwork lifecycle,
* błędu podczas territory rebuild,
* albo kombinacji kilku z tych rzeczy.

Na etapie zgłoszenia nie zakładaliśmy, że sam GhostNetwork bezpośrednio
uszkodził profil. Późniejszy Etap 1 Sprintu 130.10 potwierdził destrukcyjny
writer związany z rewardem GN, ale jego wykonanie dla tego konta nadal wymaga
korelacji serwerowej.

Moment wystąpienia błędu wskazuje jednak, że należy dokładnie prześledzić operacje wykonywane przy trzecim filarze i zmianach lifecycle części.

---

## 4. Osobny problem — pomieszanie sesji pomiędzy kontami

Po awarii pojawił się drugi, potencjalnie jeszcze poważniejszy problem.

Gracz wylogował się i zalogował na inne konto.

Po zmianie użytkownika różne części aplikacji zaczęły pokazywać dane pochodzące z różnych kont.

Zaobserwowano sytuację, w której:

* konto było już przełączone,
* aplikacje desktopowe należały do nowego użytkownika,
* ale część stanu profilu pochodziła jeszcze z poprzedniego logowania,
* mapa również prezentowała stan poprzedniej sesji.

Po wyczyszczeniu cache i ponownym logowaniu drugie konto działało prawidłowo.

Powrót na `Trollu2` również przez pewien czas działał.

Po kilku kolejnych przełączeniach kont problem z rozjeżdżaniem sesji ponownie się pojawił.

To trzeba potraktować jako **oddzielny finding dotyczący izolacji sesji i cache**, a nie jako zwykły efekt uszkodzenia jednego profilu.

Musimy sprawdzić między innymi:

* frontendowe cache profilu,
* `toolbarProfile`,
* mapę w iframe,
* snapshoty mapy,
* delty,
* `session["profile"]`,
* state przechowywany w `sessionStorage` / pamięci JS,
* reakcję na logout/login,
* czy wszystkie komponenty dostają jednoznaczny sygnał zmiany użytkownika.

Stan poprzedniego użytkownika nie może być nigdy prezentowany po zalogowaniu kolejnego konta.

---

# 5. Priorytetowa, kontrolowana odbudowa konta Trollu2

Niezależnie od późniejszego audytu chcemy odbudować konto testera.

Sam `apply` następuje jednak dopiero po GO Sprintu 130.10. Najpierw trzeba
zablokować ponowny zapis fallbacku/stale snapshotu i pomieszanie kolejnych
sesji; inaczej naprawiony profil mógłby zostać ponownie nadpisany.

Nie chcemy wyłącznie ręcznie poprawić kilku wartości w bazie.

Powstanie **dedykowany jednorazowy skrypt naprawczy dla `Trollu2`**, który wykona kontrolowaną odbudowę profilu.

Skrypt powinien być:

* jawnie przypisany do canonical username potwierdzonego w `users` dla konta
  zgłoszonego jako `Trollu2`, bez fuzzy match ani aliasu mapy,
* idempotentny albo zabezpieczony przed przypadkowym drugim uruchomieniem,
* wykonujący dry-run przed `--apply`,
* raportujący stan przed i po,
* nieingerujący w innych graczy.

---

## 6. Bonusowa odbudowa progression

Ponieważ utrata danych nastąpiła podczas testowania systemu, konto nie będzie tylko cofnięte do wcześniejszego stanu.

Gracz otrzyma bonusową rekompensatę.

Docelowo:

```text
LVL: 50
RSP / RESPECT: 2560
EXP: przeliczone z kanonicznych terytoriów
HACK COINS: 250 000
```

Pierwotnie posiadał około:

```text
HACK COINS: 77 000
```

Trzykrotność tej wartości wynosi 231 000 HC, ale wiążąca rekompensata została
ustalona na dokładnie:

`250 000 HC`.

---

# 7. Narzędzia i aplikacje

Nie usuwamy narzędzi, które pozostały po awarii.

Skrypt nie powinien przebudowywać inventory od zera, jeżeli obecne dane są poprawne.

Trzeba zachować:

* istniejące narzędzia,
* istniejące aplikacje,
* dwie aplikacje zainstalowane w Googleplexie podczas sesji poprzedzającej awarię.

Przed `--apply` skrypt powinien wypisać listę aplikacji i narzędzi, które pozostawi bez zmian.

---

# 8. Bonusowa odbudowa terytoriów

Największą częścią rekompensaty będzie odbudowa terytoriów.

Nie istnieje osobny kanoniczny store ticketów podróży. Listę miast budujemy z
hierarchii dostępnych dowodów: zabezpieczonego snapshotu, zgodnych wpisów
`product_purchases` / `googleplex_products` / `market_history`, wallet ledgeru,
system messages i logów. Relacja testera jest findingiem do jawnego
zatwierdzenia, a nie automatycznym źródłem targetów.

Dla każdego miasta potwierdzonego i zdeduplikowanego w podpisanym planie:

1. ustalamy bezpieczny obszar,
2. sprawdzamy istniejące terytoria,
3. wybieramy lokalizację niepowodującą konfliktu,
4. generujemy sztucznie nowy zestaw filarów,
5. budujemy kompletne terytorium bonusowe.

Nie kopiujemy przypadkowych współrzędnych 1:1.

Możemy wykorzystać rzeczywiste filary innych struktur jako wzorzec geometryczny, ale nowe filary muszą otrzymać własne kanoniczne identyfikatory.

---

## 9. Wielkość bonusowych terytoriów

W każdym mieście tworzymy solidne bonusowe terytorium.

Zakładany rozmiar:

`5–8 filarów`

Preferowany wariant:

`8 filarów`

tam, gdzie geometria i otoczenie na to pozwalają.

Terytorium musi być poprawne według aktualnego systemu:

* Target Registry,
* ownership CAS,
* `captured_targets`,
* territory rebuild,
* snapshot,
* worker reconciliation.

Nie wolno po prostu dopisać polygonu do profilu.

Skrypt ma wykorzystywać aktualne kanoniczne mechanizmy tworzenia ownership i filarów.

---

# 10. Brak sztucznych konfliktów podczas rekompensaty

Jeżeli w wybranym miejscu istnieje już cudze terytorium:

* nie przejmujemy go,
* nie tworzymy konfliktu,
* nie usuwamy istniejących filarów.

Bonusowe terytorium należy przesunąć obok istniejącego obszaru.

Celem skryptu jest rekompensata gracza, a nie zmiana sytuacji strategicznej innych testerów.

---

# 11. GhostNetwork podczas odbudowy

Skrypt naprawczy nie powinien sztucznie:

* odkrywać części,
* aktywować części,
* tworzyć reservations,
* powodować drop roll,
* zmieniać ownership istniejących części GhostNetwork.

Jeżeli bonusowe terytorium przypadkowo objęłoby istniejącą część GN, lokalizacja powinna zostać przesunięta.

Odbudowa profilu ma być niezależna od bieżącego cyklu GhostNetwork.

---

# 12. Backup profilu — nowy bezpiecznik

Ten incydent pokazuje, że potrzebujemy niezależnej warstwy ochrony profilu.

System powinien utrzymywać co najmniej **jeden ostatni poprawny backup profilu gracza**.

Nie chodzi o backup całej bazy wykonywany raz dziennie.

Chodzi o szybki recovery snapshot pozwalający odtworzyć pojedynczego gracza.

---

## 13. Zasada backupu

Przed zapisem, który może zastąpić znaczącą część profilu:

1. walidujemy obecny profil,
2. jeżeli jest poprawny, zapisujemy go jako `last_known_good`,
3. dopiero potem zapisujemy nową wersję.

Nie backupujemy bezwarunkowo każdego błędnego stanu.

W przeciwnym przypadku uszkodzony fallback mógłby natychmiast nadpisać dobry backup.

---

# 14. Co powinien chronić backup

Backup powinien umożliwiać odzyskanie co najmniej:

* LVL,
* RSP / respect oraz projekcję `exp`,
* Hack Coinów,
* klanu,
* profesji,
* aplikacji,
* narzędzi,
* zakupów Googleplex,
* trwałych achievementów,
* permanent history,
* ustawień profilu.

Terytoria posiadają własny source of truth i nie powinny zostać przywracane wyłącznie przez kopiowanie starego `profile["hacked"]`.

Dla terytoriów backup powinien przechowywać raczej informacje potrzebne do:

* audytu,
* identyfikacji utraconego ownership,
* uruchomienia reconciliation.

Nie tworzymy drugiego source of truth terytoriów w backupie profilu.

---

# 15. Walidacja przed zapisem profilu

Najważniejszym zabezpieczeniem nie jest sam backup.

System nie może dopuścić do sytuacji:

```text
pełny profil
→ chwilowy błąd odczytu
→ fallback LVL 1
→ fallback zostaje zapisany jako prawdziwy profil
```

Przed pełnym zapisem profilu potrzebne są sanity checks.

Przykładowo system powinien potraktować jako podejrzany nagły skok:

```text
LVL 26 → LVL 1
RSP ~1000 → 0
HC 77000 → wartość startowa
kilka terytoriów → 0
```

szczególnie jeżeli nie istnieje kanoniczne zdarzenie gameplayowe uzasadniające taki reset.

W takim przypadku:

* nie zapisujemy destrukcyjnej wersji,
* oznaczamy profil jako wymagający recovery,
* zachowujemy ostatni poprawny snapshot,
* logujemy różnicę,
* nie zamieniamy dobrych danych fallbackiem.

---

# 16. Fallback nie może być persistence source

Jeżeli profil nie może zostać załadowany, fallback może służyć do:

* wyświetlenia błędu,
* bezpiecznego ograniczonego UI,
* recovery mode.

Fallback nie powinien następnie zostać zapisany jako normalny stan użytkownika.

To wymaga osobnego sprawdzenia w audycie.

---

# 17. Sesja musi być izolowana od profilu poprzedniego użytkownika

Logout powinien wyczyścić wszystkie warstwy zależne od użytkownika.

Po zmianie konta nie może pozostać:

* poprzedni snapshot mapy,
* poprzedni `toolbarProfile`,
* poprzednia wersja delty,
* stare markery gracza,
* poprzedni aimed target,
* stare operacje,
* cache aplikacji,
* cache mapy,
* state iframe,
* event subscribers poprzedniego użytkownika.

Powinien istnieć jednoznaczny `user/session generation`, dzięki któremu odpowiedź rozpoczęta dla użytkownika A nie może zostać zastosowana po zalogowaniu użytkownika B.

---

# 18. Co trzeba teraz ustalić z logów

Z dostępnych logów gracza trzeba odtworzyć moment trzeciego filaru.

Szukamy kolejności:

```text
pillar capture
→ territory rebuild
→ GhostNetwork lifecycle
→ SFX lost/revealed
→ profile update
→ profile normalization/fallback
→ session/delta update
```

Szczególnie interesuje nas, dlaczego `part_lost` / odpowiednik został wyemitowany dwukrotnie.

Podwójny SFX może wskazywać:

* dwa różne eventy domenowe mapowane na ten sam `part_lost`,
* duplicate publication,
* dwukrotny lifecycle,
* rebuild + reconciliation generujące podobne przejścia.

Sam podwójny SFX nie jest jednak jeszcze dowodem, że to audio spowodowało utratę profilu.

Audio jest wyłącznie objawem, który pomaga wyznaczyć moment awarii.

---

# 19. Kolejność dalszych działań

Najpierw:

1. zabezpieczyć aktualny stan konta `Trollu2`,
2. zebrać logi i stan bazy,
3. ustalić przyczynę destrukcyjnego resetu,
4. sprawdzić problem mieszania sesji pomiędzy kontami.

Następnie:

5. przygotować dedykowany repair script,
6. zrobić jego dry-run,
7. zweryfikować planowane terytoria i wartości,
8. wykonać `--apply`,
9. uruchomić reconciliation,
10. sprawdzić profil, mapę i Googleplex.

Równolegle należy wprowadzić:

11. `last_known_good` backup profilu,
12. blokadę zapisu destrukcyjnego fallbacku,
13. profile sanity validation,
14. pełne czyszczenie user-scoped frontend/session state przy zmianie konta.

---

# 20. Oczekiwany efekt końcowy dla Trollu2

Po naprawie konto powinno posiadać:

```text
USER: Trollu2
LVL: 50
RSP / RESPECT: 2560
EXP: przeliczone z kanonicznych terytoriów
HACK COINS: 250 000

TOOLS:
zachowane

APPS:
zachowane
+ zachowane aplikacje zakupione podczas ostatniej sesji

TERRITORIES:
bonusowe terytoria w miastach wynikających z historii/ticketów Googleplex
preferowane 8 filarów na miasto
bez sztucznego wywoływania konfliktów
```

oraz poprawnie działającą:

* sesję,
* mapę,
* profil,
* deltę,
* Googleplex,
* Target Registry,
* territory reconciliation.

---

# Najważniejszy wniosek

To nie jest tylko problem jednego uszkodzonego konta.

Incydent ujawnił potencjalnie trzy klasy błędów:

1. **destrukcyjne nadpisanie albo fallback profilu,**
2. **brak niezależnego recovery profilu,**
3. **niedostateczną izolację stanu pomiędzy kolejnymi sesjami użytkowników.**

Naprawa `Trollu2` jest potrzebna natychmiast, ale właściwym celem jest doprowadzenie systemu do stanu, w którym podobny incydent:

* nie może skasować progression,
* nie może zapisać fallbacku jako profilu,
* nie może pozostawić mapy poprzedniego użytkownika po przelogowaniu,
* a jeśli mimo wszystko dojdzie do awarii, pojedynczy profil można szybko odzyskać z ostatniej poprawnej wersji.

---

# 21. Przefiltrowany materiał z załącznika konsoli

Źródło: załącznik rozmowy zaczynający się od
`GhostNetwork delta failed TypeError: can't access property "x", t is undefined`.

Do dokumentacji przeniesiono wyłącznie unikalne sygnały. Pominięto nazwy
pozostałych graczy, dokładne współrzędne i dziesiątki powtarzalnych wpisów
markerów.
Surowy log nie jest kopiowany do repo.

## Potwierdzony błąd

Załącznik zawiera jeden typ błędu renderera GhostNetwork występujący trzy razy:

- `2×` podczas zastosowania live delta:
  `GhostNetwork delta failed TypeError: can't access property "x", t is undefined`;
- `1×` podczas ładowania snapshotu:
  `[ghostnetwork] snapshot failed TypeError: can't access property "x", t is undefined`.

Wspólna ścieżka:

```text
Bounds.intersects
→ Polyline._clipPoints
→ projektowy wrapper _clipPoints
→ updateGhostConnectionLayer
→ renderGhostConnections
```

Dla delty dalsza część stosu to:

```text
renderGhostPart
→ applyGhostPartDelta
→ applyGhostNetworkDeltaPayload
→ handleGhostNetworkDelta
→ terminalowy pollStateChanges
```

Payload dotarł więc do klienta i awaria nastąpiła przy dodawaniu/aktualizacji
warstwy połączeń Leaflet. Ten materiał potwierdza defect presentation-layer.
Nie potwierdza błędu zapisu delty, backendowego lifecycle ani uszkodzenia
profilu.

Oba warianty mają ten sam punkt awarii, dlatego są jednym findingiem, a nie
osobnym błędem snapshotu i osobnym błędem delty. Z samego stosu nie można
rozstrzygnąć, czy źródłem był chwilowo niegotowy bounds renderera, czy wadliwy
punkt geometrii.

## Chronologia możliwa do odtworzenia

1. Dwa kolejne wpisy błędu podczas zastosowania delty GN pokazują ten sam
   wyjątek; bez event ID nie wiadomo, czy to osobne eventy, retry lub duplikat.
2. Niezależny refresh aktorów mapy nadal działa.
3. Trzy odpowiedzi actor API mają HTTP `200`, po `9` aktorów i czas
   `4,408–4,816 s`.
4. Późniejszy stos snapshotu przechodzi przez `bootMapInitialState` i wpada w
   ten sam wyjątek.
5. Równoległy refresh aktorów zostaje poprawnie scalony przez
   `[map actors] joining in-flight refresh`.
6. Kolejne trzy odpowiedzi actor API również mają HTTP `200`, po `9` aktorów i
   czas `3,854–5,002 s`.
7. Następny render raportuje `existing: 0`, tworzy `9` markerów, a późniejsze
   rendery znów je aktualizują.

Łącznie materiał potwierdza sześć poprawnie odebranych i zdekodowanych
odpowiedzi actor API. Czas około `3,9–5,0 s` pozostaje findingiem wydajnościowym,
nie dowodem utraty danych.

## Czego załącznik nie zawiera

W materiale nie ma:

- timestampów pozwalających powiązać wpisy z trzecim filarem;
- requestu ani odpowiedzi `/api/profile`;
- `401`, `403`, `500`, redirectu logowania ani session-expired;
- błędu JSON profilu lub SQLite;
- `part_lost`, event ID lifecycle ani logu SFX;
- before/after profilu, walletu lub terytoriów;
- informacji, czy dwa błędy delty dotyczą dwóch eventów, retry czy duplikatu.

Widoczność jednego aktora o podobnym aliasie nie może zostać potraktowana jako
dowód, że był to canonical login `Trollu2`, ani że jego profil był kompletny.

## Szum świadomie pominięty

- wielokrotne `marker updated/created`;
- ostrzeżenie o layout przed pełnym załadowaniem CSS;
- deprecated `mozPressure` i `mozInputSource`;
- artefakty kodowania nazw;
- drugi identyczny stack jako osobna kategoria;
- dane lokalizacyjne i nazwy innych graczy.

Bieżąca gałąź zawiera osobne hardeningi renderera połączeń GN. Ich regresja
pozostaje w Sprincie 130.10, lecz powodzenie tej poprawki nie wyjaśnia resetu
profilu.

---

# 22. Findingi z audytu kodu — potwierdzony defekt i pozostałe ryzyka

Poniższe zachowania są potwierdzone w kodzie i muszą zostać zamknięte przed
repair. Pierwsza ścieżka jest deterministycznym destructive-write. Zebrane
później dane serwerowe spełniają jej preconditions i pokazują odpowiadający
jej phenotype, z zastrzeżeniem braku historycznej telemetryki pojedynczego
write-attemptu i pre-incident LKG.

## Potwierdzony destructive-write po aktywacji części GN

Audyt odtworzył pełną ścieżkę:

1. trzeci stabilny filar może utworzyć pierwszy polygon;
2. publikacja terytorium uruchamia `ghostnetwork_territory_jobs`;
3. część zgodnego klanu przechodzi w `active`, a lifecycle emituje
   `ghost.part_activated` dla właściciela terytorium;
4. first activation reward modyfikuje profil odbiorcy;
5. `apply_ghostnetwork_runtime_result()` buduje `profile_cache` z
   `list_profile_identities()`, które zwraca tylko username i pola
   clan/faction/profession;
6. odbiorca już obecny w sparse cache nie zostaje doładowany pełnym profilem;
7. reward dopisuje respect/statystyki/historię do sparse dict;
8. `UserStore.save_profile()` zapisuje ten dict jako cały `profile_json`;
9. późniejszy `UserProfileManager` uzupełnia brakujące pola template'em, przez
   co profil przyjmuje wygląd starter-like.

Disposition:

- `CONFIRMED CODE DEFECT` — defekt istnieje niezależnie od incydentu;
- `INCIDENT CORRELATION: STRONGLY CONSISTENT / HIGH CONFIDENCE` — exact-user
  capture dla canonical loginu `trolu2` zawiera dwa skorelowane activation
  rewardy, zachowane durable stores i reset-like progression;
- brak profile-write telemetry/LKG z chwili incydentu pozostaje jawną luką,
  więc nie deklarujemy historycznej atrybucji jako absolutnie udowodnionej;
- wyjątek Leaflet nie jest częścią tego backendowego writer path.

Dodatkowo `/gonna-win` utrzymuje długowieczny pełny snapshot managera przed
capture/GN, a później może go zapisać po hookach. Jest to osobna droga stale
full-profile overwrite, słabiej wyjaśniająca całkowity starter reset.

## Odczyt i normalizacja profilu

`database.loads_json()` przy `JSONDecodeError` zwraca przekazany default.
`UserStore.get_profile()` używa defaultu `{}`, więc caller nie potrafi odróżnić
uszkodzonego JSON-u od pustego wyniku.

Ważne rozróżnienie:

- dokładnie pusty `{}` jest obecnie odrzucany przez `UserProfileManager` jako
  brak profilu;
- strukturalnie poprawny, ale niepełny i truthy JSON może zostać przyjęty,
  uzupełniony przez `_sync_with_template()` i zapisany;
- przed tą synchronizacją nie ma pełnej walidacji integralności ani dowodu, że
  brakujące pola są wynikiem legalnej migracji.

## Pełny zapis

`UserStore.save_profile()` wykonuje pełny upsert `profile_json`. Chroni obecnie
credentials, launch queue i historię rewardów GN, ale nie posiada ogólnej
revision/CAS ani `last_known_good` dla całego profilu. Stary pełny snapshot może
więc nadpisać równoległe zmiany zakresu, którego specjalny merge nie obejmuje.

## Dlaczego apps/tools mogły przetrwać

`PlayerInventoryStore.mirror_profile()` nakłada na projekcję profilową
kanoniczne aplikacje i narzędzia z wydzielonych store'ów. Jest to zgodne z
obserwacją, że inventory przetrwało utratę pozostałych wartości. To wskazówka o
częściowym charakterze awarii, a nie dowód źródła resetu.

## Ryzyko wtórnego obniżenia HC

`WalletBalanceStore.get_balance(..., fallback_profile=profile)` przy
rozbieżności ustawia saldo store na wartość z profilu jako
`profile_reconcile`. Jeżeli wejściowy profil jest niepełny albo startowy,
compatibility mirror może stać się błędnym źródłem dla kanonicznego walletu.
Jednocześnie legacy `WalletStore.transfer()` i `technical_transfer()` nadal
czytają oraz zapisują saldo bezpośrednio w pełnych `profile_json`. Wallet jest
więc w praktyce hybrydą writerów. Sprint 130.10 musi zinwentaryzować transfery,
Googleplex i Ghost Exchange oraz ustanowić jedną atomową granicę zapisu; samo
odwrócenie `fallback_profile` byłoby niepełną naprawą.

## Izolacja sesji

Backendowy logout wykonuje `session.clear()`, ale obecny kontrakt nie posiada
unikalnej generacji wiążącej odpowiedź z konkretnym logowaniem. Frontend ma
długowieczne request promise, pollery, delta cursors, dedupe sets, mapę w iframe
i user-scoped cache. To tworzy realny obszar ryzyka dla spóźnionej odpowiedzi
A po przełączeniu na B. Relacja testera potwierdza objaw, ale dokładna droga
pozostaje do odtworzenia instrumentacją.

Audyt endpointów potwierdził też brak rotacji SID/generacji przy loginie i
rejestracji, brak identity/generation w odpowiedziach oraz brak centralnego
teardownu cache, pollerów, map iframe, delta cursor, launch queue i beaconów.
Stara karta A może po loginie B działać w kontekście aktualnego wspólnego
cookie. Osobny finding autoryzacyjny: `/api/users/delete` pozwala obecnie
dowolnemu zalogowanemu użytkownikowi wskazać i usunąć dowolne konto nie-admin.
Nie jest to dowód przyczyny incydentu, ale jest blockerem hardeningu 130.10.

## Semantyka progression planowanego repair

W bieżącym modelu:

```text
level = liczba
respect = liczba RSP
exp = tekstowa projekcja powierzchni/progression
```

Dlatego intencję `EXP / RSP: 2560` normalizujemy dla repair do:

```text
level = 50
respect = 2560
hackcoins = 250000
exp = przeliczone po kanonicznym rebuildzie terytoriów
```

Nie zapisujemy `exp=2560` bez zmiany kontraktu całego systemu progression.

---

# 23. Macierz hipotez po filtracji

| Hipoteza | Stan dowodowy | Następny krok |
| --- | --- | --- |
| wyjątek Leaflet uszkodził profil | brak dowodu; stos kończy się w rendererze klienta | zachować jako osobny regression test |
| GN lifecycle wywołał reset profilu | `CONFIRMED CODE DEFECT`; dla canonical `trolu2`: `STRONGLY CONSISTENT / HIGH CONFIDENCE` | zablokować sparse full-save, dodać revision/CAS/LKG i telemetrykę |
| niepełny profil został uzupełniony template'em | potwierdzona możliwość w kodzie | test partial JSON + instrumentacja managera |
| stale pełny writer nadpisał progression | potwierdzona możliwość bez ogólnego CAS | mapa writerów + concurrency test |
| fallback HC wtórnie obniżył wallet | potwierdzona możliwość; wallet ma hybrydę profile/store writerów | audit ledgeru i jedna atomowa granica wszystkich wallet writes |
| apps/tools przetrwały dzięki osobnemu store | zgodne z kodem i objawem | porównać inventory store z profile before/after |
| stan A został pokazany po loginie B | potwierdzony objaw testera, brak request trace | session generation + test opóźnionych odpowiedzi |
| podwójny SFX oznacza duplicate lifecycle | brak event IDs w załączniku | sprawdzić event/dedupe logs; nie wnioskować z samego audio |

Systemowy destructive mechanism jest `CONFIRMED`, a korelacja konkretnego
incydentu jest `STRONGLY CONSISTENT / HIGH CONFIDENCE`. Brak historycznej
telemetryki zapisu i LKG nie pozwala rozstrzygnąć ostatniego kroku ponad wszelką
wątpliwość. GO nie może opierać się wyłącznie na odtworzeniu konta albo na
braku kolejnego błędu podczas pojedynczego manuala.

---

# 24. Serwerowe evidence capture — 2026-08-21

Canonical login ustalony exact-match to `trolu2`; `Trollu2` pozostaje nazwą
użytą w zgłoszeniu. Pakiet został zebrany read-only, pobrany jako
`logs/chaos-13010-trolu2-20260821T184643Z.tar.gz` i przeszedł weryfikację
SHA-256. Komendy `status`, `audit` oraz `verify` zakończyły wykonanie probe, a
SQLite `quick_check` zwrócił `ok`. Wynik `verify=0` w wersji evidence-v2
oznaczał technicznie ukończony odczyt bez blockerów strukturalnych; nie oznaczał
historycznego `account_integrity=clear`, ponieważ raport jawnie miał
`evidence_status=partial` i `account_integrity_status=unknown`.

Potwierdzone fakty:

- bieżący profil jest strukturalnie poprawny, ale ma reset-like core:
  `LVL 2`, `HC 1000`, `EXP 0.0`, `RSP 25`;
- zachowało się 11 aplikacji, 11 narzędzi, 11 hacked entries, 5 produktów i
  4 purchase records;
- Target/territory stores mają 11 captured targets, 35 ownership records,
  60 capture receipts i 15 applied progression receipts;
- wallet jest obecnie wewnętrznie zgodny na `1000`, ale zawiera 113 ledger
  events i 120 balance events; zgodność stanu końcowego nie dowodzi braku
  wcześniejszego propagation resetu;
- runtime zachował 578 historycznych operacji, 1000 delt, 1393 consumed system
  messages, position version 248 i target runtime version 2182;
- dwa `ghost.part_activated` mają dokładne applied
  `part_first_activated` correlations; reward ledger, contributions i profilowa
  reward history są exactly-once zgodne;
- ostatni activation/reward/publication/progression/job mieści się w oknie
  `13:24:45–13:25:01`, wallet pokazuje `1000` od `13:28:41`, a bieżący profil
  ma `updated_at=15:08:32`.

Interpretacja: strukturalna walidacja bieżącego JSON-u nie wykrywa semantycznej
utraty progression. Zachowane durable stores dowodzą, że nie jest to realnie
nowe konto LVL 2. Zgodna historia GN jest oczekiwana, ponieważ wadliwy writer
specjalnie scala reward history; nie obala sparse-overwrite path.

`FORENSICS CAPTURED — Sprint 130.10`.

## Pozostałe luki dowodowe

Przed capture lista potrzeb obejmowała:

- stan i checksum `users.profile_json` dla exact loginu;
- stan LKG, jeżeli po implementacji istnieje;
- `users.updated_at` oraz dostępne request/job IDs wokół trzeciego filaru;
- wallet balance i ledger tail;
- inventory/apps/tools oraz purchase history Googleplex;
- progression receipts i permanent history;
- Target Registry, captured targets, ownership, player areas i territory jobs;
- GN eventy oraz lifecycle części z tego terytorium;
- logi profilu/sesji obejmujące login A → B → A;
- dokładne ID dwóch aplikacji z ostatniej sesji;
- hierarchię dowodów miast używaną później przez repair; travel tickets nie
  mają dziś osobnego kanonicznego store.

Z capture nadal nie da się odzyskać pełnego profilu bezpośrednio sprzed
incydentu ani jednoznacznego profile-write request ID. Nie istniał też
zwalidowany LKG. Te luki pozostają jawne i nie są uzupełniane domysłem.

Capture wykonuje `tools/audit_profile_integrity.py` według
`doc/profile_integrity_recovery_runbook.md`. Narzędzie nie importuje runtime,
otwiera SQLite w `mode=ro` z `PRAGMA query_only=ON` i redaguje login, credentials,
pełny profil, współrzędne, target IDs oraz topologię. Nie przekazujemy surowej
bazy, WAL/SHM ani plików sesji.

---

# 25. Podział prac przed Sprintem 131

Nie używamy numerów `130.9.6` i `130.9.7`, ponieważ te oznaczenia istnieją już
w historycznym planie Runtime Enablement. Dwa kolejne, jednoznaczne sprinty to:

## Sprint 130.10 — Profile Integrity and Cross-Account Session Isolation

Najpierw forensics i systemowy stop-the-bleed:

- rozróżnienie invalid/missing/partial profile;
- osobna read-only evidence gate przed runtime changes;
- centralny write guard z expected revision, revision/CAS i `last_known_good`;
- ujednolicenie hybrydowych wallet writerów przed odwróceniem mirroru;
- rotacja identyfikatora sesji i unikalna `session_generation`;
- teardown i odrzucanie spóźnionych odpowiedzi A/B;
- automatyczna regresja oraz manual dwóch kont/dwóch kart i trzeciego filaru.

W tym sprincie nie wykonujemy repair `Trollu2`.

## Sprint 130.11 — Trollu2 Controlled Profile and Territory Recovery

Dopiero po GO 130.10:

- potwierdzenie canonical username, exact-user audit i podpisany plan;
- domyślny dry-run, before-manifest/rollback, jawny apply i durable receipt;
- LVL 50, RSP 2560, HC 250000;
- zachowanie canonical apps/tools i potwierdzonych zakupów;
- bonusowe terytoria przez atomowy recovery grant z `stationary=true` i worker;
- progression-neutralny stats/exp refresh oraz finalny settlement po jobach;
- brak konfliktów i zero repair-sourced zmian GN;
- post-apply verify, manual login/profile/map/Googleplex i jawna promocja LKG.

Sprint 131 jest formalnie:

`QUEUED — BLOCKED BY SPRINTS 130.10 AND 130.11`.

---

# 28. Gotowość kontrolowanej odbudowy — Sprint 130.11

Implementacja naprawy exact canonical `trolu2` jest gotowa do świeżego
serwerowego dry-run i operatorskiego apply. Nie używa uszkodzonego LKG jako
źródła, nie skanuje innych profili i nie wprowadza heavy profile path do weba
ani workera.

Zabezpieczenia obejmują podpisany plan i before-manifest, preconditions profilu,
walletu, inventory, session-generation, schematu i GN, atomowy per-city grant,
durable step receipts, retry exactly-once, jawne oddzielenie LKG promotion oraz
rollback blokowany przez późniejszy gameplay. Worker rozpoznaje specjalny job
tylko dla exact subject i kontraktu 130.11; canonical rebuild działa bez
profile/LKG write.

Na pełnej kopii snapshotu wykonano pierwszą fazę apply. Wynik był oczekiwany:
8 targetów Tokio, jeden pending rebuild job, faza `AWAITING_TERRITORY_WORKER`,
wallet 1000, RSP 25 i LKG bez zmian. Nie wykonano apply na właściwej bazie.

Status incydentu:

`READY FOR SERVER DRY-RUN / OPERATOR APPLY — repair not yet applied`.

---

# 26. Stan po lokalnym hardeningu Sprintu 130.10

Stop-the-bleed został zaimplementowany lokalnie. Runtime ma guarded profile
CAS/LKG/checksum/validation, kanoniczne i fail-closed granice walletu oraz
inventory, idempotentne transfery i retry, generation/precommit dla sesji wraz
z frontendowym teardown, odporną na retry sagę rewardów GN oraz bounded CAS
retry worker-owned territory projections. Naprawiono również niezdefiniowane
`profile_record` w ścieżce clear aimed target.

Testy celowane przeszły: Target Registry/persistence `221/221`, wallet
`30/30`, GhostNetwork `26/26` i territory projection CAS `3/3`. Pełna regresja
repozytorium zakończyła się wynikiem `956/956 OK`; sześć kontraktów JS oraz
pięć kontroli składni Node również przeszło.

Manual A → B → A, dwie karty, dwie niezależne sesje tego samego konta oraz
ścieżka gameplay `trzeci filar → rebuild/publication → GN lifecycle` nie zostały
wykonane przez agenta. To jest następna jawna bramka; nie deklarujemy GO.

Konto `trolu2` pozostało nietknięte. Nie wykonano repair, commita, deployu ani
restartu. Odbudowa nadal należy wyłącznie do Sprintu 130.11 po GO Sprintu 130.10.

---

# 27. Rozpoczęcie Sprintu 130.11 — read-only recovery gate

Na aktualnym lokalnym snapshotcie uruchomiono wyłącznie `status`, `audit`,
`plan` i `dry-run` nowego `tools/repair_trollu2_profile.py`. Baza była otwierana
w `mode=ro` z `query_only=ON`; pełny profil odczytano tylko dla exact canonical
`trolu2`, bez skanu profili innych kont.

Potwierdzone dowody planu:

- current profile: revision 1, checksum valid, LVL 2 / RSP 25;
- LKG: checksum valid, ale zawiera canonical mirror i nie jest dopuszczony jako
  recovery source;
- wallet balance `1000`, canonical inventory 11 apps i 11 tools;
- dwie ostatnie instalacje Googleplex: Nmap i Metasploit, obie potwierdzone
  message receipt oraz obecnością w inventory;
- travel evidence: receipt produktu `ticket_tokio` z efektem `travel_city`;
- GN: jeden aktywny `ghostnetwork_0001`, 20 części, zero planowanych write/event;
- terytorium: pierwszy pierścień Tokio kolidował z istniejącą geometrią i został
  odrzucony; resolver wybrał deterministyczny wolny wariant 3000 m na północ.

Ponowny lokalny dry-run zakończył się bez blockerów, z ośmioma stabilnymi
`stationary=true` filarami, zero zapisów innych profili i zero zapisów GN.
Regresja narzędzia: `13/13 OK`. Nie powstał before-manifest i nie wykonano apply,
wallet settlementu, territory grantów/jobs, promocji LKG, commita ani deployu.

`READY FOR MANUAL ACCOUNT-SWITCH TEST — Sprint 130.10`

---

# 29. Sprint 130.11 — częściowy apply i bramka wycofania

Serwerowy apply planu `trollu2_recovery_38f8b25502aed3990c91` utworzył osiem
recovery pillars i zakończył własny territory job, ale nie przeszedł do finalnego
RSP/wallet/LKG. Worker utworzył konflikt
`territory_conflict_26409afa48525665` z graczem `pies1`.

Root cause jest potwierdzony: dry-run oceniał tylko nowy ring Tokio, a worker
przeliczał także istniejące stationary targets po wcześniejszym podniesieniu
profilu do levelu 50. Na snapshocie istniejące targety same tworzą przy levelu 50
dwa nowe obszary i kolizję, więc relokacja bonusu nie może zagwarantować braku
konfliktu.

Revision 3/checksum po workerze nie jest automatycznie traktowany jako gameplay.
Narzędzie może go przyjąć wyłącznie po odtworzeniu exact revision 2 z podpisanego
before-manifestu i canonical stores, a następnie ponownym wyliczeniu dokładnie pól
`hacked`, `captured_targets_source`, `territory_stats` i `exp`. Wymagane są:
`revision +1`, identyczny checksum, niezmieniony wallet, brak pending progression
oraz terminalny recovery job. Inna zmiana pozostaje blockerem.

Controlled rollback zachowuje conflict history, ale usuwa jego aktywną geometrię
przez istniejący worker i publikację `no_active_fronts`. Scope konfliktu musi być
udowodniony przez recovery source/time/actor oraz nowe area IDs lub filary planu.
Captured action, player action receipt albo aktywny multi-engagement zatrzymuje
cleanup. Publikacja rollbacku nie odczytuje profili uczestników, nie uruchamia
encirclement i nie przyznaje nagrody za techniczne zamknięcie konfliktu.
GhostNetwork nie jest modyfikowany przez kod recovery.

Aktualny stan:

`NO-GO — partial Sprint 130.11 apply frozen; rollback not yet executed`.

Regresja lokalna poprawki: `376/376 OK`; `py_compile` i `git diff --check`: OK.
