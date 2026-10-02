# Sprint 147 — prosty kreator, losowana moc i trwała mechanika

Status: **W TRAKCIE — rozpoczęty 1 X 2026**. Fundament backendu zaimplementowany;
pełny runtime, migracja i odbiór pozostają otwarte. Nie jest to pakiet do wdrożenia ani PASS.
Po PASS [146.5](sprint_146_5_ghostlab_v1_completion.md); kontynuacja:
[148 — UX, edycja i aktualizacje](sprint_148_creator_ux_runtime_completion.md).
Zastępuje wcześniejszy model automatycznej pełnej mocy od LVL 40.
Historyczna podstawa: [audyt kreatorów](../audits/creators_gameplay_audit_2026_09_24.md).

## Cel i prosty kontrakt

Kreatory mają być prostsze od GhostLaba: gracze tworzą dużo aktywnych narzędzi
na własny użytek, dla innych i dla zabawy. Zdobywanie, poznawanie i dobór narzędzi
są częścią rozgrywki, a mocny produkt może być wartościowym wynikiem tworzenia.

**Nazwa + ikona + akcja/opcja mapy + czy tworzyć plik → system generuje parametry
→ końcowy edytor interfejsu i publikacji.** Bez dawnej serii formularzy technicznych.

## 147.1 — system dobiera mechanikę

- Wersjonowany katalog mapuje akcję na rodzinę, cel, executor, warunki, możliwości
  i pliki. Autor wybiera tworzenie pliku tak/nie; właściwe typy przypisuje system.
  Niezgodne połączenia są walidowane, a nie po cichu zmieniane.
- Pokazywać tylko działające akcje. Uwzględnić istniejące scan/recon, exploit,
  implant, sniff, śledzenie, kamery, audio/mikrofon, Wi-Fi i pliki zgodnie z audytem.
- Jedna aplikacja ma spójne przeznaczenie; wiele komend lub przycisków nie nadaje
  niepowiązanych zdolności. Brak executora nie może być zastąpiony obietnicą w opisie.
- **XMapper zostaje.** Według testów autora hakuje kropkę exploita i cały pasek
  zabezpieczeń. Zachować to w regresji; gracze mają móc tworzyć równie mocne
  narzędzia w odpowiednich profilach. Nie osłabiać go przy migracji.

## 147.2 — poziom wyznacza maksimum, losowanie rzeczywistą moc

- Poziom pobiera backend z małej projekcji. Wyznacza sufit, nie gwarantowany wynik.
- Punkty odniesienia: **LVL 30 — maksimum około 95%; LVL 40 — możliwe 100%**.
  Zatwierdzona 1 X tabela w configu: L1=25%, L10=50%, L20=75%, L30=95%, L40+=100%,
  interpolacja liniowa między progami (wynik całkowity zaokrąglany w dół).
  Dawna formuła `min(level,40)/40` nie odpowiada nowym ustaleniom.
- Po ustaleniu sufitu system losuje realną moc, np. 50%, 70% lub maksimum.
  Startowa szansa maksymalnego wariantu: **50/50**, konfigurowalna do późniejszego
  strojenia. Druga gałąź losuje wyłącznie poniżej maksimum, żeby nie zwiększać
  faktycznej szansy ponad config. Zatwierdzone minimum słabszej gałęzi: 20%;
  losowanie jednostajne całkowite do sufitu minus jeden punkt procentowy.
- Parametry są generowane raz i zapisywane z ID generacji, poziomem autora oraz
  wersją policy. Retry, zapis, preview, publikacja i korekta tekstu nie losują ponownie.
  Nowy projekt jest nową próbą; nie dodawać nieuzgodnionych opłat za losowanie.
- Awans autora nie wzmacnia istniejącego produktu w tle. UI odróżnia sufit od wyniku.
- Moc to wpływ we właściwej mechanice; dla zgodnego exploita 100% może rozbroić
  cały pasek. To nie to samo co szansa wygenerowania wariantu czy niezawodność użycia.
  Nie omija dostępu, aresztu, własności, warunków celu i ryzyka incydentu.

