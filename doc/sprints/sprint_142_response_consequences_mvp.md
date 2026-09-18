# Sprint 142 — pełna ścieżka incydentu i konsekwencji MVP

Status: W REALIZACJI; rozszerzony audyt techniczny ukończony 16 IX 2026
przed rozpoczęciem developmentu. 142.1 zamknięty po ponownym PASS autora
17 IX 2026. 142.2 zamknięty po odbiorze autora; 142.3 PASS autora 18 IX 2026.
Podstawa: [audyt](../audits/response_consequences_2026_09_16.md).
Zakres zatwierdzony przez autora: scan → kamery → próba wygaszenia → inicjacja
incydentu → eskalacja → publikacja w mediach gry i BlackNecie → służby →
konsekwencje MVP. Celem jest produkcyjność całej istniejącej ścieżki, nie tylko
executora kar. Dopiero PASS tego sprintu pozwala uruchomić rozbudowę w 143.
Wszystkie etapy bez pełnego profilu i bez zależności skutków od otwartej mapy.

## Bramka wejścia — audyt ukończony przed sprintem

Źródłem prac jest zamknięty raport audytu z mapą call sites, reprodukcjami,
macierzą reuse/adapt/replace i ograniczeniami pomiarów. Nie odkładamy badania
istniejącego MVP na development. Pozostałe decyzje gameplayowe zamykamy przed
implementacją właściwej policy; testy odbiorowe w sprincie weryfikują naprawy.

## 142.1 — realizacja kontraktu scanu i autoryzacji

Status: **ZAMKNIĘTY / PASS**, ponowny odbiór autora 17 IX 2026.
Autor potwierdził prawidłowe menu kamer, jedno wyłączenie podczas trwania
operacji i toast przy ponowieniu, podsumowując odbiór „mamy pass”. Następnie
osobno potwierdził również poprawne działanie kropki celu na belce.

Historia cofniętego odbioru: autor zgłosił
brak ID kamery/scanu w żądaniu z mapy. Poprawiono transport tych pól przez
oznaczanie/wybór celu i snapshot mapy. Autor potwierdził uruchamianie, ale
zgłosił duplikację operacji. Ujednolicono shutdown z mapy/pulpitu/terminala
oraz deduplikację starszych operacji; testy lokalne PASS, ponowny odbiór oczekuje.
Wcześniejsze wyniki
testów automatycznych pozostają zapisane, wymagany jest ponowny odbiór.

Kolejny odbiór ujawnił nadal duplikację, brak kropki i regresję menu markerów.
Aktualna poprawka obejmuje DOM binding oznaczonych kamer, atomowy postęp celu,
wspólną deduplikację starszego writera i okien aplikacji; szczegóły i scenariusz
ponownego odbioru w runbooku. Etap zamyka dopiero powyższy ponowny PASS autora.

Implementacja i odbiór tej paczki: [runbook 142.1](../runbooks/sprint_142_1_camera_contract.md).
Kontrakt przejść całego mechanizmu pozostaje opisany w audycie. W tej paczce
wdrażamy stabilne ID kamer, obserwacje backendu, autoryzowany shutdown,
atomowy zapis operacji/launchera/delty i odtworzenie wyniku. Integracja wpływu
kamer na inicjację i eskalację należy do 142.2; publikacja i executor do kolejnych
etapów poniżej. PASS tej paczki nie oznacza zamknięcia całego 142.

- Wykorzystać prześledzony w audycie request scanu, utrwalenie listy kamer, uprawnione
  aplikacje, akcję shutdown i jej wynik, ryzyko inicjacji oraz późniejszej
  eskalacji, publikacje, wykrycie i wykonanie istniejących kar.
- Dla każdego przejścia zapisać: trigger, canonical źródło, writer/reader,
  wersję, klucz idempotencji, deltę/outbox, recovery, koszt oraz test.
- Audyt uprawnień shutdown: zainstalowana aplikacja, dozwolona akcja,
  kompatybilność celu, aktywny dostęp i ograniczenia; recheck przy commit.
  Samo kliknięcie albo deklaracja klienta nie jest dowodem wyłączenia.
- Wdrożyć decyzje tabeli reuse/adapt/replace z audytu: risk meter i progi,
  incident initializer, publikacja/delta, bridge BlackNet, GooglePlex News,
  canonical inventory/wallet, reguły aktywnych części i Super Powers.
  Punkty startowe: `active_ghostnetwork_operation_risk_rules`,
  `ability_heat_modifier`, `publish_incident_actions`,
  `build_blacknet_incident_facts`, istniejące store’y i receipts.
- Nie zakładać zgodności istniejących funkcji tylko po nazwie. Preferować
  wspólną czystą funkcję; klon wyłącznie przy odmiennym kontrakcie i z testem
  parytetu oraz opisem zamierzonej różnicy. Bez kopiowania ciężkich ścieżek.

