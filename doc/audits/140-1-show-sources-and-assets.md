# 140.1 — źródła danych, granice projekcji i assety

Data: 2026-09-11. Audyt lokalnego kodu przed podłączeniem storyboardu.
Kontrakt 139 pozostaje bez zmian. Nie wprowadzamy nowego magazynu świata,
drugiego kontrolera, kolejki ani mechanizmu restartu.

## Audyt 24 źródeł scenariusza

| # | Dane | Istniejące źródło | Zasada projekcji / brak danych |
|---|---|---|---|
| 1 | 20 części | catalog.PARTS | Jawna lista pól, 20 rekordów; brak danych cyklu nie oznacza aktywacji. |
| 2 | Części → maszyny | PARTS.machine_code, MACHINES.part_codes | Dokładnie 4 × 5, bez nowych relacji. |
| 3 | Maszyna → klan | MACHINES.clan_code, CLANS | Cztery publiczne definicje. |
| 4 | Profesje maszyny | PROFESSIONS.machine_code / part_code | Pięć profesji części, nie arbitralnie jedna profesja maszyny. |
| 5 | Supermoce | PARTS.ability_code, ABILITIES | Lista zdolności części; nie deklaruje wykonania efektu. |
| 6 | Lifecycle części | ghost_part_events; list_events_after | Wymaga bounded, zamrożonej projekcji przed rendererem; brak historii → canonical ordering. |
| 7 | Właściciele | lock snapshot, ghost_part_transfer_history | Filtrowanie audience; nie live profile. |
| 8 | Aktywacje | eventy, ghost_contributions / list_cycle_contributions | Zamrożone fakty; nie odtwarzać wymyślonych stanów. |
| 9 | Część → terytorium | lock snapshot.parts / historical nodes | Tylko stan archiwalny; nie zmienione ghost_parts po konsumpcji. |
| 10 | Konflikty | strategic conflicts i territory_conflicts | Oba źródła; 139 wykazał, że tabela strategiczna może być pusta. |
| 11 | Teksty Ollamy | zapisane medium records / publication lineage | Wyłącznie zaakceptowane i audience-safe; żadnego model call. |
| 12 | BlackNet | narrative medium records target_medium blacknet | Zamrożony wybór, brak → pominięcie. |
| 13 | Newsy | medium records target_medium googleplex_news | Ta sama polityka; nie pobierać nowych publikacji w pętli sceny. |
| 14 | Świat przed settlement | immutable lock territory_consumption_plan | Plan obejmuje właściwy zakres finału, nie automatycznie cały świat. Pełna mapa sprzed zmian wymaga projekcji przed skutkami. |
| 15 | Konsumpcja/redukcja | ghost_signal_territory_consumptions | Istniejące receipts; etykiet REDUCED/PRESERVED nie wylicza renderer. |
| 16 | Wynik konfliktu | list_endgame_production_conflicts i lock lineage | Stan końcowy przypisany do cyklu; nie bieżący przypadkowy konflikt. |
| 17 | Nagrody | ghost_reward_ledger, signal_id | Oddzielić nagrody całego cyklu od finału; istniejące kwoty bez przeliczania. |
| 18 | Gracz/statystyki | ranking snapshot / identity snapshot | Publiczna projekcja GhostSignalRankingService.public_snapshot; avatar nie jest jeszcze kontraktem manifestu. |
| 19 | Statystyki klanów | ranking snapshot.clans | Tylko istniejące pola, nie wymyślona aktywność/liczba graczy. |
| 20 | Miara klanu | ranking score_policy i clans | Brak nowej formuły Clan Measure; zgodność z istniejącą miarą do weryfikacji w 140.3. |
| 21 | Ranking | ghost_signal_rankings | W pollu tylko indexed EXISTS, bez parsowania snapshot JSON. |
| 22 | Archiwum | signals, rankings, historical nodes, Signal Registry | Odczyt istniejącej historii; plansza nie tworzy archiwum. |
| 23 | Nowy cykl | GhostNetworkService.rollover_stabilized_cycle | Istniejący settlement → successor → restart epoch → klient boot/ACK. |
| 24 | Wysłanie | GhostTransmissionService._transmit / ghost.signal_sent | Istniejący durable event i sent_at; SFX pozostaje w terminal.js / GameSfx. |

Źródła 6–20 wymagają dopasowania danych do konkretnych scen w 140.2–140.3.
140.1 nie publikuje surowych snapshotów: manifest jawnie zwraca
cycle_history.available=false / scene_projection_pending. To brak podłączonej
projekcji, nie brak historii w bazie. Bez fallbacku do żywego świata/profili.
Nie uznajemy zidentyfikowania tabeli za gotową, bezpieczną projekcję.

## Call flow i budżet 140.1

Istniejący GET /api/ghostnetwork/show → GhostSignalShowService →
projection_for_cycle → odczyt show + get_show_presentation_facts →
build_manifest → istniejący GhostSignalShowController.render / sceneAt.
Gameplay lock, delty, SFX, deadline i restart pozostają własnością 139.

