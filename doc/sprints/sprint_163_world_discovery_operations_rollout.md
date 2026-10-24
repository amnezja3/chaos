# Sprint 163 — World Discovery: kolejka, panel operacyjny i kontrolowany rollout

Data: 20.10.2026. Aktualizacja: 24.10.2026. Status: **W REALIZACJI — pasywny etap PASS na VPS, cykl zadań lokalnie**.
Zaimplementowano ograniczony rejestr sektorów/warstw PENDING oraz podgląd stanu
magazynu i budżetu. Pasywny zapis odebrany na VPS; ingest/read nadal OFF.
Lokalna biblioteka zadań ma lease/fencing i uzgadnianie publikacji po crash,
bez automatycznych pobrań. Priorytet live MapLark i rotacja sektorów są
zaimplementowane lokalnie; pilot exact ingest/local przeszedł na VPS odczyt
przez innego workera i po restarcie. Operator potwierdził wyłączenie flag i
zapis PM2 oraz usunięcie jednego wygasłego snapshotu bez zmian cache/księgi.
Operator potwierdził zwykły skan w nowej lokalizacji po rollbacku: ograniczony
pilot exact-query odebrany. Nie jest to odbiór regionalnego pokrycia ani tła.
Nie ma jeszcze produkcyjnego workera ani mapy dowodów coverage.
Dowody: [163](../audits/sprint_163_evidence.md).
Zależności: [161](sprint_161_world_contract_and_adapters.md),
[162](sprint_162_world_repository_local_read.md), otwarte dowody 160.
Źródło: [koncepcja](../prototypes/poi/CHAOS_WORLD_DISCOVERY_ENGINE_KONCEPCJA_BEZ_NUMERU.md), etapy E–H.

## Cel i podział odbioru

Rozwijać poznany świat według rzeczywistego zapotrzebowania, z kontrolą kosztów
i pierwszeństwem graczy. Domknąć panel i uruchomić świadomie jeden ograniczony
pilot. Osobne statusy: **offline**, **pilot live/local**, **pilot background**,
**rollout**. Brak dostawcy nie blokuje implementacji offline, ale blokuje pilot.
Niniejszy plan nie odwołuje wstrzymania 160 i nie zezwala na nowe próby API.

## 163.0 — bramki wejścia i rejestr przejętych zobowiązań

Wymaga kontraktu 161, dowodów coverage i odczytu 162, a do ruchu realnego również
zatwierdzonego źródła. Nie wymaga pozornego zamknięcia całego 160 przed pracą offline.

| Otwarty element 160 | Właściciel dokończenia | Dowód wymagany przed ON |
| --- | --- | --- |
| 160.0 kontrakt / baseline | 161.0–161.1, 163.4 | Profil i porównywalny pomiar, oddzielony od okresu awarii |
| 160.1 storage/WAL/retencja | 162.0–162.1, 163.4 | Crash, limity, migracja, restore na VPS |
| 160.2 pełność/geometria | 162.2–162.5 | Wersjonowana domena parity, brak fałszywego local hit |
| 160.3 capabilities/źródła/rollback | 161.2–161.3, 163.2 | Scope, transport, propagacja i sprawdzony rollback |
| 160.4 agregaty/coverage/monitor | 163.2–163.3 | Liczebność i okno metryk, zero HTTP od odświeżenia panelu |
| 160.5 integracja/produkcja | 162.4–162.5, 163.4–163.5 | Gameplay, koszty, lokalny odczyt, restart/restore/rollback |

Macierz 160 aktualizujemy dowodami i odsyłaczami po wykonaniu; nie wpisujemy PASS
za samo przenumerowanie prac. Historyczne wyniki 81 testów nie dowodzą nowego silnika.

## 163.1 — discovery queue i worker

Zdarzenie `coverage_demand` opisuje sektor/profil i zagregowane zainteresowanie,
bez user_id, nicku, sesji i historii ruchu. Kolejka w tej samej logicznej bazie;
HTTP poza transakcjami. Klucz dedup obejmuje sektor, profile i wersję kontraktu.

