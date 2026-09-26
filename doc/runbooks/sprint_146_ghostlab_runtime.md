# Sprint 146 — jeden pakiet runtime i skoordynowany odbiór

Stan: przygotowanie lokalne, 26 IX 2026. Bez commita, pusha i wdrożenia.
Odbiór produkcyjny pozostaje otwarty. Ten pakiet obejmuje bazowy sprint 146,
nie osobne sprinty 146.1–146.3 (bilety i konserwacja) ani GhostLab v2.0.

## Zakres pakietu

Aktywacja potomków Financial Sniffer, Friend Kicker, Security Panel Proxy,
Arsenal Cleaner i Intruder Kicker; regresja działającego System Log Reader.
Wspólne limity rodziny obejmują rodzica i wszystkich potomków. Zmiana nazwy,
kompilacja, aktualizacja, ponowna instalacja i drugi produkt nie odnawiają użycia.
Proxy można ponownie otwierać do końca tego samego dostępu. Pozostałe narzędzia
wykonują jedną próbę na rodzinę/dostęp; nieudane losowanie również zużywa próbę.

Wykonanie jest przypięte do zainstalowanego artefaktu. Transfery, relacje,
usunięcie aplikacji, komunikaty i receipt są zapisywane transakcyjnie.
Proxy używa wersjonowania canonical security; Intruder istniejącego transportu.
Arsenal emituje częściową deltę usunięcia i aktualny stan zajętości dysku,
bez odczytu całego inventory/profilu. Runtime nie czyta ani nie przepisuje
ciężkiego profilu. Badane błędy zapisu nie pozostawiają części skutku.

## Konfiguracja i aktualizacja istniejących produktów

`ecosystem.web.config.js` zawiera osobne przełączniki:

| Rodzina | Flaga |
|---|---|
| System Log Reader | `CHAOS_GHOSTLAB_LOG_RUNTIME_ENABLED` |
| Financial Sniffer | `CHAOS_GHOSTLAB_FINANCIAL_SNIFFER_RUNTIME_ENABLED` |
| Friend Kicker | `CHAOS_GHOSTLAB_FRIEND_KICKER_RUNTIME_ENABLED` |
| Security Panel Proxy | `CHAOS_GHOSTLAB_SECURITY_PANEL_PROXY_RUNTIME_ENABLED` |
| Arsenal Cleaner | `CHAOS_GHOSTLAB_ARSENAL_CLEANER_RUNTIME_ENABLED` |
| Intruder Kicker | `CHAOS_GHOSTLAB_INTRUDER_KICKER_RUNTIME_ENABLED` |

Flagi w pakiecie są włączone, ale wykonawców ogranicza istniejąca allowlista
`CHAOS_GHOSTLAB_RUNTIME_ACTORS=main,admin`. Autor może być innym graczem;
na allowliście musi być konto **używające** potomka. Udostępnienie wszystkim
graczom następuje dopiero po odbiorze, przez świadomą zmianę tej konfiguracji.

Stare buildy pięciu nowych rodzin pozostają zablokowane. Autor wykonuje:
**Save Draft → Compile → Publish**, a nabywca **Aktualizuj bezpłatnie**.
Nowy build ma `runtime_revision: 1`. Publikacja nie zmienia sama instalacji
nabywcy. Nie trzeba odinstalowywać aplikacji ani kupować jej drugi raz.
Wycofanej publikacji nie można kupić/aktualizować; wcześniej zainstalowany,
zgodny artefakt zachowuje istniejącą politykę działania.

Financial Sniffer: stary cooldown poniżej 180 minut trzeba podnieść przed
kompilacją. Arsenal: usuwanie pliku narzędzia jest obowiązkową polityką;
edytor pokazuje wartość serwerową, którą należy zapisać w drafcie. Stary build
nie jest modyfikowany w miejscu. Nie ma automatycznej migracji artefaktów.

## Pola blueprintu a wykonanie

| Rodzina | Rzeczywisty wpływ |
|---|---|
| Financial Sniffer | Kwota to minimum: losowanie według dotychczasowej formuły poziomu/respektu, zaokrąglony w dół procent salda celu i dostępne saldo. `steal_percent` ogranicza kwotę, nie zwiększa bazowego maksimum. `detection_percent` steruje wykryciem. `cooldown_minutes` 180–1440 obejmuje parę wykonawca–cel, także przy zmianie produktu/rodzica i nowym dostępie. Własne komunikaty sukcesu/braku kwoty oraz `reward_note` są prezentacją. |
| Friend Kicker | `success_percent` ogranicza bazową szansę. Polityka wyboru pozostaje losowym dozwolonym kontaktem. Udane zerwanie jest wykrywane jak u rodzica; przy porażce działa `detection_percent`. Dwa teksty trafiają do odpowiednich odbiorców. Pusta lista daje jawny brak efektu. |
| Security Panel Proxy | Stała polityka boolean, presety i macierz konfliktów serwera. Brak dowolnych pól profilu. Każdy zapis sprawdza wersję, dostęp, instalację, artefakt i areszt. |
| Arsenal Cleaner | `success_percent` ogranicza bazową szansę. Chronione aplikacje nie są kandydatami. Udane usunięcie jest wykrywane; porażka używa `detection_percent`. Instalacja i powiązane pliki znikają atomowo, zajętość dysku jest aktualizowana. Polityki ochrony i usunięcia plików są zablokowane dla autora. Nie dodano osobnej polityki anulowania operacji — obowiązuje istniejąca ścieżka uninstall. |
| Intruder Kicker | Własny komunikat sukcesu; kwalifikacja i ruch pozostają po stronie serwera: aktualny dostęp, intruz, własne terytorium, dozwolona pozycja, brak aresztu. |

