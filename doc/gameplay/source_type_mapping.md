# CHAOS — Source Type Mapping

Ten dokument opisuje mapowanie `source_type -> target_type`.

`source_type` mówi, skąd pochodzi obiekt mapy albo jak został rozpoznany technicznie.

`target_type` mówi, czym obiekt jest w gameplayu.

Lista rozwija się rozwojowo. Nie zamykamy jej na sztywno, ale każdy nowy `source_type` powinien zostać dopisany do tej tabeli.

## Tabela mapowania

| source_type | target_type | confidence | notes | menu_group | supported_map_actions |
| --- | --- | --- | --- | --- | --- |
| `camera` | `camera` | high | Kamera monitoringu, kamera sklepowa albo wygenerowany punkt obserwacji. | camera | `camera_stream`, `camera_shutdown`, `scan_ports`, `exploit` |
| `person` | `person` | high | Osoba, klient, pracownik, ochroniarz lub inny półmobilny aktor świata. | person | `trace_device`, `mic_sniff`, `trace` |
| `atm` | `atm` | high | Bankomat lub terminal finansowy. | atm | `atm_logs`, `install_sniffer`, `scan_ports`, `exploit` |
| `mock_router` | `router` | high | Mockowy router używany w pierwszych sprintach gameplayu. | generic | `scan_ports`, `install_sniffer`, `sniff`, `exploit` |
| `mock_server` | `server` | high | Mockowy serwer używany w pierwszych sprintach gameplayu. | generic | `scan_ports`, `install_sniffer`, `sniff`, `exploit` |
| `car` | `vehicle` | high | Samochód, pojazd firmowy albo cel mobilny z elektroniką pojazdu. | vehicle | `car_hack`, `trace_gps`, `trace` |
| `parking` | `vehicle_source` | medium | Parking jest osobnym źródłem potencjalnych pojazdów, a nie pojazdem samym w sobie. | vehicle | `scan_ports`, `trace` |
| `shop` | `shop` | medium | Sklep lub punkt usługowy. | venue | `scan_hotspots`, `audio_hack`, `scan_ports` |
| `restaurant` | `restaurant` | medium | Restauracja jako miejsce z hotspotami, personelem i urządzeniami audio. | venue | `scan_hotspots`, `audio_hack`, `scan_ports` |
| `bar` | `bar` | medium | Bar jako miejsce z hotspotami, rozmowami i urządzeniami audio. | venue | `scan_hotspots`, `audio_hack`, `scan_ports` |
| `cafe` | `cafe` | medium | Kawiarnia jako miejsce z hotspotami, rozmowami i urządzeniami audio. | venue | `scan_hotspots`, `audio_hack`, `scan_ports` |
| `fast_food` | `fast_food` | medium | Lokal fast food jako miejsce z hotspotami i ruchem klientów. | venue | `scan_hotspots`, `audio_hack`, `scan_ports` |
| `manual` | `poi` | low | Ręcznie dodany punkt. Wymaga doprecyzowania przez dane obiektu. | generic | `scan_ports`, `exploit`, `sniff`, `trace` |
| `generated` | `poi` | medium | Obiekt wygenerowany przez system gry. Target type powinien być zapisany jawnie, jeśli generator go zna. | generic | `scan_ports`, `exploit`, `sniff`, `trace` |
| `player` | `player` | high | Widoczny gracz: znajomy, intruz, członek klanu, wróg albo neutralny actor. | player | `scan_ports`, `exploit`, `sniff`, `trace` |
| `vulnerability` | inherited | high | Zgłoszona podatność ma własny `target_mode = vulnerability`, ale dziedziczy `target_type` z obiektu źródłowego. | vulnerability | inherited |
| `conflict_pillar` | `pillar` | high | Filar konfliktu terytorium. Może reprezentować przejęty obiekt gracza. | conflict | `scan_ports`, `exploit`, `sniff`, `trace` |

## Zasady

* `source_type` nie powinien być bezpośrednim routerem gameplayu.
* Backend może używać `source_type` jako heurystyki, ale powinien możliwie szybko wyprowadzić `target_type`.
* Menu mapy powinno docelowo używać `target_type`, `target_mode` i `map_action_id`, a nie nazw obiektów.
* Jeśli obiekt ma `target_type`, to ma pierwszeństwo przed heurystyką z `source_type`.
* Jeśli `source_type` jest `manual` lub `generated`, generator powinien możliwie dopisać jawny `target_type`.

## TODO_DECISION

* Jakie realne `source_type` z OSM lub generatorów mapujemy docelowo na `router`.
* Jakie realne `source_type` z OSM lub generatorów mapujemy docelowo na `server`.
* Czy dla `vehicle_source` tworzymy osobne akcje generowania/wykrywania pojazdów, czy zostaje tylko źródłem skanu.