## 142.2 — kamery, inicjacja i próba wygaszenia

Status: **ZAMKNIĘTY — PASS AUTORA I TESTÓW AUTOMATYCZNYCH**
(17 IX 2026). Prześledzono punkt startu operacji,
bounded worker, kalkulator heat oraz inicjalizator. Autor zatwierdził:
+4 osobnego składnika przy kamerach, wyłączenie jednej zeruje ten
składnik, bez stackowania; zakres własnych operacji tego samego obiektu;
istniejący incydent otrzymuje niższy wkład, bez usuwania incydentu/kar;
po expiry składnik wraca. Reguły zatwierdzone 17 IX 2026.

Integracja ma zapisywać serwerowy kontekst ekspozycji przy tworzeniu operacji
i zbiorczo odczytywać ważne shutdown dla ograniczonego batcha workera.
Nowy scan ani TTL obserwacji nie mogą nadpisywać kontekstu działającej operacji.
142.2 zachowuje wkłady graczy spoza bieżącego batcha i zapisuje zmianę wkładu
również przy sumie ograniczonej do 100. Pozostałe defekty trwałości/publikacji
pozostają zakresem 142.3. Kontrakt wdrożenia i odbioru:
[runbook 142.2](../runbooks/sprint_142_2_camera_risk.md).

Szczegółowy kontrakt kamer znajduje się na końcu dokumentu. Musi obejmować
zarówno początkowe wzbudzenie, jak i zmianę eskalacji już istniejącego incydentu.
Sprawdzić brak kamer / wszystkie aktywne / jedna off / wiele off, uprawnienia
narzędzia, skuteczność akcji i powrót kamer do aktywności. Zapisać liczbę kamer
wykrytych, aktywnych i skutecznie wyłączonych oraz wersję/czas obserwacji.

## 142.3 — eskalacja, trwałość i publikacja

Status: **ZAMKNIĘTY / PASS AUTORA** (18 IX 2026).
Potwierdzony przepływ hero i rotacja produktów. Dodano ręczny refresh
w WebDragons do obserwacji zmian bez zamykania okna. Kolejny etap obserwacyjny:
kilka godzin aktywności graczy i ocena dynamiki News przy większej liczbie
zdarzeń. Jakość tekstów, ewentualne deterministyczne treści zastępcze oraz
dodatkowa rotacja narzędzi należą do przyszłych sprintów Ollamy i nie blokują PASS.
Autor zatwierdził 30 minut cooling po zakończeniu ostatniej aktywnej operacji.
Wylogowanie nie zmienia tego zegara. Nowa operacja powyżej progu aktywuje
jeszcze niewygaszony incydent. Po cooling następuje resolved.
Implementacja i instrukcja restartu wszystkich czterech procesów:
[runbook 142.3](../runbooks/sprint_142_3_incident_publications.md).

Potwierdzone przed sprintem naprawy: częściowy tick gracza usuwa wkład innych
graczy we wspólnym incydencie; timeout ostatniej operacji anuluje incydent;
mapa/BlackNet różnie filtrują expiry; publikacje delty nie mają wspólnego
commitu z incydentem. Radio pozostaje poza zakresem. Nie kopiować ciężkich
list_active/list_public bez limitu do nowego workera. Szczegóły i testy w audycie.

- Jedno źródło poziomu, heat, przyczyn eskalacji/wygaszania i powiązania
  incydentu z graczem oraz publicznym miejscem. Zmiana kamer wpływa na
  właściwy składnik, nie usuwa niezależnych powodów ryzyka.
- Prześledzić inicjację, eskalację, cooling i zakończenie, aktualizację NPC,
  delty mapy, GooglePlex News oraz fakty/publikacje BlackNet i ich CTA.
- Outbox, stabilne event_id i version: retry nie powiela wpisów, późny event
  nie cofa poziomu; restart publishera nadrabia zaległości. Niedostępność
  publikacji/Ollamy nie blokuje mechaniki i nie tworzy powtórnej kary.
- Wylogowanie inicjatora NIE kończy incydentu. Publiczne miejsce pozostaje
  dostępne i widoczne zgodnie z cyklem incydentu, może przyciągać graczy
  i intruzów. Sprawdzić TTL, cancellation, brak aktywnej operacji i cleanup:
  nie mogą traktować nieobecności jako przyczyny usunięcia incydentu.
- Dwie/trzy godziny offline nie są same w sobie warunkiem zakończenia.
  Odrębna, jawna reguła cyklu incydentu określa faktyczne zamknięcie;
  nie trzymać obiektów wiecznie ani nie kończyć ich razem z sesją gracza.

## 142.4 — kontrakt kwalifikacji i zabezpieczenie wejścia