Stany: PENDING → LEASED → FETCHING → VALIDATING → COMMITTED; także DEFERRED,
RETRY_AFTER, POLICY_BLOCKED, FAILED_TERMINAL, CANCELLED. Lease fencing,
idempotencja, maksymalna liczba prób, TTL zainteresowania i pojemność kolejki.
Crash po zapisie i przed ack nie powoduje ponownego publikowania/rozliczania.

PASSIVE: rejestrowanie popytu bez HTTP w tle. BOUNDED_PREFETCH: mały pierścień
wyłącznie od rzeczywistego zapotrzebowania, bez rekurencyjnego generowania
nieskończonych zadań z wyników własnego prefetch. Brak popytu → zadania wygasają.

Worker poza Gunicornem; wspólny slot, circuit, Retry-After i limity 158.
Nie wystarcza „ten sam mutex”: trzeba wykazać pierwszeństwo oczekujących live
przed przyznaniem nowego slotu tłu. Rozpoczętego HTTP nie anulować w sposób,
który zwolni lease i pozwoli na równoległą drugą próbę tego samego zadania.
Fairness regionalny zapobiega zużyciu budżetu przez jeden obszar. Wagi dopiero
po benchmarku; grupę około 100 testerów symulować bez publicznego obciążania API.

Każda strona/estimate/refresh zużywa wspólną rezerwację kosztu i limitów.
Brak potwierdzonej ceny lub pozostałej kwoty blokuje płatne zadanie, nie zakłada
kosztu zero. Anulowanie zwalnia niewykorzystaną rezerwację, nie cofa zużytych kredytów.
Background wymaga osobnego scope, limitu przestrzeni/czasu i miejsca na dysku.

### 163.1-G — geografia odwiedzanych regionów (23.10.2026)

- Generować zagregowane `coverage_demand` region/warstwa również z odwiedzenia
  obszaru bez POI. Nie zapisywać user_id ani tras; zdarzenie nie zależy od sukcesu
  upstream. Deduplikować według profilu, regionu, wersji i wymaganego kontekstu.
- Uzupełniać niezależnie drogi `highway`, cieki `waterway`, wody `natural=water`,
  coastline i produkt ląd–woda. Nie żądać wszystkich warstw przy każdym skanie.
  Live POI ma pierwszeństwo. Każda warstwa ma osobny budżet/limit, ale nadal
  podlega wspólnemu limitowi ruchu, kosztów, RAM, dysku i kolejki.
- Regiony i ograniczony halo wynikają z rzeczywistego popytu. Ukończenie zadania
  nie generuje bez końca sąsiednich zadań. Popyt wygasa; limity wierzchołków,
  obszaru, liczby zależności i bytes zatrzymują rozrost dużej geometrii.
- Dla morza oddzielić fetch coastline od pozyskania/budowania `land_water`.
  Preferować dopuszczony wycinek gotowego produktu, jeśli istnieje i spełnia
  kontrakt. Rekonstrukcja z linii jest osobnym zadaniem z bounded dependencies,
  wersją algorytmu, dowodem topologii i kontekstem wysp/otworów/antymeridianu.
  Brak domknięcia daje DEFERRED/PARTIAL z powodem; nie dociągać całego kontynentu
  i nie wypełniać oceanu na podstawie braku POI czy `natural=water`.
- Publikować geometrię i coverage dopiero po walidacji. Awaria opcjonalnego
  uzupełniania geografii nie cofa poprawnego skanu POI ani nie uruchamia jego
  glitcha MASA. Wyłączenie jednej warstwy nie odbiera innych lokalnych danych.
- Panel pokazuje per warstwa regiony unknown/partial/fresh/stale, wersję,
  źródło, zależności, koszty, wielkość geometrii i przyczyny odłożenia.
  Nie pokazuje tras użytkowników i nie wywołuje API przez samo odświeżenie.

Pilot warstw etapami: ograniczony region drogi/cieku → jezioro z wyspą →
region przybrzeżny i certyfikowany wycinek ląd–woda. Każdy etap wymaga właściwego
źródła, praw, limitów, dowodów odczytu 162 i osobnego włączenia profilu.
Nie zakładać wsparcia MapLark/Geoapify dla całej geografii. Brak źródła morza
pozostawia ten profil otwarty, nie blokuje odbioru dróg ani skanera.

