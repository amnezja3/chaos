# CHAOS — World Objects

Ten dokument opisuje obiekty świata gry w Sprint 0.2.

`target_type` opisuje, czym obiekt jest w gameplayu.

`source_type` opisuje, skąd obiekt pochodzi technicznie lub jak został rozpoznany.

Szczegółowe mapowanie `source_type -> target_type` znajduje się w `doc/gameplay/source_type_mapping.md`.

---

## Kategorie obiektów

| target_type | category | source_types | movement_model | can_be_captured | can_be_traced | produces_data | has_security | supported_map_actions | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `camera` | static | `camera` | none | yes | no | yes | yes | `camera_stream`, `camera_shutdown`, `scan_ports`, `exploit` | Cyfrowe oczy świata. Może dawać stream albo dump zależnie od aplikacji. |
| `atm` | static | `atm` | none | yes | no | yes | yes | `atm_logs`, `install_sniffer`, `scan_ports`, `exploit` | Źródło danych finansowych i ryzyka alarmu. |
| `router` | static | `mock_router` | none | yes | no | yes | yes | `scan_ports`, `install_sniffer`, `sniff`, `exploit` | Realny cel w pierwszych sprintach na mockowej wersji. Docelowe źródła mapy do dopisania. |
| `server` | static | `mock_server` | none | yes | no | yes | yes | `scan_ports`, `install_sniffer`, `sniff`, `exploit` | Realny cel w pierwszych sprintach na mockowej wersji. Docelowe źródła mapy do dopisania. |
| `venue` | group | `shop`, `restaurant`, `bar`, `cafe`, `fast_food` | none | optional | no | yes | optional | `scan_hotspots`, `audio_hack`, `scan_ports` | Grupa menu i wspólna kategoria UX. Konkretne typy lokacji są rozbite niżej. |
| `shop` | static | `shop` | none | optional | no | yes | optional | `scan_hotspots`, `audio_hack`, `scan_ports`, `exploit`, `sniff` | Sklep lub punkt usługowy. |
| `restaurant` | static | `restaurant` | none | optional | no | yes | optional | `scan_hotspots`, `audio_hack`, `scan_ports` | Restauracja jako lokacja z hotspotami i audio. |
| `bar` | static | `bar` | none | optional | no | yes | optional | `scan_hotspots`, `audio_hack`, `scan_ports` | Bar jako lokacja z rozmowami, hotspotami i audio. |
| `cafe` | static | `cafe` | none | optional | no | yes | optional | `scan_hotspots`, `audio_hack`, `scan_ports` | Kawiarnia jako lokacja z hotspotami i audio. |
| `fast_food` | static | `fast_food` | none | optional | no | yes | optional | `scan_hotspots`, `audio_hack`, `scan_ports` | Lokal fast food jako lokacja z ruchem klientów. |
| `person` | semi_mobile | `person` | local_walk | no | yes | yes | optional | `trace_device`, `mic_sniff`, `trace` | Klient, pracownik, ochroniarz lub inna osoba świata. |
| `phone` | semi_mobile | TODO_DECISION | carrier_movement | no | yes | yes | yes | `trace_device`, `trace`, `sniff` | Rozwijany target_type. Nie blokujemy go na tym etapie. |
| `vehicle_source` | static | `parking` | none | no | no | optional | optional | `scan_ports`, `trace` | Źródło potencjalnych pojazdów. Nie jest pojazdem samym w sobie. |
| `vehicle` | mobile | `car` | road_movement | optional | yes | yes | yes | `trace_gps`, `car_hack`, `trace` | Pojazdy, kurierzy, taksówki, samochody firmowe. |
| `player` | mobile | `player` | player_position | no | yes | yes | yes | `scan_ports`, `exploit`, `sniff`, `trace` | Gracz widoczny na mapie. Ma osobne zasady player target. |
| `poi` | static | `manual`, `generated` | none | optional | optional | optional | optional | `scan_ports`, `exploit`, `sniff`, `trace` | Ogólny punkt mapy, gdy typ nie jest jeszcze doprecyzowany. |
| `pillar` | static | `conflict_pillar` | none | yes | no | optional | yes | `scan_ports`, `exploit`, `sniff`, `trace` | Filar konfliktu terytorium. |

---

## Zasady

* `target_type` może rozwijać się w kolejnych sprintach.
* Nowy `source_type` powinien dostać wpis w `doc/gameplay/source_type_mapping.md`.
* Menu mapy powinno docelowo wynikać z `target_type`, `target_mode` i `map_actions`, a nie z samej nazwy obiektu.
* Obiekty statyczne są podstawą terytoriów.
* Obiekty mobilne i półmobilne mogą produkować dane oraz generować aktywne operacje, ale nie muszą być filarami terytorium.

---

## TODO_DECISION

* Jakie realne, niemockowe `source_type` mapujemy docelowo na `router` i `server`.
* Czy `phone` będzie wykrywany jako osobny obiekt mapy, czy jako zasób powiązany z `person` lub `player`.
* Czy `vehicle_source` ma później generować konkretne obiekty `vehicle`, czy tylko zwiększać szansę znalezienia pojazdu przy skanie.
