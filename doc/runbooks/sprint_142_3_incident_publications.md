# 142.3 — trwałość i publikacja incydentów

Status: PASS autora 18 IX 2026 — potwierdzone hero, produkty i przepływ publikacji.
Reguła cyklu zatwierdzona przez autora 17 IX 2026. Poniższe wcześniejsze
opisy lokalnej walidacji są zapisem wdrożenia; nie oznaczają otwartego odbioru.

WebDragons ma przycisk refresh obok strzałek. Pobiera bieżące dane aktywnej
zakładki, zachowuje wyszukiwanie i blokuje wielokrotne kliknięcia w trakcie
żądania. News korzysta z istniejącego endpointu bez cache i nie uruchamia
modelu. Zmieniono wersję assetu terminal.js w trzech szablonach. Walidacja:
`node --check static/js/terminal.js` oraz `git diff --check` PASS.

Po deployu odświeżyć cały klient raz, aby pobrać przycisk. Następnie przez
kilka godzin aktywności graczy obserwować rotację, wiek publikacji, kolejkę
Ollamy i poprawność odnośników za pomocą refreshu w WebDragons. Jakość tekstów,
deterministyczne wpisy zastępcze i dalsza rotacja narzędzi pozostają w zakresie
przyszłych sprintów Ollamy. Nie są blokadą 142.3.

## Cykl

Aktywna operacja podtrzymuje incydent niezależnie od sesji gracza. Po końcu
ostatniej operacji następuje cooling na 30 minut; incydent pozostaje na mapie
i w BlackNecie. Powtórny tick i restart nie przesuwają końca cooling.
Operacja powyżej progu przy tym miejscu ponownie aktywuje niewygaszony incydent.
Po 30 minutach bez operacji stan zmienia się na resolved. Dłuższa nieobecność
nie jest warunkiem zamknięcia: rozstrzyga cykl operacji i incydentu.

Heat, poziom i przypisanie do incydentu wylicza wspólny inicjalizator.
W transakcji SQLite odczytuje również canonical operacje innych uczestników;
częściowy tick ani konkurujące ticki nie usuwają ich wkładów.
Znana osłona kamer z 142.2 nadal dotyczy tylko swojego składnika.

## Trwałość i koszt

- Incident, audit, membership i head publikacji zapisują się atomowo.
- response_incident_publications przechowuje jeden aktualizowany head na
  incydent, delivered_version, wersję batcha, kursor odbiorców i lease 60 s.
  Restart ponawia niedostarczoną publikację. Idempotencja delty jest po
  incydencie/kapsule, wersji i odbiorcy.
- Tick obsługuje do 32 incydentów; relay do 8 headów, po 64 konta ze wąskiej
  user_identity_projection na stronę. Canonical przypisania są indeksowane;
  spatial lookup ma limit 32 kandydatów na operację. Publiczne listy incydentów
  mają limit 256. Nie dodano list_profiles ani get_profile do nowego workera.
- Kolejna wersja podczas dostarczania nie resetuje kursora przed końcem strony
  odbiorców; po zakończeniu batcha najnowszy head jest odtwarzany od początku.
- Snapshot publiczny jest recovery. Mapa i BlackNet wykluczają wygasłe cooling
  według tej samej reguły. Cache BlackNet odświeża tylko fakty incydentów;
  nie wymusza odczytu pełnych profili przy każdej zmianie heat.
- Stan incydentu zmienia się bez zależności od dostępności modelu. Błąd
  publikacji zostawia zadanie do retry, a nie powtarza mechaniki ani kary.

## Media i NPC

Publiczne delty są dostarczane stronami do kont obserwatorów. NPC nie przyjmują
starszej wersji incydentu, a mapa chroni również usunięty marker przed późnym
starym eventem. Koniec cooling powoduje usunięcie kapsuł.

BlackNet zachowuje deterministyczne fakty i bezpieczne CTA. Narracja BlackNet
trafia do istniejącej kolejki Ollamy/publication receipts. Googleplex
News nadal wybiera kwalifikujące się incydenty przez istniejący scheduler;
nie każdy incydent musi otrzymać artykuł. Brak odpowiedzi modelu nie wyłącza mapy.

Radio jest poza zakresem 142.3; dodany omyłkowo biuletyn został usunięty.
Publisher sprawdza canonical wersję publicznego stanu incydentu w transakcji;
spóźniony wynik nie może publikować zamkniętego/starszego stanu. Nieaktualne
publikacje są wycofywane z aktywnego widoku przez relay, pozostając w historii.

## Deploy

Przed aktualizacją zachować standardowy backup SQLite. Rozszerzenie schematu
jest addytywne: tabele response_incident_members i response_incident_publications
oraz indeksy tworzone przy inicjalizacji store'ów. Bez pełnej migracji profili.
Istniejące incydenty są uzupełniane partiami przez lifecycle worker; zaległe,
faktycznie zakończone operacje mogą doprowadzić do resolved według nowej reguły.

Po pobraniu zmian restartować **wszystkie cztery procesy po nazwie**:

```bash
pm2 startOrRestart ecosystem.web.config.js --update-env
pm2 startOrRestart ecosystem.territory-worker.config.js --update-env
pm2 startOrRestart ecosystem.ollama-worker.config.js --update-env
pm2 startOrRestart ecosystem.narrative-publisher.config.js --update-env
pm2 save
pm2 list
```

Ograniczyć okno mieszania wersji; podczas kontrolowanego deployu można zatrzymać
te procesy przed aktualizacją. Sam restart weba pozostawia stary worker/metery
albo stary registry promptów. Odświeżyć kartę gry po deployu.

Nie wystarcza restart po nazwie: log produkcyjny wskazał publisher `disabled`.
Włączenie Ollamy/publishera, pusty filtr SOURCE_EVENT_ID i wyłączenie legacy queue
są zapisane jawnie w ecosystemach. Po wdrożeniu oczekiwany log publishera:
`status=started`, a nie `disabled`. Nie używać jednorazowych exportów w shellu.
Scheduler loguje również `googleplex_status` i `googleplex_reason`; jego
interwał w ecosystemie territory wynosi 900 s. Przetwarzanie modelu może
wydłużyć czas pojawienia się nowego wpisu.

Recovery wycofuje do 32 nieaktualnych zleceń incydentów na przebieg, bez
kasowania historii i odczytu profili. Brak canonical incident_context w starym
zleceniu blokuje publikację. Rozwiązane/wygasłe cooling i starsze wersje
nie zajmują miejsca na nowe zadania GooglePlex i tracą aktywne publikacje.

## Walidacja i odbiór

Kolejna korekta obejmuje całą ścieżkę zadań Ollamy: expires_at, priorytety klas,
source key/version, retry bez odnawiania terminu i odrzucenie spóźnionej generacji.
Kontrakt, limity i diagnostyka:
[audyt ważności kolejki](../audits/narrative_freshness_priority_2026_09_17.md).
Schemat outboxu otrzymuje addytywnie expires_at i indeks; legacy kolejka jest
porządkowana partiami po 32, bez kasowania historycznych rekordów.

Korekta zakresu: radio odłożone na później. Po usunięciu tej ścieżki:
27 testów publishera PASS i 19 testów incydentów/pipeline PASS;
kontrola składni odtwarzacza PASS. Autor potwierdził już wszystkie punkty
gameplay oraz kierunek NPC; otwarty punkt 5 dotyczy BlackNetu i GooglePlex News.
Recovery mediów: 45 testów publishera/incydentów PASS, następnie 13 testów
recovery/PM2/harmonogramu PASS; test JS ecosystemów PASS także przy starych
flagach false i filtrze zdarzenia w otoczeniu.

Lokalny wynik 17 IX 2026: **110 testów Python PASS (112,037 s)** przez
`tools/run_isolated_tests.py`, na tymczasowych bazach poza danymi gry.
Zakres: lifecycle/publications, initializer, pipeline audit, public map,
BlackNet bridge, camera exposure, NPC, territory worker, narrative publications,
operation risk meter i camera shutdown contract. Dodatkowo
`node tests/js/test_incident_version_guard.js` PASS oraz kontrola składni
`node --check static/js/ghost_radio.js` PASS. Sprawdzono też zerowy wkład
aktywnej operacji i spóźniony runtime po canonical anulowaniu.

Automatyczne testy obejmują: 30-minutowe cooling i brak resetu, operację trwającą
ponad trzy godziny, reactivation, równoległych aktorów i canonical terminal state,
atomowy rollback outboxu, recovery publishera, pagination z nowym headem,
zgodność mapy/BlackNet, fan-out i dedupe, stale NPC, BlackNet do medium record,
odrzucenie spóźnionego biuletynu oraz brak wywołań pełnych profili.
Test JS sprawdza starą deltę usunięcia i próbę przywrócenia starego markera.

Gameplay po deployu, krok po kroku:

1. Doprowadzić operację do incydentu. Na dwóch kontach sprawdzić publiczny
   marker i kapsuły oraz zgodne miejsce w BlackNecie.
2. Zakończyć ostatnią operację. Incydent ma pozostać jako cooling, także
   po wylogowaniu inicjatora. Reconnect nie rozpoczyna nowego odliczania.
3. Potwierdzić zamknięcie po 30 minutach bez aktywnych operacji — marker i NPC
   znikają, BlackNet nie daje aktywnego CTA do zakończonego incydentu.
4. Osobny przypadek: operacja powyżej progu podczas cooling ponownie aktywuje
   incydent. Nie mieszać tego z pomiarem nieprzerwanego cooling w punkcie 3.
5. Sprawdzić publikację incydentu w BlackNecie oraz kwalifikującego się
   incydentu w GooglePlex News. Czas publikacji zależy od kolejki/modelu i
   kwalifikacji przez scheduler. Nie interpretować opóźnienia jako
   awarii samego cyklu incydentu. Odbiór wizualny desktop/mobile pozostaje ręczny.

Nie wykonano deployu, produkcyjnego pomiaru p95 ani ręcznej weryfikacji UI.
Kwalifikacja spotkań i wykonanie kar pozostają zakresem 142.4–142.6.