Status: **IMPLEMENTACJA LOKALNA / ODBIÓR PRODUKCYJNY PENDING** (18 IX 2026).
Kontrakt i odbiór: [runbook 142.4](../runbooks/sprint_142_4_detection_qualification.md).
Produkcyjna ścieżka została przełączona na jawną obserwację: brak losowania,
wywołań starego executora i kar do czasu uszczelnienia kolejnych etapów.

- Backend ustala aktora, aktualną obecność, pozycję motocykla i jej wersję,
  status incydentu, NPC i tożsamość inicjatora z lekkich store’ów.
- Rozróżnić offline, sesję wygasłą/timeout, online nieaktywnego, inicjatora
  i postronnego. Sam timeout operacji nie jest timeoutem sesji.
- Offline: brak rzutu i kary; ponowne zalogowanie nie odtwarza zaległych kar.
- Odrzucać stare/przyszłe czasy, nieaktualną pozycję i cudze zgłoszenia bez
  serwerowego potwierdzenia. Publiczny tracking token nie jest autoryzacją.
- Globalna bramka bezpieczeństwa przed ciężkimi odczytami; przy brakujących
  projekcjach odroczenie/odrzucenie z przyczyną, bez fallbacku do profilu.
- Hotfix P0 w pierwszej paczce: uszczelnienie pozycji/czasu/presence; jeżeli
  obecny executor nie może bezpiecznie wykonać kary, jawny tryb obserwacji
  dla tej ścieżki, bez udawania sukcesu. Zmiana produkcyjnego trybu w runbooku.

## 142.5 — spotkanie i losowanie

Warunek poprzedzający ten etap: naprawiony kamerowy kontekst incydentu opisany
poniżej; szansa utworzenia incydentu i szansa kary 30/80 to odrębne etapy.

- Wprowadzić trwały encounter/receipt oraz pojedynczy serwerowy rzut:
  inicjator 80%, postronny 30%. Rzut i wynik także dla uniknięcia kary zapisane.
- Proponowana jednostka MVP: raz na gracza i incydent; patrole, karty,
  obserwatorzy, retry i reconnect nie tworzą nowego rzutu. Ponowne wejście
  do tego samego incydentu nie resetuje wyniku. Potwierdzić przed kodowaniem.
  Model receipt musi umożliwić odrębne, legalne kolejne zatrzymanie w 143;
  retry nie jest recydywą. Reguła nowego spotkania pozostaje do ustalenia.
- Incydent musi mieć trwałe przypisanie inicjatora, także po końcu operacji.
  Nie wyciągać roli wyłącznie z bieżącej aktywnej operacji.
- Reakcja na powrót online: sprawdzenie aktualnej sceny, nie historycznych punktów.
- Obsłużyć bounded serwerową detekcję aktywnych aktorów w pobliżu incydentu
  niezależnie od otwarcia mapy; żadnego skanowania pełnych profili ani
  pętli wszyscy gracze × wszystkie NPC. Wykorzystać indeks przestrzenny/presence.

## 142.6 — canonical wykonanie i recovery

- Wąski odczyt identity, position, presence, incident, operation, inventory,
  wallet. Przenieść Judgment/historię kar do osobnego małego store’u.
- Jedna transakcja: recheck online i wersji, decyzja/receipt, debit wallet,
  uninstall inventory+tool files+storage, anulowanie właściwej operacji,
  wpisy historii i outbox powiadomień/delt. Te same conn, bez schema init.
- Nie odinstalowywać przez profile.apps; nie wysyłać komunikatu przez
  profile.system_messages. Użyć dzisiejszych kanonicznych mechanizmów.
- Recovery po crash/rozłączeniu zwraca trwały wynik, wznawia pending bez
  ponownego losowania/pobrania. Nie zostawia wiecznie prepared.
- Zachować ochronę ostatniego narzędzia i rezerwę HC; recheck pod transakcją.
- Live: portfel, arsenał, otwarty menedżer plików, operacje i powiadomienie
  ofiary aktualizują się przez delty. Reconnect daje ten sam stan.

## 142.7 — testy całej ścieżki i odbiór

Test integracyjny od realnego scanu i autoryzowanego shutdown, przez różnicę
inicjacji/eskalacji, publikacje mapowe/media/BlackNet, aż po istniejącą karę
HC/narzędzia. Kontrola bez wyłączenia i z wyłączeniem; błędna aplikacja nie
daje ochrony. Weryfikować trwałe dane i odbiorców, nie tylko komunikat UI.
Osobny scenariusz: inicjator offline 2–3 h, inni gracze nadal widzą publiczne
miejsce i mogą do niego dotrzeć; powrót nie resetuje historii ani eskalacji.