Nowy odczyt to jeden SELECT po signal_id z EXISTS dla canonical dedupe eventu
i rankingu. Nie pobiera signal payload, ranking JSON, geometrii ani profili.
Razem projection_for_cycle: dwa SELECT-y, plus PRAGMAs obu połączeń.
Manifest maksymalnie 32 KiB w teście, 49 scen, 20 części i cztery maszyny.
Koszt nie zależy od wielkości profilu ani signal payload; test obejmuje 35 MB.
Brak nowego schema init, write, model call lub background job w pollu.

Manifest v2 jest publiczny, bez ownerów, nicków, wewnętrznych ID show/sygnału,
sekretów sesji i payloadów. Czytelny fallback jest jedynym rendererem 140.1;
oprawa scen jest zadaniem 140.2–140.4. Invalid/missing manifest wraca do
renderera 139. Brak potwierdzenia sent nie pozwala pokazać sukcesu retrospekcji.
Upływ czasu nie uruchamia restartu; controller nadal oczekuje epoch z backendu.

Data 2108 i dodatkowe fakty settlement/archiwum zostaną podłączone przed
montażem scen, ze stabilnego źródła serwerowego; 140.1 ich nie losuje ani
nie zastępuje fikcyjnymi wartościami. Późniejsza migracja wymaga osobnego planu.

## Asset inventory i kontrakt dla autora

| Identyfikator | Materiał | Status / fallback |
|---|---|---|
| machine_virex_oracle | VIREX ORACLE | Nowy hero asset; fallback pięciu canonical części. |
| machine_echo_libertas | ECHO LIBERTAS | Jak wyżej. |
| machine_phantom_veil | PHANTOM VEIL | Jak wyżej. |
| machine_sentinel_aegis | SENTINEL AEGIS | Jak wyżej. |
| ghostsignal_transmission_video | Film ok. 30 s, w ramce | Nowy; fallback tekstowy, bez triggera/SFX w filmie. |
| ghostnetwork.signal | static/audio/sfx/ghostnetwork/08_signal.mp3 | Istniejący GameSfx, ghost.signal_sent, bez replay. |
| części | static/images/ghostnetwork/parts/ | Istniejące PNG, mapowanie icon_key katalogu. |
| superpowers | static/images/ghostnetwork/superpower/ | Istniejąca oprawa; nie uruchamiać zdolności. |
| mapa | static/js/map/ghostnetwork.js + ghostnetwork_map.css | Istniejąca warstwa; najpierw odseparować renderer od gameplay handlerów. |
| overlay/glitch | static/css/style.css, ghost-signal-show / ofs-fx | Ponowne użycie stylów, bez drugiego engine animacji. |
| terminal/BlackNet | static/js/terminal.js | Ponowne użycie wyglądu; nie otwierać interaktywnych aplikacji. |
| radio | static/js/ghost_radio.js, ghost_radio.css | Istniejący mixer i ustawienia; show nie wymaga radia. |

Autor dostarcza cztery obrazy (preferowane PNG/WebP, opcjonalna przezroczystość)
i film ok. 30 s (preferowane MP4, bez wbudowanego SFX sygnału), wraz z wymiarami,
długością, informacją o audio i źródle/prawach. Dokładne rozmiary i wariant mobile
zatwierdzamy po pomiarze materiałów, nie wymuszamy teraz przypadkowej rozdzielczości.
Nieistniejące pliki mają src=null i available=false; klient nie próbuje ich pobierać.
W 140.1 nie ma preloadu mediów ani nowych żądań assetów.

## Dostarczone materiały — 7a7d03c

W signal_sends/ istnieją machine_virex_oracle, machine_echo_libertas,
machine_phantom_veil, machine_sentinel_aegis jako PNG oraz ich warianty _active.
Odczyt metadanych: podstawowe 1254×1254 RGBA (alpha 0–255), około 1,7–1,9 MB;
aktywne 1672×941 bez alpha, około 2,6–2,9 MB. Wariantów _active nie traktujemy
jako przezroczystych nakładek. Ładowanie scenami i ocena wariantów mobile
pozostają zadaniem montażu; plików źródłowych nie zmieniano.

20 canonical części w parts/ ma 128×128 i alpha 0–255. Mogą służyć jako
przezroczyste elementy sieci, ale nie są materiałami o rozdzielczości hero.
Aktualny pull zawiera osiem nowych maszyn, bez osobnych nowych wersji części.
Film autora w przygotowaniu. Dostępność plików nie oznacza jeszcze ich
podłączenia w runtime: manifest 140.1 zachowuje jawne fallbacki.

## Film dostarczony do 140.2

`static/video/ghostsignal_transmission_video.mp4`: 38,120 s, 7 003 148 B,
H.264 720×480 yuv420p 25 fps oraz AAC; dodatkowy MJPEG to okładka.
Sprawdzono metadane ffprobe i klatkę środkową. Film podłączony w oryginalnym
tempie 07:05–07:43,12, wyciszony. SFX nadal należy do ghost.signal_sent.
Nie modyfikowano źródła ani dołączonej miniatury. Przeglądarkowy odbiór
kompozycji/odtwarzania pozostaje bramką wdrożenia.