## 147.3 — ręczny effect tylko w Button Choice

- Button Choice (obecny Button Maker) pokazuje pole `effect` wszystkim graczom.
  Wartość działa dopiero od wysokiego poziomu; roboczy próg **LVL 100** jest
  konfigurowalny, zgodnie z przykładem autora.
- Poniżej progu wpis nie nadaje efektu; UI jasno to wyjaśnia. Obowiązuje zwykła
  systemowa generacja. Powyżej progu serwer waliduje identyfikator, typ, zakres,
  zgodność z przeznaczeniem i uprawnieniami. Nieznany efekt daje czytelny błąd.
- Jest to wewnętrzny hakerski input, nie dowolny kod ani niekontrolowane klucze
  zabezpieczeń. Potężne efekty mogą umożliwiać narzędzia podobne do XMappera.
- Katalog musi określać, które zatwierdzone efekty ustalają wynik bezpośrednio,
  a które korzystają z losowania. Ustalić to przed implementacją, bez utożsamiania
  progu LVL 40 na losowe maksimum z progiem dostępu do ręcznego efektu.
- Term Creator, Window Maker i AppForge nie mają ręcznego `effect`; ich moc ustala
  system i losowanie. Backend odrzuca próby przemycenia efektu w innym polu.
- Weryfikować poziom autora przy zatwierdzaniu mechaniki, nie poziom późniejszego
  kupującego. Zwykłe wymagania używania narzędzia pozostają niezależne.

## 147.4 — wiedza w obiegu gry

Materiały szkoleniowe i PTK dostępne w Googleplexie uczą zatwierdzonych wartości
`effect` i ich zastosowań. Gracz zdobywa wiedzę i buduje zaawansowane narzędzia.
To część 147–148, nie wyłączenie z zakresu. Reuse obiegu PTK; materiał nie nadaje
uprawnień i nie zastępuje walidacji. Przykłady muszą odpowiadać realnym executorom.

## 147.5 — projekt, publikacja i zamrożona logika

- Projekt i produkt mają trwałe ID. Pierwsza publikacja zamraża przeznaczenie,
  tworzenie/typy plików, mechaniki, moc, efekty, sposób działania i cenę.
  Także ceny płatnych opcji należą do zablokowanego kontraktu.
- Później edytowalne są tylko elementy prezentacyjne: nazwa/tytuł, opis, ikona,
  logi, outputy, etykiety i prezentacja oferty. Serwer stosuje listę dozwolonych
  zmian i porównuje logikę z pierwszym opublikowanym kontraktem.
- Zmiana tekstu komendy lub przycisku nie zmienia akcji, efektu ani ceny.
  Nowa mechanika wymaga nowego projektu, nie aktualizacji istniejącego produktu.
- Nowe wydanie zastępuje ofertę pod tym samym ID. Stare instalacje pozostają
  niezmienne; dotychczasowy nabywca ma bezpłatną **AKTUALIZACJĘ**. UX dopina 148.

## 147.6 — ceny, wykonanie, kompatybilność

- Rozdzielić zakup i opłatę użycia; jawne zero oznacza bezpłatność danej czynności.
  Quote przed pierwszą publikacją wyznacza cenę w systemowych widełkach. Korekta
  wyglądu ani awans autora jej później nie przeliczają. Odrzucać błędne kwoty.
- Wynik wynika z zapisanego stanu celu, plików i progresu, nie narracji autora.
  Nie dublować incydentów; rozliczenia użycia dopina 148.
- Inwentaryzacja i dry-run legacy: zachować ID, instalacje i XMappera. Nie losować
  na nowo parametrów kupionych aplikacji. Niejednoznaczne kontrakty zgłaszać do
  przeglądu. Nowe produkty nie mogą omijać policy starym payloadem.
