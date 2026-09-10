# 138.2 — GhostSignal Cyberner support repair

## Produkcyjny przypadek

Pierwsza emisja `ghostnetwork_0001` utworzyła dokładnie trzy taski narracyjne.
BlackNet i Googleplex News zostały opublikowane. Kandydat Cybernera został
zachowany w kwarantannie:

- `task_id`: `narrative_task_f50c7ebe7c7d3bec`,
- `validation_status`: `quarantined`,
- `quarantine_reason`: `selected_fact_mismatch`,
- tytuł: `PRZECHWYT //`,
- fakty: `f01`, `f02`, `f03` — wszystkie pochodziły z kanonicznego pakietu.

## Przyczyna

Walidator wymagał, aby lista referencji była dokładnie równa jednemu
`selected_source_ref`, choć pakiet GhostSignal przekazywał trzy powiązane fakty.
Jednocześnie incomplete-title guard nie rozpoznawał samego prefiksu
`PRZECHWYT //`, a support contract nie gwarantował fallbacku Cybernera dla
końcowych zdarzeń sieci.

## Naprawa

- główny `selected_source_ref` musi być obecny, ale może mu towarzyszyć inny
  kanoniczny fact ref;
- sam prefiks `PRZECHWYT //` jest odrzucany jako `voice_title_missing_subject`;
- Cyberner ma deterministyczne fallbacki dla `machine_online`, `cycle_locked`
  i `signal_sent`;
- `repair-support` zachowuje pierwotnego kandydata w kwarantannie, requeue'uje
  wyłącznie wskazany zakończony task i tworzy osobny accepted candidate z
  zachowanego raw outputu bez drugiego wywołania modelu;
- monitor 138.2 raportuje osobno accepted i quarantined candidates.

## Oczekiwany zapis po naprawie

- trzy taski `completed`,
- trzy accepted candidates,
- jeden dodatkowy historyczny quarantined candidate,
- trzy receipts i trzy opublikowane medium records,
- pierwotny raw output oraz jego przyczyna kwarantanny pozostają audytowalne.

## Weryfikacja lokalna

Zestaw testów walidatora, support layer, kolejki, workera, PM2 contract i
monitora 138.2: `83/83 OK`.
