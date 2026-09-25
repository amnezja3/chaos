# Sprint 144.3 — pro-toolsy, admin i PvP

Status: **PASS — ZAMKNIĘTY**, 25 IX 2026. Wdrożenie i odbiór produkcyjny potwierdzone przez użytkownika.

### Odbiór serwerowy 25 IX 2026

- Audyt katalogu PASS po usunięciu starego wpisu testowego ghostlab_getsfilen_1
  (kopia bazy, 1 usunięty wpis, 5 kanonicznych publikacji, brak anomalii).
- Migracja zabezpieczeń: 37/37 migrated.
- Admin PASS. Syslog: instalacja → obecny, runtime pending → uninstall → znika: PASS.
- Blokady aresztu oraz zapis zabezpieczeń zgodny na obu kontach: PASS.
- Nieaktualna wersja odrzucona jako profile_write_conflict: PASS.
- Wykryto brak możliwości ponownego otwarcia użytego Proxy po zamknięciu okna
  lub odświeżeniu strony. Poprawka dodaje can_reopen i odczyt GET istniejącego
  panelu bez nowego użycia narzędzia; nie resetuje receipt ani czasu dostępu.
  Ponowne otwarcie Proxy: PASS potwierdzony przez użytkownika.
  Pozostałe pięć narzędzi po użyciu pozostaje zablokowanych: PASS.
  Dalszy zapis po odświeżeniu konfliktu wersji rodzica: PASS potwierdzony przez użytkownika.
- Potomek Security Panel Proxy: utworzenie/publikacja/instalacja, własna marka
  na liście PvP i zablokowany runtime: PASS potwierdzony przez użytkownika.
  Odświeżanie i mutacje potomka będą testowane po wdrożeniu runtime w 146;
  nie są oznaczone jako wykonane w 144.3.
- Końcowy odbiór użytkownika: warianty listy PvP PASS, w tym pusty stan,
  sam potomek oraz rodzic i potomek. Kilku potomków sprawdzono na koncie main: PASS.
- Potomek Intruder Kicker (IKP_v2): tworzenie/publikacja/instalacja i runtime pending: PASS.
- Zakup potomka oraz wycofana publikacja z zachowaniem instalacji: PASS.
- Mobile: PASS. Wszystkie pozostałe po poprzednim odbiorze testy serwerowe potwierdzone.

## Dostarczone

- Jawne przypisanie wszystkich 11 pro-toolsów w kodzie: 6 GLab, 5 non-GLab.
  Intruder Kicker ma szósty kontrakt, sztywne kwalifikowanie intruza we własnym
  terytorium i limit rodziny na dostęp. Istniejący wykonawca pozostaje bez zmian;
  runtime potomstwa nadal oczekuje na 145–146.
- Admin → GhostLab: kontrakty, pro-tool źródłowy, dostępność; stronicowana lista
  produktów z autorem, nazwą, ikoną, datą projektu, ceną, pobraniami i publikacją.
  Filtrowanie po szablonie i nazwie/autorze. Szkice nie są ofertami; withdraw
  pozostaje w historii. Nie odtwarzamy brakujących dat datą migracji.
- PvP korzysta z canonical inventory, pokazuje tylko posiadane produkty właściwego
  zastosowania. Potomek bez rodzica jest widoczny, ale ma `runtime_pending`.
  Własna marka pochodzi z opublikowanego buildu, nie z nazwy ani flag katalogu.
  Wycofanie sprzedaży nie usuwa instalacji. Nowa publikacja nie aktualizuje jej
  automatycznie. Stary receipt rodzica blokuje całą rodzinę; nie resetujemy użyć.
- Odświeżenie listy przy deltach instalacji/usunięcia, blokada spóźnionych
  odpowiedzi po zmianie dostępu. Okna wyników przyjmują markę zatwierdzonego
  produktu; dispatch pozostaje po jawnie obsługiwanych result_type.
- `player_security`: osobny stan z wersją. Security update/preset i ustawienia
  własne bez pełnego profilu. Transakcja, konflikt wersji, SECURITY_CONFLICTS,
  dostęp, instalacja, wersja artefaktu i areszt sprawdzane przed skutkiem/commitem.
  Panel ma odświeżenie danych po konflikcie, bez ponownego wykonania mutacji.
  Stary zapis profilu nie nadpisuje canonical security; odczyty projekcji i
  legacy get_profile nakładają stan kanoniczny. Brak migracji daje jawny recovery.
- Wykryta podczas realizacji ciężka instalacja pro-toolsów/GLab usunięta:
  istniejący bounded installer, canonical wallet/inventory, płatność do dotychczasowego
  odbiorcy i wymagania z projekcji. Zakup potomka sprawdza kanoniczną publikację
  ponownie w transakcji. Bez nowych zasad cen, balansu ani automatycznego update.

## Pobrania

