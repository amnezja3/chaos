# Dokumentacja CHAOS

Dokumentacja jest pogrupowana według roli. Aktualny kod i testy pozostają
nadrzędne wobec historycznych planów oraz wpisów journalu.

## Gdzie zacząć

- [Panel administracyjny — layout i odczyty na żądanie](runbooks/admin_panel_lazy_layout.md):
  cztery sekcje, paginacja, pojedyncze konto i zasoby z kanonicznych store’ów.

1. [`Pełne przekazanie projektu — 2026-09-14`](runbooks/handoff_project_2026_09_14.md) — aktualny punkt startowy: architektura, decyzje, stan prac, produkcja i ryzyka.
2. [`overview/ABOUT_CHAOS.md`](overview/ABOUT_CHAOS.md) — produkt, świat i canon.
3. [`history/project_journal.md`](history/project_journal.md) — najnowszy stan prac.
4. [`architecture/profile_hot_path_contract_130_11_plus.md`](architecture/profile_hot_path_contract_130_11_plus.md) — wiążąca bramka wydajności i integralności.
5. [`history/game_play_180726.md`](history/game_play_180726.md) — chronologia wcześniejszych sprintów.

Do audytu wydajności przeczytaj również
[`mapę ciężkich i lekkich ścieżek`](runbooks/handoff_hotpaths_2026_09_14.md).
[`Przekazanie 139–140 z 10 września`](runbooks/handoff_sprints_139_140.md)
jest historyczne: jego polecenie rozpoczęcia Sprintu 139 nie jest aktualne.

## Struktura

- [`overview/`](overview/) — opis projektu, nazwa i canon klanów.
- [`gameplay/`](gameplay/) — kontrakty pętli gry, mapy, operacji, zasobów i ekonomii.
- [`architecture/`](architecture/) — przekrojowe kontrakty runtime, persistence, delt, sesji i profilu.
- [`systems/ghostnetwork/`](systems/ghostnetwork/) — architektura GhostNetwork.
- [`systems/blacknet/`](systems/blacknet/) — BlackNet, read modele, fakty, CTA i outbox.
- [`systems/cyberner/`](systems/cyberner/) — Cyberner i kanały radiowe.
- [`systems/audio-feedback/`](systems/audio-feedback/) — OFS, SFX i audio.
- [`systems/incidents-npc/`](systems/incidents-npc/) — gameplay i architektura NPC incidents.
- [`sprints/`](sprints/) — artefakty realizacji i zamknięcia sprintów.
- [`audits/`](audits/) — audyty, post-audyty i raporty diagnostyczne.
- [`hardbugfix/`](hardbugfix/) — przyczyny regresji, naprawy i kontrakty chroniące przed ich powrotem.
- [`runbooks/`](runbooks/) — instrukcje operatorskie i migracyjne.
- [`incidents/`](incidents/) — raporty incydentów.
- [`plans/`](plans/) — plany i propozycje przyszłych zmian.
- [`history/`](history/) — journale oraz historyczne roadmapy.

## Status bieżący

- [Audyt konsekwencji służb — 16 IX](audits/response_consequences_2026_09_16.md):
  szkielet MVP istnieje, ale wymaga naprawy kwalifikacji, źródeł danych i commitów.
  [Sprint 142](sprints/sprint_142_response_consequences_mvp.md) — pełna ścieżka
  scan → kamery → wygaszanie/inicjacja → eskalacja → media/BlackNet → konsekwencje MVP;
  [Sprint 143](sprints/sprint_143_response_consequences_expansion.md) — tabela kar,
  recydywa, ograniczenia systemowe/ruchu/teleportów i więzienia. Wylogowanie nie
  usuwa incydentów ani automatycznie nie odbywa kary.
  [142.1 — kontrakt kamer](runbooks/sprint_142_1_camera_contract.md): implementacja
  i testy lokalne zapisane; PASS gameplayu cofnięty przez autora 17 IX 2026.
  142.1 ponownie otwarty, przejście do 142.2 wstrzymane. 143 pozostaje zaplanowany.

- [Terminal: pakiety Googleplex](gameplay/terminal_packages.md) — `pkg list-all`,
  `pkg search <nazwa>` i `pkg install <nazwa lub ID>` przez istniejący instalator.

- [`Sprint 141 — Control Loop: hakowanie gracza end to end`](sprints/sprint_141_player_hacking_end_to_end.md)
  ma rozpisany zakres na polecenie autora: wykrycie i wybór intruza, przełamanie
  zabezpieczeń, dostęp, kwalifikacja i wykonanie narzędzi, efekty oraz pełny
  interfejs desktop/mobile. Status W REALIZACJI: lokalny pakiet Player Access /
  Log Reader ma testy PASS; pozostałe naprawy i odbiór całej ścieżki otwarte.
  [Raport audytu 15 IX](audits/sprint_141_player_hacking_audit_2026_09_15.md)
  dokumentuje reprodukcje wyjątków narzędzi, stare źródła pozycji i luki bramek.
  Od 15 IX obejmuje także osobny etap naprawy starej pozycji aktora po
  teleportacji; audyt potwierdził stare źródła współrzędnych, wpływ ciężkiego
  profilu na czas produkcyjny pozostaje do pomiaru.
  Pakiet 141.2 usuwa pełne profile ze snapshotu aktorów i dodaje ochronę
  kolejności pozycji. Przed jego uruchomieniem wymagane jest
  [jawne uzupełnienie projekcji awatarów](runbooks/sprint_141_2_map_actor_projection.md).
  141.2 zamknięty po migracji operatora i odbiorze mapy/alarmu przez autora.
  141.3 zamknięty: [security i Picker/capture](runbooks/sprint_141_3_player_target_selection.md)
  oraz [launcher PvP](runbooks/sprint_141_3_launcher_runtime.md) mają odbiór autora.
  Migracja launchera na serwerze: 31/31, verify READY również po uruchomieniu
  czterech procesów; cztery punkty smoke PASS. Runbooki zachowują procedury
  referencyjne, nie są poleceniem ponownej migracji.

