# Najcięższe hotfixy developmentu

Katalog `doc/hardbugfix/` przechowuje osobne artefakty dokumentacyjne dotyczące najtrudniejszych błędów, regresji i incydentów technicznych napotkanych podczas developmentu CHAOS.

Dokumenty te są niezależne od `project_journal.md`.

## Artefakty

- [Sprint 135.5 — regresje kontraktu publikacji LLM](llm_publication_contract_regressions_sprint_135_5_2026-08-30.md)

Dziennik projektu zapisuje chronologię prac, natomiast `hardbugfix/` ma zachować pełny kontekst problemu: objawy, diagnozę, root cause, wykonane próby naprawy, finalne rozwiązanie oraz wnioski istotne dla przyszłych sprintów.

Celem katalogu jest stworzenie trwałej bazy wiedzy o problemach, których ponowne diagnozowanie od zera byłoby kosztowne.

Do `doc/hardbugfix/` powinny trafiać przede wszystkim problemy, które:

- wymagały wieloetapowej diagnozy;
- powodowały poważne regresje gameplayu lub runtime;
- dotyczyły integralności danych, profili, sesji lub canonical state;
- ujawniły istotny problem architektoniczny;
- wymagały recovery lub kontrolowanych operacji na produkcji;
- powracały mimo wcześniejszych poprawek;
- mogą być istotnym punktem odniesienia dla kolejnych sprintów.

Typowe przykłady:

- utrata lub uszkodzenie profilu gracza;
- regresje CAS / LKG / session generation;
- SQLite contention i długie writer-locki;
- duplikacja efektów gameplayowych;
- błędy territory rebuild / conflict lifecycle;
- trudne race conditions frontendu;
- awarie renderera Leaflet / GhostNetwork;
- regresje heavy-profile hot pathów.

## Struktura nazw plików

Nazwy dokumentów mają format:

`problem_alias_sprint_nr_data.md`

gdzie:

- `problem_alias` — krótka, jednoznaczna nazwa problemu;
- `sprint_nr` — sprint, w którym problem był diagnozowany lub naprawiany;
- `data` — data utworzenia artefaktu w formacie `YYYY-MM-DD`.

Przykłady:

`profile_loss_trolu2_sprint_130_11_2026-08-24.md`

`leaflet_bounds_undefined_x_sprint_130_12_2026-08-24.md`

`sqlite_writer_contention_sprint_130_9_2026-08-23.md`

`session_generation_relogin_sprint_130_12_2026-08-24.md`

## Zalecana struktura dokumentu

Każdy artefakt powinien w miarę możliwości zawierać:

1. **Problem / objawy**
2. **Wpływ na grę lub runtime**
3. **Warunki reprodukcji**
4. **Evidence**
5. **Root cause**
6. **Próby naprawy i odrzucone hipotezy**
7. **Finalne rozwiązanie**
8. **Testy i weryfikację**
9. **Wpływ na architekturę**
10. **Wnioski na przyszłość**
11. **Powiązane pliki, commity i sprinty**
12. **Status końcowy**

## Zasada

Artefakty `hardbugfix` nie są backlogiem.

Dokument zakończonego problemu powinien jasno wskazywać jego finalny status, np.:

`RESOLVED`

`MITIGATED`

`ROOT CAUSE CONFIRMED`

`RECOVERY COMPLETE`

Jeżeli problem powróci, nie należy bezrefleksyjnie nadpisywać starego dokumentu. Nowy incydent powinien otrzymać własny artefakt z odwołaniem do wcześniejszego przypadku.