Zachowujemy historyczny licznik katalogu jako bazę. Nowe instalacje sklepowe
liczy `googleplex_download_counts`, jeden raz dla klucza zakupu; retry nie dodaje
pobrania. Seed/import do inventory nie dodaje pobrań. To dotychczasowa semantyka
zdarzeń zakupu, nie obietnica liczby unikalnych graczy. Admin i Googleplex pokazują
bazę plus licznik kanoniczny. Narzędzie audytu wykrywa bazę wymagającą uzgodnienia
z wcześniejszym katalogiem; opcjonalny apply kopiuje wyłącznie wyższy licznik,
nie zmienia autora, ID, ceny ani powiązań.

## Sprawdzenie przed restartem

Nie migrować ponownie projektów ani 37 kont z bazowego 144. Po dostarczeniu kodu:

```sh
.venv/bin/python tools/audit_glab_catalog.py
.venv/bin/python tools/migrate_player_security.py
```

Oba polecenia domyślnie tylko raportują. Najpierw przejrzeć wyniki. Anomalie
pochodzenia produktu lub `invalid_projection` wyjaśnić przed wdrożeniem;
nie przypisywać autora/szablonu po nazwie.

Na krótkie okno migracji zatrzymać stare procesy CHAOS zapisujące stan graczy
(web i workery według aktywnych ecosystemów). Następnie:

```sh
.venv/bin/python tools/migrate_player_security.py --apply
```

Polecenie tworzy kopię SQLite w `backups/`, a potem przenosi wyłącznie małą,
zweryfikowaną projekcję zabezpieczeń. Nie czyta/zapisuje ciężkich profili ani
nie nadpisuje istniejącego stanu canonical. Ponowienie daje pustą listę.
Jeżeli audyt podał `download_baseline_updates`, osobno wykonać:

```sh
.venv/bin/python tools/audit_glab_catalog.py --apply-download-baselines
```

Ta operacja również robi kopię bazy. Po poprawnych raportach uruchomić procesy
z ich ecosystemów; web:

```sh
pm2 startOrRestart ecosystem.web.config.js --update-env
```

Odświeżyć grę Ctrl+Shift+R. Nie włączać runtime potomstwa na tym etapie.

## Odbiór serwerowy

1. Admin-only: GhostLab pokazuje 6 szablonów i 5 non-GLab; Syslog, produkty
   dwóch autorów i legacy admina mają prawidłowe dane. Sprawdzić filtr i pager.
2. Intruder Kicker: tworzenie, zapis, Compile, Publish; stałych polityk nie można
   zmienić. Runtime pending jest oczekiwany.
3. PvP: pusta lista, sam rodzic, sam potomek, rodzic i dwa potomki. Brak szarych
   nieposiadanych rodziców; pending widoczny tylko dla faktycznie zainstalowanego
   potomka. Po uninstall/konfiskacie przycisk znika. Rodzina użyta wcześniej
   pozostaje użyta. Wycofany produkt nadal widoczny, jeśli był zainstalowany.
4. Wbudowany Security Panel Proxy: odczyt → zmiana boolean → preset; weryfikacja
   drugiego writera przez ustawienia ofiary, konflikt starej wersji i Odśwież.
   Wygaśnięcie dostępu/uninstall/areszt nie dopuszcza mutacji.
5. Zakup: wymagania, saldo, odbiorca, instalacja, ponowienie bez drugiej opłaty;
   licznik nie rośnie przy retry. Dotychczasowa instalacja zachowuje swój build.
6. Desktop/mobile: admin, lista PvP i marka wyniku. Raport serwera jest osobnym
   dowodem — lokalne testy nie oznaczają produkcyjnego PASS.

## Testy lokalne

Regresja: registry/publication, alignment, player_hack_read_paths, intruder_kicker,
Agi2108BoundedInstallTest, admin_panel_lazy. Testy alignment blokują pełne helpery
profilu i SQL profile_json; obejmują odmowę, retry, stare wersje, podszywanie się,
withdraw, legacy receipt, płatność i instalację. Ciężkie fixture 35 MB w regresji PvP.
Testy JS: lifecycle okna, request guard, log reader, financial result, publikacja GLab.
25 IX 2026: regresja Python PASS (36 testów alignment/Intruder/publication/admin,
następnie 37 testów alignment/AGI/PvP/registry po zabezpieczeniu pierwszeństwa
kontraktu wbudowanego produktu). Wszystkie pięć wymienionych skryptów JS PASS;
kontrola składni JS i git diff --check PASS. Odbiór serwerowy i wizualny
potwierdzono następnie przez użytkownika, zgodnie z wynikami powyżej.

## Dodanie następnego pro-toola i cofnięcie aktywacji

Logika w kodzie → jawna decyzja PRO_TOOL_GLAB → kontrakt TEMPLATES jeśli GLab
(lub samodzielny szablon bez rodzica) → test rejestru/defaultów/granic → testy
inventory/publikacji/zero-heavy → raport katalogu → odbiór admina i potomstwa.
Admin nie dodaje logiki ani nie zmienia kontraktów.

Cofnięcie dostępności tworzenia/publikacji wykonuje się flagami rejestru,
bez usuwania projektów/buildów/zakupów. Runtime pozostaje wyłączony w tym etapie.
Po cutoverze security nie wracać do starego writera profilu ani nie odtwarzać całej
bazy po nowych transakcjach; poprawka musi zachować player_security jako źródło prawdy.