Quality/reliability w katalogu nie dodają drugiego mnożnika skuteczności.
Nie wprowadzono opłat za użycie. Kradzież HC jest transferem cel → wykonawca;
zakup pozostaje transferem do autora według istniejącej wyceny katalogowej.
Limit procentowy nie pozwala wyprodukować HC ani ujemnego salda. Wynik 0 HC
jest poprawnym wykonaniem i ma receipt/cooldown.

## Jedno wdrożenie — operator

1. Zachować kopię bazy przez SQLite backup oraz poprzedni pakiet kodu i konfiguracji.
   Nie kopiować samego pliku aktywnej bazy z pominięciem WAL.
2. Dostarczyć cały przygotowany zestaw zmian wybraną metodą wydania. Lokalny pakiet
   nie został wysłany do Git; samo `git pull` nie pobierze tych zmian.
3. Wymagany jest wcześniej wdrożony 144.3 i 145, z canonical stores i zakończonymi
   migracjami. Bazowy 146 nie dodaje migracji schematu ani masowego zapisu profili.
4. Sprawdzić allowlistę wykonawców i flagi. Uruchomić na serwerze:

   ```sh
   pm2 startOrRestart ecosystem.web.config.js --update-env
   pm2 logs chaos --lines 80 --nostream
   ```

5. Odświeżyć desktop/WebDragona z pominięciem cache. Oba warianty desktopu mają
   nową wersję `terminal.js`. Sprawdzić publikację i bezpłatną aktualizację przed
   uzyskaniem dostępu PvP, aby nie zużywać jego czasu na przygotowanie.

## Przygotowanie trzech kont — bez uruchamiania hakowania

| Rola | Przygotowanie |
|---|---|
| A — autor, zwykły gracz | Publikuje pięć rozpoznawalnie nazwanych potomków. Nie używać konta systemowego jako kontaktu do Friend Kickera. Zapisuje saldo i liczbę pobrań przed zakupami. |
| B — wykonawca, np. main | Konto z allowlisty, poziom i respekt spełniają wymagania produktów, bez aresztu. Kupuje/aktualizuje wszystkie potomki przed rundą. Zapisuje ceny i saldo. Rodzice są opcjonalni, potrzebni tylko do sprawdzenia wspólnego limitu. |
| C — cel | Zwykły gracz bez blokady kolejnego dostępu B→C. Ma dodatnie saldo, jedną relację z A i jedną zbędną aplikację dopuszczoną do czyszczenia. Nie jest znajomym/klanowiczem B. Stoi jako intruz wewnątrz terytorium B. |

Spisać stan początkowy C: saldo, kontakt A, nazwa/id zbędnej aplikacji,
zajętość dysku, zabezpieczenie do zmiany i pozycja. Pozostałe cenne, możliwe do
usunięcia aplikacje C mogą zostać wylosowane — użyć przygotowanego konta testowego.
Sprawdzić nazwy/ikony, zakup każdego potomka, przyrost salda autora i instalację
bez posiadania rodzica. Cena z katalogu jest wiążąca, nie sugerowana cena autora.

Wszystkie launchery i dopasowanie mobile można obejrzeć przed dostępem PvP.
Nie tworzyć drugiej sesji B w środku rundy; zmiana generacji unieważnia poprzednią.

## Główna runda — jeden aktywny dostęp B→C

Po uzyskaniu dostępu wykonać kroki w tej kolejności. A i C mają otwarte własne
okna do obserwowania skutków. Intruder zawsze na końcu, bo zmienia pozycję celu.