- Nie zmieniać reguł GhostLaba przy okazji przebudowy kreatorów.

## Bramka i PASS

Obowiązuje [zero ciężkiego profilu](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Projekty w osobnym magazynie, nie `profile.files.projects`; generator, quote,
publikacja i błędy korzystają z małych projekcji. Naruszenia naprawiać od razu.

Testy: granice 30/39/40/41 i progu effect (roboczo 99/100/101), obie gałęzie
losowania, sufit, brak automatycznego maksimum i rerollu przy retry/edycji,
podrobiony poziom/moc/efekt, niedozwolone kombinacje, rzeczywisty cały pasek,
regresja XMappera, blokada logiki/cen po publikacji i zachowanie kupionych wersji.
Rozkład testować kontrolowanym źródłem losowym, nie przypadkowym trafieniem.

Dostarczyć config, katalog, kontrakt wersji, raport migracji i runbook rollback.
Aktywację nowego UX oraz płatnych opcji skoordynować z 148.

## Stan prac 1 X 2026

Dodano `creator_policy.py`, `creator_store.py` i `creator_routes.py`: katalog recept,
progi mocy, losowanie raz na ID żądania, walidację effect, osobny zapis projektów,
niezmienne wydania i edycję prezentacyjną z kontrolą rewizji. Lista projektów ma
małą projekcję i strony po 100 pozycji. API nowej ścieżki jest za wyłączoną domyślnie
flagą `CHAOS_CREATORS_V2_ENABLED`; nie włączać jej przed domknięciem runtime.

Naprawione znalezione ciężkie zależności: jakość legacy generatora czyta małe
projekcje i wallet, publikacja/wycofanie nie zapisują `profile.files`, bootstrap
kluczy kreatora i katalog projektów FM mają osobne endpointy. Katalog nakłada
kanoniczne publikacje kreatorów na legacy, zachowując ID istniejących aplikacji.

Weryfikacja: 9 nowych testów backendu (policy/store/requesty, zero-heavy,
współbieżny retry, wersje, zapis pełnego wyłączenia zabezpieczeń do target store),
istniejący test JS kontraktu kreatora oraz kontrola składni JS przeszły.
Przypadkowe szersze uruchomienie importowanych klas ujawniło osobny FAIL fixture
`test_security_migration_idempotent_missing_fails_closed` (seedowane konta w raporcie
migracji); nie należy uznawać całego starszego zestawu za zielony.

Kontynuacja: efekt zainstalowanego kontraktu jest podłączony do `/gonna-win`,
z walidacją celu i indeksu opcji przed mutacją. Dodano ścisłą walidację prezentacji,
quote (puste = cena systemowa, jawne 0 = gratis), konfigurację cen i efektów opcji
przed pierwszą publikacją oraz ich blokadę po publikacji. Konfiguracja nie losuje
ponownie mocy. Narzędzie `creator_migration.py` ma operatorski dry-run i import
snapshotów historycznych publikacji z kontrolą powtórzeń. Zachowuje ceny, ID
i efekty; nie migruje jeszcze legacy projektów do nowego edytora.

Przeszło 18 nowych testów i 3 wybrane regresje starego runtime. Test requestu
potwierdza zapis pełnego paska i kropki exploit, z pozostałymi akcjami nieaktywnymi;
izoluje stary loader i nie potwierdza zero-heavy pełnego przejęcia ani XMappera.
Dodano [runbook](../runbooks/sprint_147_creators.md) z migracją, rollbackiem i odbiorem.

Otwarte w 147: ciężkie zależności przejęcia/progresji/właściciela i workerów,
pozostałe executory z plikami, rzeczywista regresja XMappera, pełna migracja projektów
i odbiór zakupów. Te prace nie są przeniesione do długu ani objęte PASS.
Materiały szkoleniowe i końcowa ścieżka edytora/aktualizacji wymagają koordynacji z 148.