Odbiór D09–D12: dedup popytu bez POI i brak rekurencyjnej ekspansji; pierwszeństwo
live i wspólne limity przy dużych geometriach; regionalny ingest → lokalny
odczyt 0 HTTP → restart/restore każdej certyfikowanej warstwy; niepełny brzeg,
brakujące dependencies i zmiana datasetu bez fałszywego COMPLETE.
Stop/rollback per warstwa sprawdzić niezależnie od globalnego kill switcha.
Pełny odbiór rozszerzonego 163 wymaga D01–D16; częściowe odbiory nazywać
profilem i zakresem, nie deklarować ukończenia całej geografii.

## 163.2 — panel, decyzje i rollback konfiguracji

Rozbudować istniejący admin 160, bez nowego systemu kont. Sekcje:
providers/capabilities/secret refs, coverage i jakość warstw, wzrost repo/WAL,
koszty i budżety, kolejka, stan upstream, historia i sterowanie.

- Rewizje konfiguracji i ponowna walidacja na czterech workerach przed nowym HTTP.
- Zmiana URL/adaptera unieważnia właściwe dowody; rollback nie przywraca wygasłych
  scope ani sekretu ujawnionego w historii. Zapisywać referencje, nie wartości kluczy.
- RBAC, CSRF, allowlisty adapterów, public DNS/IP/TLS, brak redirect/proxy,
  redakcja kluczy i weryfikacja endpointów także przy porównaniach/rollbacku.
- Kill switch nowych pobrań oddzielny od local read: odcięcie sieci nie odbiera
  gry na kompletnych danych. In-flight kończy się w ograniczonym deadline;
  nowe strony/zadania nie startują. Nie kasować danych ani aktywnych lease.
- UI PL/EN, desktop/mobile, komunikaty przy przyciskach. „Saved” nie może
  oznaczać wizualnie sukcesu testu providera przy zapisanym HTTP 500.
- Mapa coverage pokazuje dowody i znany obszar, nie fikcyjny procent całego świata.
  Bez mapowania śladów poszczególnych testerów.

### 163.2-K — panel kredytów API i budżetu CHAOS (23.10.2026)

Wykorzystać registry, historię i rezerwacje przygotowane w 161, bez osobnego
systemu zarządzania dostawcami. Parametry wejściowe z kont operatora:

| Dostawca | Limit kredytów zgłoszony przez operatora | Do potwierdzenia przed ON |
| --- | --- | --- |
| MapLark | 30 000 / miesiąc | Plan, reset okresu, koszt operacji, rate limit |
| Geoapify | 3 000 / dzień; 5 req/s | Plan, naliczanie, reset i znaczenie wskazanego limitu 10 km |

To dane do weryfikacji 161.2-K, nie hardcoded ustawienia ani deklaracja oferty.
Panel rozdziela dwa liczniki per konto/plan/dostawca:

1. **Konto dostawcy:** limit, zużyte, pozostałe, okres/reset, źródło odczytu,
   aktualność. Synchronizacja tylko przez udokumentowane API, jeśli dostępne;
   inaczej ręcznie wpisany odczyt panelu z datą. Nie pobierać panelu scrapingiem.
   Brak danych = unknown; lokalny szacunek nie jest rzeczywistym saldem.
2. **Budżet CHAOS:** zatwierdzony limit dzienny/miesięczny, naliczone/szacowane
   zużycie, rezerwacje in-flight i pozostała kwota do wydania. Historia rozdziela
   live, background, probe, strony i ponowienia. Nie zakładać jeden request = kredyt.

Ostrzeżenia przy 70%, 85%, 95% wykorzystania wewnętrznego budżetu, z uwzględnieniem
rezerwacji. Jeśli aktualny limit dostawcy jest znany, alarmować również jego
wyczerpanie, z osobną etykietą. Dedup ostrzeżeń per konto/okres/próg; komunikaty
przy liczniku i akcjach, PL/EN. Bez automatycznej wysyłki poczty lub kupowania pakietu.

Rezerwacja i rozliczenie atomowe, idempotentne i wspólne dla 4 procesów oraz
workera. Nowy HTTP/strona nie startuje, jeśli koszt nie mieści się w którymkolwiek
obowiązującym limicie. Uwzględnić rate limit per konto i obecny globalny limit
158 — 5 req/s nie stanowi polecenia zwiększenia równoległości. Przy timeout
nieznane naliczenie zachować jako niepewne do uzgodnienia; nie zwalniać w ciemno.
Crash/restart ani reset okresu nie zerują nierozliczonych kosztów. Okresy dzienny
i miesięczny mają jawne strefy/granice; resetować tylko właściwy licznik.

