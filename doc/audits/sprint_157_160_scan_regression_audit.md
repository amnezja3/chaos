# Audyt regresji skanowania 157–160 — 2026-10-19

## Wniosek

Odtworzono błąd transportu 160 i poprawiono go. Nie ma podstaw do deklaracji,
że wszystkie problemy są wyłącznie awarią dostawców. Jednocześnie ten błąd
nie tłumaczy raportowanych HTTP 502/504 ani timeoutów przed odpowiedzią.
Do zamknięcia audytu produkcji potrzebny jest odczyt flag, circuit i leases VPS.
Nie włączono dostawców, nie zmieniono polityk ani limitów gameplayu.

## Historia i porównanie

Porównano f0782b3 (156), ea86abc (157.8), a6ff305 (158), ce6cd74 (159) i stan
po e819de8 (160). AST `_build_query` w każdym przypadku ma identyczny SHA-256
z prefiksem `4a90d173602bc3d0`. Nie zmieniono nwr, filtrów ani out center.
Domyślne 8 s odczytu, QL timeout 15 s i endpoint_limit=2 istniały już w 156.
Filtry w run.py pozostały shop/amenity/office/healthcare/atm=yes/man_made=surveillance.

157: brak zmian w poiFetchClass.py. Wyłączenie ip-api dotyczy wyboru miasta przy
starcie, nie Overpass. Ochrona komunikacji nie obejmuje map_action. Bramka wieku
może zatrzymać żądanie przy aktywnej fladze, ale przy wartości 0 zwraca bez blokady.
Nie sprawdzono obecnej flagi na VPS w tym audycie.

158: pojawił się transport w procesie potomnym, connect timeout 3 s, wspólny cache,
slot, single-flight i circuit breaker. Ścieżka legacy przy fladze infrastruktury 0
pozostała. Przekazane wcześniej logi pokazywały api_error także przy infrastructure=false.

159: prezentacja MASA nie zmienia zapytania. Frontend odmawia ponownego skanu,
gdy żądanie jest pending albo trwa cooldown otrzymany z backendu. W normalnej
ścieżce finally wywołuje finish; upływ cooldownu jest lokalny i cichy.
To przegląd kodu UI, nie nowy test przeglądarkowy.

160: secure transport dotyczy probe/diagnostyki oraz gameplayu z registry=1.
Przy registry=0 infrastruktura używa requests, bez nowego secure transport.
World i wide wymagają własnych flag. Dodanie kandydata do panelu nie dodaje go
automatycznie do legacy listy. Domyślny limit dwóch endpointów wybiera DE i LZ4
tego samego operatora; to nie jest fallback do dwóch niezależnych dostawców.

## Potwierdzony błąd: zamknięcie odpowiedzi HTTP 200

secure_transport po response.read() wykonywał kolejną iterację i settimeout()
na TLS socket. Gdy odczyt Content-Length domknął HTTPResponse przy Connection:
close (również domyślne HTTP/1.0), odłączone od connection gniazdo mogło być już
zamknięte. Poprawny i kompletny JSON był odrzucany jako http_read_failed.

Nowy test na prawdziwym lokalnym serwerze odtworzył WinError 10038 przed poprawką.
Po poprawce pętla kończy odczyt, gdy HTTPResponse jest zamknięte; limit rozmiaru
i parsowanie JSON pozostają obowiązkowe. Testy krótkiej i >1024-bajtowej odpowiedzi
przeszły. Test używa plaintext loopback zamiast TLS wyłącznie w fixture; nie jest
to test certyfikatów VPS. Porównano rzeczywiste body formularza, Host,
Content-Length, Content-Type i ścieżkę z requests — są zgodne.

Nie jest to wyjaśnienie 502/504: błąd występował dopiero przy odczycie HTTP 200.
Nie wpływa na ścieżkę gameplayu z registry=0. Wcześniejsze mocki socketów nie
odtwarzały cyklu zamknięcia prawdziwego gniazda.

## Warunki blokujące lokalnie

| Mechanizm | Skutek | Jak rozpoznać |
| --- | --- | --- |
| registry=1, brak enabled/tested_ok/normal_scan/ważnej decyzji | Brak HTTP, ewentualnie stale cache | provider_configuration_unavailable |
| Circuit po co najmniej 3 błędach | Wspólna blokada operatora; automatyczny backoff do 120 s, Retry-After może wydłużyć | circuit_open, until_at |
| Wspólny slot zajęty | Inny skan nie wysyła HTTP, może użyć stale | upstream_busy, @upstream |
| Ten sam query lease | Join do 2 s, potem stale/błąd | join_timeout |
| Cache pełny, błąd SQLite lub utrata lease | Możliwe odrzucenie nawet poprawnego pobrania | cache_capacity_or_lease_lost / storage_unavailable |
| Wide bez wymaganych flag | Brak pobrania | wide_fetch_dependencies |

Admin probe i controlled_scan współdzielą slot i circuit z grą. Ich nieudane
wywołania mogą czasowo zablokować tego samego operatora również w gameplayu.
Ich limit 15 minut jest jednak oddzielnym ograniczeniem diagnostyki, nie stałą
15-minutową blokadą każdego skanu gry. Lease wygasają; zwykły restart nie czyści
bazy. Nie kasować blokad ani bazy w ciemno.

## Dowody i następny krok

Przed poprawką uruchomiono 81 testów test_poi*.py: PASS w 35,485 s; nie obejmowały
nowego testu zamknięcia gniazda. Po poprawce: 2 testy wire contract + 9 secure
transport PASS. Dodatkowy test raportu runtime sprawdza filtrowanie sekretów
i zachowanie konfiguracji providerów.

Na VPS, bez restartu i bez publicznych zapytań:

```bash
git pull --ff-only
.venv/bin/python tools/poi_runtime_audit.py
```

Raport odczytuje tylko dozwolone ustawienia PM2 i bazę POI w mode=ro/query_only.
Nie wypisuje sekretów, pozycji graczy ani raw payloadów. Nie dowodzi wartości
już zainicjalizowanego fetchera w pamięci workerów; pokazuje konfigurację PM2
i aktualny stan bazy. Po odczycie wybieramy konkretną korektę, a nie aktywację
wszystkich flag. Do zastosowania poprawki w web potrzebny będzie osobny restart.
