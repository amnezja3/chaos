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

- Sprinty 130.10, 130.10.1, 130.10.2 i 130.11 są zamknięte.
- Audit Sprintu 131 jest zakończony. Projekt ma `NO-GO FOR SPRINT 132` do
  zamknięcia blockerów wskazanych w
  [`sprints/sprint_131_ghostnetwork_suite_audit.md`](sprints/sprint_131_ghostnetwork_suite_audit.md).
- Recovery Trollu2 jest zakończone i nie jest aktywnym backlogiem.

Przenosząc lub dodając dokument, należy zaktualizować ten indeks i wszystkie
wersjonowane referencje. Nie należy tworzyć ponownie płaskich plików w katalogu
głównym `doc/` poza tym indeksem.