Uwzględnić użycie konta poza CHAOS i opóźnienia raportowania: pokazać rozbieżność,
datę uzgodnienia i ewentualny margines rezerwy. Nie obiecywać bezwzględnej ochrony
całego współdzielonego konta przy nieaktualnym saldzie. Nieznana cena blokuje
płatną operację; brak bieżącego salda nie znosi wewnętrznego limitu. Dopuszczenie
pracy na lokalnym liczniku wymaga jawnej polityki konta i limitu bez nadwyżek.
Zmniejszenie budżetu poniżej zużycia blokuje nowe pobrania; nie anuluje zapisu
poprawnej rozpoczętej odpowiedzi. Limit kosztu nie jest awarią upstream/MASA.
Po wyczerpaniu budżetu pozostają lokalne odczyty; brak danych ma jawny powód.

### 163.2-M — interaktywna mapa poznanego świata

Mapa tylko w adminie, w stylistyce CHAOS: pan/zoom, półprzezroczyste pokrycie,
wybór warstwy i klik w obszar. Korzystać z ograniczonego odczytu 162.2-E,
agregacji zależnej od zoomu, limitów odpowiedzi i uproszczeń prezentacyjnych.
Nie renderować tysięcy markerów POI ani pełnej bazy w przeglądarce.

Warstwy: **POI / Drogi / Rzeki i kanały / Jeziora i zbiorniki / Wybrzeża /
Ląd–morze** oraz widok zbiorczy. Każda ma osobną wersję profilu i kompletność.

| Wygląd | Znaczenie dla wybranego profilu i zakresu |
| --- | --- |
| Zielony | COMPLETE_FRESH z dowodem selekcji i dopuszczonym lokalnym odczytem |
| Żółty | PARTIAL; brak pełnego pokrycia lub wymaganych danych |
| Pomarańczowy | COMPLETE_STALE/EXPIRED; potrzebna aktualizacja, używalność wskazana osobno |
| Szary / neutralne tło | UNKNOWN; brak dowodu, niekoniecznie brak obiektów |

Legenda, tekst i wzór wspierają kolory. Blokada praw/konfiguracji ma osobną
etykietę; nie sugerować działającego lokalnego odczytu samym zielonym kolorem.
Komórka przecięta małym dowodem nie może wyglądać na całkowicie pokrytą;
rysować obrys dowodu lub oznaczać agregat jako mieszany/częściowy. Widok zbiorczy
podaje które warstwy są kompletne (np. 2 z 6); jedna nie zazielenia wszystkich.

Domyślnie pokazywać obszary z zapisanymi użytecznymi danymi, z widocznym filtrem
„ukryte kompletne puste wyniki” i przełącznikiem ich pokazania. Pusty COMPLETE
zachowuje status kompletności i etykietę „0 obiektów”; ukrycie nie zamienia go
w UNKNOWN. Statystyki jawnie rozróżniają widok filtrowany i całą bazę.
Nie rozbudowywać sąsiadów wyłącznie wskutek pustego wyniku. Popyt na inną warstwę
może uruchomić jej własne zadanie; pusty POI nie blokuje pozyskania rzeki.

Szczegóły obszaru: profil, stan, geometria dowodu, źródło, wersja, daty,
liczba obiektów, powód partial/stale, dopuszczalny odczyt i zadanie odświeżenia.
Bez user_id, nicków, pozycji graczy i historii tras. Żadnych requestów do
providerów danych przy pan/zoom/klik/refresh; podkład mapowy zachowuje istniejącą
konfigurację i jest odróżniony od płatnych operacji World Discovery.
Publiczną mapę rozwoju pozostawić w backlogu, poza zakresem 163.

## 163.3 — definicje statystyk, telemetria i limity operacyjne

