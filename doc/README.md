# Dokumentacja CHAOS

Dokumentacja jest pogrupowana według roli. Aktualny kod i testy pozostają
nadrzędne wobec historycznych planów oraz wpisów journalu.

## Gdzie zacząć

1. [`overview/ABOUT_CHAOS.md`](overview/ABOUT_CHAOS.md) — produkt, świat i canon.
2. [`history/project_journal.md`](history/project_journal.md) — najnowszy stan prac.
3. [`architecture/profile_hot_path_contract_130_11_plus.md`](architecture/profile_hot_path_contract_130_11_plus.md) — wiążąca bramka wydajności i integralności.
4. [`history/game_play_180726.md`](history/game_play_180726.md) — aktualna chronologia sprintów.

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
- [`runbooks/`](runbooks/) — instrukcje operatorskie i migracyjne.
- [`incidents/`](incidents/) — raporty incydentów.
- [`plans/`](plans/) — plany i propozycje przyszłych zmian.
- [`history/`](history/) — journale oraz historyczne roadmapy.

## Status bieżący

- Sprinty 130.10-130.12 oraz GhostNetwork Suite 131-135 są zamknięte albo
  przekazane do potwierdzonej walidacji zgodnie z journalem.
- Audit integracji Ollamy jest zapisany w
  [`sprints/sprint_135_1_ollama_outbox_integration_audit.md`](sprints/sprint_135_1_ollama_outbox_integration_audit.md).
  Przywraca formalnie zamrożony Sprint 84 oraz świadomie odłożony BlackNet AI
  Ecosystem (Sprint 21+), wyznacza jeden canonical outbox oraz roadmap 135.2+.
  Status: `SPRINT 135.1 — COMPLETE`; canonical transport 135.2 jest
  `READY FOR SERVER VALIDATION`.
- Osobne kontrakty realizacyjne:
  [`135.2 — canonical task transport`](sprints/sprint_135_2_canonical_llm_task_transport.md),
  [`135.3 — event producers i Googleplex ingress`](sprints/sprint_135_3_llm_event_producers_googleplex_ingress.md),
  [`135.4 — Ollama worker i canonical Inbox`](sprints/sprint_135_4_ollama_worker_canonical_inbox.md),
  [`135.4.1 — Googleplex Home i News foundation`](sprints/sprint_135_4_1_googleplex_home_news_foundation.md),
  [`135.4.1.1 — Googleplex Search Presentation Repair`](sprints/sprint_135_4_1_1_googleplex_search_presentation_repair.md),
  [`135.4.2 — kupowane narzędzie Googleplex`](sprints/sprint_135_4_2_googleplex_purchasable_llm_tool.md),
  [`135.5 — publishery BlackNet/Googleplex News/Cyberner`](sprints/sprint_135_5_llm_publishers_blacknet_googleplex_cyberner.md),
  [`135.5.2 — signal-aware narrative quality`](sprints/sprint_135_5_2_signal_aware_narrative_quality.md),
  [`135.6 — hardening i controlled cutover`](sprints/sprint_135_6_narrative_hardening_cutover.md).
- Sprint 135.2 rozszerza SQLite `ghost_narrative_outbox` do jednej kolejki z
  canonical dedupe, claim/lease/CAS, retry/dead-letter i crash recovery. Legacy
  BlackNet JSON jest tylko eksportem diagnostycznym; Ollama, Inbox, producenci i
  publikacja pozostają poza zakresem do kolejnych bramek.
- Recovery Trollu2 jest zakończone i nie jest aktywnym backlogiem.

Przenosząc lub dodając dokument, należy zaktualizować ten indeks i wszystkie
wersjonowane referencje. Nie należy tworzyć ponownie płaskich plików w katalogu
głównym `doc/` poza tym indeksem.
