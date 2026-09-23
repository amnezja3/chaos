# Promienie wykrywania służb — 24 IX 2026

Konfiguracja: `config.py`, `RESPONSE_SERVICE_DETECTION_RADIUS_M`.

| Służba | Rodzina runtime | Promień od pojazdu |
|---|---|---:|
| Policja | police | 300 m |
| Cybersecurity | cyberpolice | 2 000 m |
| Secret services | secretservice | 39 000 m |

Zastępuje dawną formułę zależną od poziomu incydentu, ograniczoną do 180 m.
Fabryka zapisuje promień w kapsule NPC. Mapa, walidator i worker wykrywający
graczy online korzystają z tego samego `detection_radius_m`. Obszar ruchu
patrolu i obszar incydentu pozostają odrębnymi parametrami.

Po wdrożeniu zrestartować web oraz territory worker i odświeżyć mapę.
Snapshot kapsuł aktualizuje istniejące aktywne patrole ze starym promieniem,
bez resetowania identyfikatora, trajektorii, spawnu i czasu życia.
Nowe patrole od początku otrzymują wartości z konfiguracji.

Wykrycie nadal podlega kwalifikacji obecności online i jednemu trwałemu
rzutowi na gracza–incydent. Zwiększenie promienia nie resetuje dawnych rzutów.
Przypadkowi gracze pozostają kwalifikowani jako bystanders.

Walidacja: 31 testów kapsuł, kwalifikacji i spotkań, w tym wszystkie trzy
zasięgi, granice odległości, odświeżenie aktywnych patroli oraz skan workera
bez otwartej mapy. Dane serwera nie były modyfikowane.