Panel obok mapy: liczba sektorów per profil/stan, unikalnych obiektów (bez
podwójnego liczenia memberships), regionów zagregowanego popytu w zadanym oknie,
nowych obiektów/dobę (oddzielnie aktualizacje/usunięcia), rozmiar danych/indeksów/WAL.
Region musi mieć ustaloną jednostkę siatki; nie wyliczać pozornych „miast” ani
procentu całej planety. Przykładowe liczby załącznika to ilustracja, nie baseline.

Główna miara: `world_local_scan_ratio` = udane skany gracza obsłużone w całości
z trwałego repo bez HTTP / wszystkie udane skany gracza w tym samym oknie.
Licznik obejmuje zgodny kontraktowo wynik pusty, jeśli gameplay uznaje go za sukces.
Oddzielne rozłączne źródła wyniku: world-only, exact-cache-only, mieszane lokalne,
z udziałem sieci. Cache 158 nie udaje trwałej wiedzy świata. Błędy/anulowania
pokazywać osobno wraz ze wszystkimi próbami, żeby odsetek sukcesów nie ukrywał
awarii. Przy zerowym mianowniku wyświetlić „brak danych”, nie 0% lub 100%.
Udział skanów wymagających HTTP liczyć na tych samych udanych skanach; liczba
requestów (strony/retry) jest osobną miarą. Tło/probe nie zwiększają mianownika
skanów gracza. Każda statystyka ma okres i liczebność; próbki agregować bez tras.

Pasywne obserwacje mają pierwszeństwo. Otwarcie panelu i 20 odświeżeń = 0 HTTP.
Aktywny monitor tylko po osobnym dopuszczeniu; jeden skoordynowany job, nie
scheduler w każdym Gunicornie. Niedawny realny sukces może zastąpić probe.

Mierzyć: local_hit_ratio, HTTP/successful_scan, kompletne nowe coverage,
partial_ratio, spend/100_scans, unique_objects, bytes/object, latency p50/p95,
błędy per reason, queue_age p95, 429/5xx, RAM peak, lock wait i WAL.
Każdy agregat ma okno, liczebność i rozróżnienie live/background/probe;
brak próbek to unknown, nie zero opóźnienia. Koszt szacowany oddzielić od naliczonego.
Baseline i SLO uzgodnić po pomiarach; nie obiecywać „90% offline” bez danych.

Osobno stan dostępności upstream i używalności repo. Brak konfiguracji/praw
nie jest awarią sieci ani dowodem fabularnej blokady MASA.

## 163.4 — policy review i pilot jednego źródła

Przed pierwszym HTTP nowego zakresu świata/tła operator potwierdza: konkretne API/plan, zakres kategorii,
normal_scan, wide, cache/permanent_store, refresh/background_fill, wymagane
atrybucje i ewentualne redistribute; budżet finansowy i techniczny oraz retencję.
Weryfikować bieżące oficjalne warunki, nie przyjmować deklaracji koncepcji za umowę.
Nie trzeba dopuścić wszystkich trzech adapterów, żeby uruchomić jeden zgodny profil.

Kolejne bramki, każda z osobną decyzją operatora:

1. **Mała próba techniczna:** z VPS, z ograniczonym budżetem, capability/kompletność
   i pełna walidacja; pojedynczy 200 nie daje dowodu stabilności.
2. **Pilot ingest:** izolowany obszar i konta, background OFF; porównanie z
   kontraktem na utrwalonym snapshotcie. Zweryfikować kredyty i liczbę stron.
3. **Local read:** ten sam i sąsiedni pokryty skan → 0 HTTP, potem restart i
   ponowny odczyt; brak source nie blokuje poprawnego local hit.
4. **Operacje:** backup/restore do osobnej ścieżki, rollback konfiguracji,
   zmiana źródła widoczna na czterech workerach. Bez globalnego odcinania gry.
5. **Odbiór gameplayu:** dwa konta, GhostLab, koszty, kamery, NPC, marked targets,
   klany i MASA. Pusty kompletny teren oraz nieznany teren to różne przypadki.

Brak dostępnego źródła zatrzymuje ten etap, a nie wymusza zapytań w pętli.
Nie wznawiamy starych prób DE/VK automatycznie. Aktualizacja publicznych informacji
o przetwarzaniu danych, jeżeli zmienia się rzeczywisty odbiorca/zakres, poprzedza ON;
nie deklarujemy zawarcia niepotwierdzonych umów.

