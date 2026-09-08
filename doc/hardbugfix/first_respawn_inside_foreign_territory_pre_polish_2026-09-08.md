# Pierwszy respawn wewnątrz kontrolowanego terytorium

**Etap:** pre-polish po `138.getway.4`  
**Data:** 2026-09-08  
**Severity:** P1 onboarding/gameplay  
**Status:** `IMPLEMENTED / LOCAL PASS / SERVER E2E PENDING`

## Problem

Pozycja nowego konta jest wyznaczana z geolokalizacji IP. W dużym mieście punkt
providera może wypaść wewnątrz aktywnego terytorium innego gracza. Nowy operator
zaczyna wtedy bez zasięgu, narzędzi i wiedzy potrzebnej do zrozumienia blokady, a
sam start może zostać błędnie potraktowany jak wartościowe wtargnięcie.

## Decyzja architektoniczna

Jeżeli wyliczona pozycja pierwszego respawnu znajduje się wewnątrz aktywnego lub
okrążonego, nadal kontrolowanego terytorium, konto otrzymuje najbliższy wolny punkt
poza całą kontrolowaną strefą. Punkt znajduje się domyślnie 180 metrów za granicą.

Polityka działa tylko podczas finalizacji rejestracji. Nie korzysta z teleportu,
travel, operacji, targetu ani Response Network, dlatego nie emituje alarmu
wtargnięcia właścicielowi.

## Realizacja

`resolve_first_respawn_outside_controlled_territory()`:

- normalizuje aktualne geometrie z istniejącej projekcji `player_areas`;
- sprawdza punkt IP względem wszystkich kontrolowanych wielokątów;
- projektuje punkt na krawędzie i testuje obie strony każdej granicy;
- odrzuca kandydatów pozostających wewnątrz dowolnego obszaru;
- wybiera najbliższy punkt poza sumą nakładających się lub zagnieżdżonych
  terytoriów;
- dodaje konfigurowalny margines
  `CHAOS_FIRST_RESPAWN_TERRITORY_MARGIN_METERS` (domyślnie 180 m);
- posiada deterministyczny fallback radialny dla nietypowych geometrii;
- nie tworzy konta, jeżeli mimo zabezpieczeń nie można wyznaczyć wolnego punktu.

Ta funkcja jest czystą polityką pozycjonowania i może później zostać wykorzystana
w GhostLab jako schemat Pro Toola.

## Invariant

```text
pierwszy respawn ∉ każde aktywne kontrolowane terytorium
rejestracyjna korekta pozycji ≠ ruch gracza
rejestracyjna korekta pozycji ≠ intrusion/detection/alarm
```

## Testy

- wolny punkt IP pozostaje bez zmian;
- punkt wewnętrzny trafia za granicę z marginesem;
- zagnieżdżone terytoria są traktowane jak jedna kontrolowana strefa;
- nieaktywne terytorium nie zmienia respawnu;
- `/api/register-finalize` zapisuje skorygowany punkt bez pipeline'u ruchu.

## Pliki

- `run.py`
- `tests/test_first_respawn_territory_edge.py`
- `doc/history/project_journal.md`

## Bramka

`LOCAL PASS / SERVER E2E PENDING`