Macierz: trzy służby × inicjator/postronny × online/offline/timeout/nieaktywny;
wewnątrz/na granicy/poza zasięgiem; powrót online; operacja zakończona;
brak narzędzi, ostatnie narzędzie, pusty portfel, obciążenie równoległe.

Testy deterministyczne rzutu na granicach 30/80, współbieżne dwa patrole
i obserwatorzy, ten sam POST, następny bucket, reconnect, crash przed/po commit,
awaria publikacji, stara epoka/sesja i zmiana presence między check/commit.
Sprawdzić rzeczywiste tabele canonical i outbox, nie tylko payload odpowiedzi.

Wymagana bramka wydajności: profile_full_read/write=0, profile_bytes=0;
zakazane get_profile/list_profiles/UserProfileManager/sync_session_profile;
mały profil i >=35 MB, bounded queries/payload, pomiar liczby zapytań i czasu
writer-locka oraz lokalny baseline p95. Próg czasowy ustalić po pomiarze
na porównywalnym środowisku, bez wymyślonych wyników produkcyjnych.

Rollout: wersjonowane schema/projekcje, dry-run/status/backup/apply/verify
tylko gdy wymagane; najpierw observe, potem kontrolowany przypadek autora,
na końcu full. Kill switch zatrzymuje nowe skutki, nie usuwa ledgeru.
DoD: wszystkie testy pełnej ścieżki, mapa reuse/adapt/clone, działające
publikacje i recovery, udokumentowane źródła danych, odbiór realnej kary/live
na desktop/mobile i powrotu po disconnect, brak niewyjaśnionych prepared.

## Decyzje do zamknięcia przed implementacją

Propozycje, nie istniejący gameplay: jedna próba na incydent; bierny online
jako postronny 30%, chyba że chroniony własnym niezwiązanym terytorium;
timeout sesji jak offline. Wyjaśnić znaczenie gameplayowego „timeoutu”.
Dla postronnego ustalić wybór konfiskowanego narzędzia (brak użytej operacji),
kwotę HC i czy kary występują razem. 30/80 to szansa konsekwencji, nie osobny
rzut dla każdej kary. Zachować stare limity jako punkt wyjścia do uzgodnienia.

Poza zakresem: więzienia, blokady komunikacji, ruchu i teleportów — sprint 143.

## Uzupełnienie zakresu — kamery jako źródło incydentów

Realizować w 142.2 przed kwalifikacją skutków. Audyt 16 IX potwierdził, że
redukcja starego camera_detected nie wpływa na publiczny operation_risk_meter.

1. Trwałe ID kamery, jednoznaczny typ i powiązanie z celem/scenem scanu.
   Zapis ograniczonego kontekstu ekspozycji przy rozpoczynaniu operacji;
   nowy scan/TTL nie może usuwać dowodu ani tworzyć darmowego resetu.
2. Canonical stan wyłączenia z expires_at i owner/scope; potwierdzenie
   wykonanej akcji na backendzie, nie z deklaracji `camera_disabled` klienta.
   Powiązać rzeczywisty shutdown z co najmniej jedną kamerą z właściwego scanu.
3. Bounded context do publicznego metera i inicjalizatora: wszystkie kamery
   aktywne podnoszą kamerowy składnik, jedna prawidłowo wyłączona go redukuje
   lub zeruje. Nie usuwać innych źródeł ryzyka (alarm ATM, hałas narzędzia itp.).
   Brak kamer w scanie nie może być automatycznym immunitetem na wszystkie incydenty.
4. Reakcja na start/koniec shutdown i ponowne włączenie, invalidacja/delta
   ryzyka, restart/reconnect. Nie cofać już wykonanych konsekwencji.
5. Worker pobiera potrzebne aktywne wyłączenia zbiorczo z indeksowanego store’u,
   bez profilowego assessment/fan-out, bez wszystkich kamer i operacji świata.

Testy: brak kamer; wszystkie aktywne; jedna off; dwie off (bez przypadkowego
stackowania); obca/odległa kamera; kończący się shutdown; ponowny scan;
snapshot TTL/brak snapshotu; restart; sfałszowany ID/off; jednoczesne incydenty;
realny canonical zapis akcji → zmiana heat → utworzenie/brak incydentu → NPC
→ kwalifikacja i kara. Mały profil i >=35 MB, zero full-profile I/O.

Zatwierdzono: +4 przy kamerach i brak ważnego shutdown; jedna wyłączona kamera
zeruje wyłącznie ten składnik, bez kumulacji. Osłona obejmuje operacje autora
przy tym samym obiekcie. Nie pomaga innym graczom, nie usuwa incydentu ani kar.
Wygaśnięcie lub anulowanie shutdown przywraca +4. Stare -18 pozostaje odrębną
mechaniką i nie jest balansem publicznego metera.