| Kolejność | Test | PASS |
|---|---|---|
| 1 | Potomek Proxy: otworzyć, zmienić dozwolony przełącznik | C widzi zmianę, obce ustawienia pozostają. |
| 2 | C zmienia security; B zapisuje ze starą wersją | Konflikt bez nadpisania; Odśwież pobiera nową wersję, kolejny dozwolony zapis działa. Zamknięcie i ponowne otwarcie zachowuje dostęp bez nowego użycia i resetu czasu. |
| 3 | Potomek Syslog (regresja) | Odczyt działa, limit obejmuje rodzica/rodzeństwo. |
| 4 | Potomek Financial Sniffer | Różnica sald B/C odpowiada pokazanej kwocie; drugi produkt/rodzic nie wykonuje ponownie transferu. Zachować kwotę i receipt. |
| 5 | Potomek Friend Kicker | Sukces usuwa jedną relację po obu stronach, właściwe komunikaty trafiają do C/A. Porażka jest opisana uczciwie i nie zmienia kontaktów. |
| 6 | Potomek Arsenal Cleaner | Przy sukcesie ta sama aplikacja znika z instalacji, pulpitu i FM C; dysk się aktualizuje. Powtórzenie nie usuwa kolejnej aplikacji. |
| 7 | Potomek Intruder Kicker | C zostaje wypchnięty zgodnie z regułami terytorium; kolejne użycie potomka/rodzica nie porusza C drugi raz. |

Na mobile sprawdzić launcher i wynik bez poziomego przewijania, przyciski i
ponowne otwarcie Proxy. Zmiana szerokości tej samej sesji pozwala sprawdzić układ
w rundzie; realne urządzenie można odebrać w osobnej rundzie bez wyłączania limitów.

Losowanie Friend/Arsenal może się nie udać. To PASS ścieżki porażki, **nie** PASS
skutecznego usunięcia. Dokończyć pozostałe rodziny; brakujący sukces odebrać przy
następnym legalnym dostępie po cooldownie. Nie kasować receiptów ani kartoteki.
Areszt przerywa rundę zgodnie z regułami gry; najpierw odbyć karę/zwolnienie,
następnie ustalić pozostałe testy. Nie obiecywać pełnego odbioru w jednym losowaniu.

## Dodatkowy odbiór bez marnowania prób

- Po rundzie: reconnect C nie przywraca aplikacji, kontaktu ani starej pozycji.
- Aktualizacja jednego potomka po zmianie blueprintu: nowy build w tym samym wpisie,
  bezpłatny update, brak odnowienia limitu zużytej rodziny.
- Wycofanie sprzedaży blokuje nowy zakup, bez usunięcia istniejącej instalacji.
- Utrata dostępu blokuje wykonanie i zapis Proxy. Areszt blokuje wszystkie rodziny.
- Wyłączona flaga konkretnej rodziny daje powód odmowy, pozostałe nadal działają.
  Test wyłączenia wykonać przed rundą lub po niej, nie restartować procesu w jej środku.
- Dłuższy cooldown Sniffera sprawdzić przy następnym dostępie do tego samego celu;
  samo odświeżenie/zmiana produktu nie może go skrócić.

Automatycznie testowane są także konkurencyjne żądania, fałszywy artefakt,
rollback po awarii notyfikacji, cofnięcie dostępu przed commit, pusty wynik,
chronione aplikacje, areszt i zero-heavy. Tych awarii nie wymuszamy na produkcji.
Do raportu zapisać konto/produkt/build, rodzinę, czas, wynik i receipt; nie wklejać
prywatnych logów celu. Statusy serwerowe uzupełniać dopiero po rzeczywistym teście.

## Rollback aktywacji

Ustawić odpowiednią flagę na `false`, zrestartować web z `--update-env` i odświeżyć
UI. Nie usuwać poprawnie wykonanych skutków ani historii. Cofnięcie kodu wymaga
spójnego poprzedniego pakietu; nie przywracać starej bazy ponad późniejszymi zakupami
i ruchem graczy. Wyłączenie runtime nie jest zwrotem HC ani odwróceniem efektów.

## Walidacja lokalna

Testy Pythona uruchamiać wyłącznie przez `tools/run_isolated_tests.py` na tymczasowej
bazie, nigdy przez import `run` z roboczym katalogiem danych gry. Zestaw obejmuje
nowe `tests/test_ghostlab_mutation_runtime.py`, runtime/publication/registry/alignment,
Player Hack Access/finalization/disconnect/read paths, Intruder i canonical wallet.
Testy JS obejmują launcher, publikację, request guard, czytnik logów i częściową
deltę ekwipunku. Wynik automatyczny nie zastępuje odbioru serwerowego powyżej.

Wynik lokalny 26 IX 2026:

- 15 nowych testów mutacji: PASS (w tym pełny zakup/użycie pięciu rodzin na trzech
  kontach, równoczesne wykonanie, rollback, blokady i kontrola ciężkich odczytów).
- Ostatni zestaw 76 testów registry/alignment/publication/runtime, Intruder,
  disconnect i wallet runtime: PASS.
- Canonical wallet oraz read paths/Arsenal: PASS. Dwa stare testy security
  zaktualizowano, aby badały rzeczywisty canonical writer, zamiast niewywoływanego
  zapisu profilu. Test walletu dostał aktualną atrapę resolvera produktu.
- Pięć zestawów JS (runtime, publication, request guard, log reader, inventory
  delta), składnia terminal.js i `git diff --check`: PASS.
- Desktop/mobile i skutki na serwerze: **DO ODBIORU** według tabeli powyżej.
