# Camera Street View 166.1 — branding i przygotowanie odbioru nowej kamery

Aktualizacja po odbiorze operatora 01.11: kod a36513a pobrany na VPS. Skan nowego
celu blokowany przez MapLark provider_response_incomplete (4 próby 11:46 UTC,
revision 9). Szczegółowy powód partial nie został utrwalony w starych logach.
Lokalna diagnostyka poi_maplark_incomplete przygotowana, 11 testów PASS;
nie zmieniono warunków przyjmowania danych ani limitów. Brak nowego materiału
Mapillary i brak PASS pełnego 166.1. Szczegóły w journalu z tej daty.

2026-11-01, baza HEAD 56d5af0. Zmiany lokalne, bez commit/push/deploy.
**Branding LOCAL PASS; checkpoint 166.1 W TOKU — brak nowego dowodu VPS.**

## Zakres

Najpierw zaktualizowano istniejące sprinty 164, 165 i 166. Zachowano PASS main,
30 minut i wyglądu pilota. Global OFF i dotychczasowa konfiguracja VPS bez zmian.
Nie rozwijano nowego prototypu ani architektury; wzorzec accepted_164_0 nietknięty.

Oficjalne oryginalne logo pochodzi z
[mapillary/api-demo](https://github.com/mapillary/api-demo/blob/bbf4f29395116b5c019af87bd3e5c836487cedda/logo_green.svg).
Plik w static/images/providers/mapillary, oryginalne bajty/kolor/proporcje,
MIT repo dostawcy w sąsiednim LICENSE. Porównano z archiwalnym mapillary_press,
który deklaruje dla znaków CC BY-ND 4.0. Szczegóły i SHA256 w
[metryce zasobu](../../static/images/providers/mapillary/README.md).
Nie uznajemy licencji repo za pełną zgodę znakową. Strona terms zwracała bramkę
logowania; **L02 nadal OPEN**, bez deklaracji prawnego zatwierdzenia.

Renderer: znak i etykieta dostawcy w lewym górnym rogu poza transformacją/FX,
oficjalny znak także w istniejącym panelu. Dane autora, ID, licencji, źródła,
modyfikacji i archiwalnej symulacji pozostają oparte na material. Fixture AI
nie otrzymuje brandingu Mapillary. Zastąpiono dawny dialog potwierdzenia
prawdziwymi anchorami _blank/noopener/noreferrer. Ramka/kropka/typewriter dotyczą
komunikatu, nie logo. Touch pierwszy tap informuje, drugi otwiera; klawiatura
otwiera bez dodatkowej blokady, reduced-motion wyłącza animacje.

Powrót z karty dostawcy zachowuje DOM okna; ukrycie zawiesza prezentację i zwalnia
lease, bez consumed. Przed odnowieniem klient czeka na zakończenie release.
Zamknięcie przez gracza nadal korzysta z dotychczasowej trwałej ścieżki.

Przygotowanie nowej kamery ujawniło zależność od global ON w bramce targetów.
Teraz accepts_target bierze użytkownika i respektuje istniejące enabled:
main/pilot może używać kanonicznego celu poza Paryżem przy global OFF. Nadal
wymagany jest aktualny skan, tożsamość, zasięg i zgodna aplikacja. Nowa kamera
zawsze wymaga materiału; nie dostaje fikcyjnego obrazu przy source OFF.
Nie zmieniono timera, mocy, wyniku hakowania, rezerwacji OFC/pickera,
aktywatora ani camera_off/incydentów. Brak nowych odczytów pełnych profili.

## Dowody lokalne

- Playwright MCP na prawdziwym Flask /desktop i istniejącej izolowanej bazie:
  21 kontroli PASS (desktop hover/focus/Enter/mysz, target/rel/opener, atrybucja,
  zachowana instancja/grant/operation po ukryciu, maximize, reduced motion,
  mobile 390×844 z hasTouch, pierwszy/drugi tap, brak overflow).
- Spóźniony materiał: PASS, ten sam DOM, atrybucja i fokus linku.
- Metadane Mapillary i odpowiedź strony zewnętrznej były kontrolowane przez
  routing testowy. Auth, grant i media używały lokalnego backendu. To nie jest
  dowód realnego API, nowego pobrania ani zainstalowanej PWA.
- Zrzuty desktop/mobile obejrzane; poprawiono poziomy overflow ostrzeżenia na
  telefonie. Log konsoli głównej strony: komunikaty informacyjne APP_FLOW,
  bez błędów JS. Nie powtarzano paryskiego testu produkcyjnego.
- Gameplay: 25 testów PASS po dodaniu przypadku global OFF / pilot / skan.
  Ostatnia korekta rewalidacji legacy celu objęta dodatkową regresją celowaną.
- Końcowa regresja celowana: 25 testów PASS (2 przypadki skanu/bramki,
  20 camera_shutdown_contract i 3 camera_incident_audit). Składnia JS oraz
  git diff --check PASS. Read-only CLI uruchomiony na starym backupie oraz
  izolowanej bazie z aktualnym schematem; nie wykonywał zapisu ani API.

[Desktop](../../artifacts/camera-branding-166-1-desktop.png),
[mobile](../../artifacts/camera-branding-166-1-mobile.png).

## Kandydat rzeczywistego celu i granice dowodu

Odczyt tylko response_camera_observations z lokalnego backupu
game-prod-20261031T065150Z.sqlite3:

| Pole | Wartość |
| --- | --- |
| camera_id | camera_0014ac41c138c389e40fa5cf |
| rodzic | 5001825490 |
| etykieta / typ | Kamera sklepu / camera |
| lat:lon | 48.85294369549624:2.3349836995089666 |
| zapisany scan_id | scan_1bcb820caa8119a4f2ff584b |
| klucz Mapillary | 12c619fd3eb6b3c90c87afaf36bf1380916ddffe23e7ce974af84dd0a547de6e |

Cel leży około 1,3 km od pilota. Obserwacja w backupie wygasła; backup poprzedza
schemat archiwum. To potwierdza historyczną tożsamość, nie aktualny cel VPS ani
brak materiału. Nie tworzono żadnego celu w produkcji. Nowy read-only CLI
tools/camera_checkpoint_166.py zbiera ograniczony baseline/post, checksum,
budżet i heartbeat bez API, enqueue, importu run.py czy zapisu gameplayu.

Brak dostępu do aktywnego terminala VPS/produkcji w tej sesji: automatyczne
pozyskanie, nowe WebP/checksum, realny download i podgląd tej kamery NIEPRZETESTOWANE.
Nie deklarować pełnego 166.1 PASS na podstawie lokalnych fixture.

Istniejący workflow kolejkuje materiał po zatwierdzonym sukcesie, równolegle
do pobierania aktywatora. Nie utworzono osobnego żądania przed hackiem ani nie
uruchomiono work-once. To istotne doprecyzowanie kolejności diagramu odbioru.

## Gotowość wdrożenia

Brak migracji/zależności/nowych sekretów. Standardowy Git po decyzji operatora;
restart web i operations zachowujący obecne env, bez przeładowania konfiguracji
archive. [Jedna procedura VPS i zbierania dowodów](../runbooks/camera_street_view_system_s1_s3.md).
Następny krok: wdrożenie tego zakresu, świeży skan wybranego celu, baseline
braku archiwum/reuse, normalny hack i obserwacja automatycznego workera.
166.2–166.5 oraz globalna aktywacja pozostają poza bieżącym poleceniem.
