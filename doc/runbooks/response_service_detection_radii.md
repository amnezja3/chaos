# Promienie patrolowania i wykrywania służb — 24 IX 2026

Konfiguracja: `config.py`, `RESPONSE_SERVICE_PATROL_RADIUS_M`.

| Służba | Rodzina runtime | Promień patrolowania wokół incydentu |
|---|---|---:|
| Policja | police | 300 m |
| Cybersecurity | cyberpolice | 2 000 m |
| Secret services | secretservice | 39 000 m |

Powyższe wartości dotyczą `patrol_radius_m`, nie radaru pojazdu.
Radar `detection_radius_m` ponownie korzysta z wcześniejszej formuły:
`max(55, min(180, 65 + poziom_incydentu * 18 + poziom_służby * 8))` metrów.
Mapa i backend korzystają z promienia zapisanego w kapsule. Stare kapsuły
z radarem przekraczającym 180 m nie kwalifikują graczy do nowych kar przed
przeliczeniem (`capsule_recalibration_required`).

Po wdrożeniu zrestartować web oraz territory worker i odświeżyć mapę.
Snapshot kapsuł aktualizuje istniejące aktywne patrole ze starym promieniem,
bez resetowania identyfikatora, seeda trajektorii, spawnu i czasu życia.
Pozycja patrolu zmieni się zgodnie z nowym promieniem ruchu.
Nowe patrole od początku otrzymują wartości z konfiguracji.

Wykrycie nadal podlega kwalifikacji obecności online i jednemu trwałemu
rzutowi na gracza–incydent. Korekta promienia nie resetuje dawnych rzutów ani wyroków.
Przypadkowi gracze pozostają kwalifikowani jako bystanders.

Regresje obejmują trzy promienie patrolowania, limit radaru, odrzucenie
starych błędnych promieni i aktualizację kapsuł bez odnowienia czasu życia.
Dane serwera nie były modyfikowane.