## 163.5 — testerzy, ograniczone tło i odbiór końcowy

Po udanym live/local: ograniczony opt-in użytkowników/obszarów i obserwacja
z uzgodnioną liczebnością. Globalna architektura nie wymusza globalnego startu pilota.
PASSIVE przed BOUNDED_PREFETCH. Włączenie tła dopiero po osobnym zatwierdzeniu
praw, budżetu, obciążenia VPS i dowodzie pierwszeństwa graczy.

Warunki stop: niepełny wynik oznaczony jako kompletny, regresja kosztów/markerów,
wyciek sekretu/danych gracza, przekroczenie budżetu, amplifikacja requestów lub
utrata kontroli nad kolejką. Progi wydajności/kosztu liczbowe ustalić przed pilotem
na podstawie benchmarku, nie dopiero po wystąpieniu przekroczenia.

Rollback: zatrzymać nowe pobrania/tło, zachować bezpieczny local read, a jeśli on
jest źródłem regresji — wyłączyć go osobno. Zachować snapshoty i audit trail.
Powrót do exact 158 nie naprawia niedostępnego źródła. Przetestować operacyjnie
zgodność schematu ze starym kodem lub restore kopii w nowej ścieżce.

## Macierz odbioru

| ID | Wymagany dowód |
| --- | --- |
| D01 | Dedup, restart/lease/fencing, ack po crash, TTL i limit kolejki |
| D02 | 4 procesy + worker: priorytet live, fairness, jeden globalny budżet, brak rekurencji |
| D03 | Paginated costs, rezerwacje, Retry-After, stop/kill switch i brak nowego HTTP |
| D04 | Policy/capability/revision, RBAC/CSRF/SSRF, redakcja kluczy, bezpieczny rollback |
| D05 | Playwright MCP PL/EN mobile/desktop, panel/coverage/queue, błędy przy akcjach, 0 HTTP od refresh |
| D06 | Pełny live ingest → local 0 HTTP → restart → restore/rollback na VPS |
| D07 | Izolowane konta, GhostLab i komplet regresji mapy zgodnie z 162 |
| D08 | Obserwacja testerów: próbki/okno, koszty, SLO, RAM/WAL; osobny odbiór background |

Dowody docelowo: `doc/audits/sprint_163_evidence.md`, runbook operacyjny i
uzupełnienie macierzy 160–162. Pełny PASS 163 wymaga D01–D16; PASS offline
i PASS live/local można zapisać osobno przy nadal wyłączonym tle.

Dodatkowe dowody odbioru panelu (23.10.2026):

| ID | Wymagany dowód |
| --- | --- |
| D13 | Dwa liczniki, unknown/ręczny odczyt, nieaktualne saldo i rozbieżność; strony/retry i naliczenia niepewne |
| D14 | Progi 70/85/95, atomowe rezerwacje przy 4 procesach + worker, restart/reset okresów i stop przed przekroczeniem; local read nadal działa |
| D15 | Playwright PL/EN mobile/desktop: pan/zoom/warstwy/szczegóły, puste/unknown/mixed/stale, filtry i legenda; brak wywołań API dostawców danych |
| D16 | Statystyki na znanych fixtures: world/cache/network/mixed/error, puste sukcesy, zero prób, memberships i przyrost; jawne okno/mianownik |

Te dowody uzupełniają D01–D12, nie zastępują odbioru geografii.

## Flagi i decyzje pozostawione do zatwierdzenia

Zachować flagi ingest/read/registry/wide/admin/monitor z 160. Wyłącznie brakujące
zdolności kolejki, background i globalnego stopu nowych pobrań mogą otrzymać
nowe flagi; nazwy zatwierdzić po przeglądzie konfiguracji, wszystkie domyślnie OFF.

Do decyzji: pierwszy dostawca/plan/scopes; TTL fresh/usable i retencja trwałej
wiedzy; limity kredytów/RAM/dysku/kolejki; siatka i envelope z benchmarku;
granice łączenia snapshotów; grupa pilota i progi stop; zgoda na live, potem tło.
Otwarte decyzje nie oznaczają zgody przez upływ czasu. Na tym etapie brak pusha,
deploya, aktywacji flag, nowych prób API i korespondencji do dostawców.