- Sprinty 139–140 i [`stylizacja .1–.10`](sprints/sprint_140_stylization_1_plus.md)
  są zrealizowane. Autor potwierdził końcowy przebieg show 13 września.
  Zachowujemy zaakceptowaną oprawę wraz z
  [kontraktem layoutu, responsywności i assetów](sprints/140_stylization_layout_responsive_asset_contract.md):
  wspólna oprawa CSS, reflow desktop/portrait i reuse zasobów CHAOS.
  Nie należy ponownie rozpoczynać planu stylizacji ani automatycznie wykonywać triggera.

- Sprint 138.2 zakończył pełny producer-backed production E2E wynikiem `PASS`.
  Zrealizowane późniejsze etapy opisują
  [`Sprint 139 — natychmiastowy show i restart`](sprints/sprint_139_ghostsignal_activation_restart.md)
  oraz
  [`Sprint 140 — 15-minutowy finał`](sprints/sprint_140_ghostsignal_15_minute_finale.md).
  Aktualny stan i rozróżnienie odbioru wizualnego od formalnego postflight zawiera
  [`nowe przekazanie`](runbooks/handoff_project_2026_09_14.md).

- Po show naprawiono odczyt wygasłych publicznych publikacji w archiwum oraz
  logowanie z istniejącą sesją po restarcie. Autor potwierdził poprawki.
  Brak nowych publikacji po triggerze pozostaje osobnym otwartym punktem
  diagnostyki workerów/env; historyczne wpisy nie dowodzą działania producerów dziś.
- Signal Registry ma zaakceptowany układ i oprawę. Ostatnia implementacja
  (`96dec35`) przenosi listę/statusy bug reportów do admina i dodaje pełny dump TXT;
  testy PASS, brak osobnego potwierdzenia ręcznego odbioru panelu.
- Następny kierunek to **Control Loop**, czyli sprinty poprawkowe gameplayu.
  Pierwszy zakres autor określił jako pełną naprawę hakowania obcego gracza;
  opisuje go Sprint 141 powyżej. Przekazania z 14 IX zachowują stan sprzed
  otrzymania tego polecenia.

- Sprinty 130.10-130.12 oraz GhostNetwork Suite 131-135 są zamknięte albo
  przekazane do potwierdzonej walidacji zgodnie z journalem.
- Audit integracji Ollamy jest zapisany w
  [`sprints/sprint_135_1_ollama_outbox_integration_audit.md`](sprints/sprint_135_1_ollama_outbox_integration_audit.md).
  Przywraca formalnie zamrożony Sprint 84 oraz świadomie odłożony BlackNet AI
  Ecosystem (Sprint 21+), wyznacza jeden canonical outbox oraz roadmap 135.2+.
  Historyczne statusy pośrednie czytaj wraz z późniejszymi wpisami journalu
  i wynikiem 138.2, nie jako bieżący backlog.
- Osobne kontrakty realizacyjne:
  [`135.2 — canonical task transport`](sprints/sprint_135_2_canonical_llm_task_transport.md),
  [`135.3 — event producers i Googleplex ingress`](sprints/sprint_135_3_llm_event_producers_googleplex_ingress.md),
  [`135.4 — Ollama worker i canonical Inbox`](sprints/sprint_135_4_ollama_worker_canonical_inbox.md),
  [`135.4.1 — Googleplex Home i News foundation`](sprints/sprint_135_4_1_googleplex_home_news_foundation.md),
  [`135.4.1.1 — Googleplex Search Presentation Repair`](sprints/sprint_135_4_1_1_googleplex_search_presentation_repair.md),
  [`135.4.2 — kupowane narzędzie Googleplex`](sprints/sprint_135_4_2_googleplex_purchasable_llm_tool.md),
  [`135.5 — publishery BlackNet/Googleplex News/Cyberner`](sprints/sprint_135_5_llm_publishers_blacknet_googleplex_cyberner.md),
  [`135.5.2 — signal-aware narrative quality`](sprints/sprint_135_5_2_signal_aware_narrative_quality.md),
  [`135.6 — hardening i controlled cutover`](sprints/sprint_135_6_narrative_hardening_cutover.md),
  [`136 — GhostNetwork Domain Narrative Bridge`](sprints/sprint_136_ghostnetwork_domain_narrative_bridge.md),
  [`137 — GhostNetwork Narrative Generation and Validation`](sprints/sprint_137_ghostnetwork_narrative_generation_validation.md),
  [`138 — GhostNetwork Narrative Publication Lifecycle`](sprints/sprint_138_ghostnetwork_narrative_publication_lifecycle.md).
- Sprint 135.2 rozszerza SQLite `ghost_narrative_outbox` do jednej kolejki z
  canonical dedupe, claim/lease/CAS, retry/dead-letter i crash recovery. Legacy
  BlackNet JSON jest tylko eksportem diagnostycznym. Ollama, Inbox, producenci
  i publikacja zostały rozwinięte w późniejszych etapach wymienionych powyżej.
- Recovery Trollu2 jest zakończone i nie jest aktywnym backlogiem.

Przenosząc lub dodając dokument, należy zaktualizować ten indeks i wszystkie
wersjonowane referencje. Nie należy tworzyć ponownie płaskich plików w katalogu
głównym `doc/` poza tym indeksem.
