# Utrata profilu Trollu2 — Sprint 130.11

**Plik:** `profile_loss_trolu2_sprint_130_11_2026-08-24.md`  
**Projekt:** CHAOS  
**Sprint:** 130.11  
**Data zamknięcia:** 2026-08-24  
**Status:** `RECOVERY COMPLETE`  
**Klasyfikacja:** krytyczny incydent integralności profilu / controlled recovery / session & profile safety

---

## 1. Problem / objawy

Podczas normalnego gameplayu konto `trolu2` utraciło znaczną część progression i zaczęło wyglądać jak świeżo utworzone konto.

Najbardziej widoczne objawy:

- poziom spadł z około `LVL 25/26` do wartości startowej,
- Respect został zredukowany,
- wallet wrócił do niskiej wartości,
- nick i avatar przyjęły wartości domyślne,
- część danych tożsamości profilu zniknęła,
- na mapie zniknęły wcześniej istniejące terytoria,
- jednocześnie aplikacje i narzędzia gracza pozostały dostępne,
- przełączanie kont i sesji ujawniło dodatkowe problemy z izolacją session state.

Incydent nie wyglądał jak zwykły reset jednej wartości. Profil był częściowo poprawny, a częściowo zastąpiony stanem przypominającym bootstrap nowego użytkownika.

---

## 2. Wpływ na grę

Incydent dotyczył kilku krytycznych warstw jednocześnie:

- progression,
- walletu,
- profilu,
- identity,
- mapy,
- terytoriów,
- session state,
- Last Known Good profile,
- integralności zapisów `profile_json`.

Największym ryzykiem było wykonanie szybkiego ręcznego „restore” całego profilu i nadpisanie nowszego canonical state, który powstał już po incydencie.

Dlatego zrezygnowano z ręcznych SQL hotfixów i pełnego przywracania starego snapshotu.

---

## 3. Evidence początkowe

Audyt konta wykazał, że uszkodzony profil nadal posiadał część poprawnego canonical state.

W szczególności:

- inventory zawierało `11` aplikacji,
- inventory zawierało `11` narzędzi,
- Nmap i Metasploit były nadal zainstalowane,
- Googleplex posiadał potwierdzony zakup biletu do Tokio,
- GhostNetwork posiadał aktywny cykl z `20` częściami,
- profile checksum przechodził walidację,
- wallet canonical store nadal był spójny ze swoim ledgerem,
- historyczne targety Trollu2 nadal istniały w bazie.

To oznaczało, że profilu nie można było po prostu zastąpić starym backupem.

---

## 4. Pierwotna przyczyna incydentu

Audyt historycznej ścieżki GhostNetwork wykazał poważną wadę architektoniczną.

Jedna z dawnych ścieżek reward / activation pracowała na lekkiej projekcji identity użytkownika, a następnie mogła potraktować tę projekcję jak pełny profil i zapisać ją jako cały `profile_json`.

W praktyce oznaczało to ryzyko:

```text
bounded / sparse identity projection
→ potraktowana jak pełny profile object
→ zapis pełnego profile_json
→ utrata pól, których projection nigdy nie zawierała
```

Wada była silnie zgodna z symptomami Trollu2.

Nie istniała jednak kompletna telemetria pojedynczego historycznego write, dlatego końcowa klasyfikacja przyczyny była:

`ROOT CAUSE CONFIRMED WITH HIGH CONFIDENCE`

Najważniejszy wniosek architektoniczny:

> Cache, viewer projection, identity row, session profile i inne bounded projections nigdy nie mogą zostać użyte jako źródło pełnego canonical profilu.

---

## 5. Sprint 130.10 — zabezpieczenia poprzedzające recovery

Przed odbudową konta wykonano Sprint 130.10, którego celem było uniemożliwienie ponownego wystąpienia podobnej klasy uszkodzeń.

Wprowadzono między innymi:

- profile revision,
- checksum,
- CAS guarded writes,
- Last Known Good profile,
- session generation,
- izolację sesji i kart,
- precommit guards,
- canonical wallet/inventory boundaries,
- ochronę przed zapisem starego snapshotu na nowszy profil.

Dodatkowo Sprint 130.10.1 usunął regresję wydajnościową, w której pełny profil trafił do gorących ścieżek gameplayowych.

Recovery rozpoczęto dopiero po zbudowaniu tych zabezpieczeń.

---

## 6. Pierwsza próba recovery i rollback

Pierwszy plan controlled recovery zakładał:

- `LVL 50`,
- `RSP 2560`,
- `250000 HC`,
- zachowanie inventory,
- bonusowe terytorium w Tokio.

Pierwszy apply podniósł poziom oraz przyznał bonusowe filary.

Worker przebudował jednak terytorium i utworzył nieplanowany konflikt z innym graczem.

Recovery natychmiast zatrzymano.

Nie wykonano finalnego wallet settlementu ani promocji LKG.

Następnie wykonano kontrolowany rollback:

- usunięto wyłącznie recovery-owned bonus targets,
- rozwiązano wyłącznie recovery-created conflict,
- przywrócono profil do stanu sprzed apply,
- wallet pozostał bez zmian,
- GhostNetwork pozostał nietknięty,
- rollback został zweryfikowany jako czysty.

Finalny rollback verify:

```text
blockers=[]
receipt_status=rolled_back
profile_restored=true
wallet_unchanged=true
recovery_targets=0
active_fronts=0
GhostNetwork recovery references=0
```

---

## 7. Kluczowa diagnoza geometrii

Po rollbacku wykonano osobny read-only geometry audit.

Najważniejsze odkrycie:

> Historyczne markery Trollu2 nie zniknęły podczas incydentu. Zniknęły jedynie aktywne terytoria.

Evidence:

```text
captured targets: istnieją
stationary targets: istnieją
ownership history: istnieje
active player areas: 0
```

Symulacja canonical workera dla tych samych markerów:

| LVL | Active areas | Powierzchnia | Kolizje |
|---:|---:|---:|---:|
| 2 | 0 | 0 m² | 0 |
| 25 | 2 | 2 638 470,30 m² | 3 |
| 26 | 2 | 2 638 470,30 m² | 3 |
| 50 | 2 | 2 638 470,30 m² | 3 |

Wniosek:

- przy niskim LVL markery były zbyt daleko od siebie, aby domknąć obszary,
- od około LVL 25 geometria ponownie się aktywowała,
- LVL 50 nie zwiększał już powierzchni względem 25/26,
- w czasie geometrycznej nieaktywności świata gry inni gracze zajęli część historycznych obszarów Trollu2.

Klasyfikacja:

`DIAGNOSIS CONFIRMED — BOTH LEVEL SCALING AND WORLD EVOLUTION CONTRIBUTE`

---

## 8. Historyczne kolizje

Po reaktywacji historycznej geometrii występowały kolizje z terytoriami utworzonymi już po incydencie.

Dotyczyło to między innymi graczy:

- `neo1`,
- `pies1`.

Nie było poprawne odebranie im nowych terytoriów tylko po to, aby odtworzyć mapę Trollu2 1:1.

Recovery musiało uwzględnić aktualny canonical world state.

---

## 9. Tokio — oddzielenie bonusu od starej geometrii

Pierwszy planner błędnie analizował razem:

- historyczne markery Trollu2,
- nowe bonusowe markery Tokio.

Po rozdzieleniu geometrii uzyskano:

```text
bonus-only Tokio:
8 targets
1 closed area
collision_count=0
```

To potwierdziło, że sam bonus Tokio był bezpieczny.

Historyczne konflikty wynikały ze starych markerów, a nie z nowego bonusu.

---

## 10. Recovery v2 — finalna strategia

Wybrano wariant kontrolowanego retirementu historycznych markerów.

Recovery v2 wykonywało:

1. podpisany plan,
2. dry-run,
3. backup before-manifest,
4. retirement dokładnie 9 historycznych stationary targets,
5. trwały audit retirementu,
6. worker rebuild,
7. potwierdzenie 0 historycznych areas,
8. podniesienie LVL,
9. przyznanie 8 bonusowych targetów Tokio,
10. finalny worker rebuild,
11. exactly-once wallet settlement,
12. ustawienie Respect,
13. finalny verify,
14. promocję LKG.

Nie wykonano bezśladowego DELETE historii ownership.

---

## 11. Retirement 9 historycznych targetów

Recovery wycofało z aktywnej geometrii dokładnie 9 stationary captured targets, które tworzyły dwa historyczne komponenty.

Warszawa — 6 targetów:

- `map:52.1486:20.90033:DPD`
- `map:52.15753:20.8892:POI-9D7173`
- `map:52.15806:20.90962:Cerber`
- `map:52.15876:20.9115:POI-67044F`
- `map:52.16796:20.89818:POI-166846`
- `map:52.17101:20.90633:Arkazen`

Japonia — 3 targety:

- `map:35.36472:139.46136:Lawson`
- `map:35.36583:139.44617:ユーミーClass`
- `map:35.37252:139.45338:スーパー生鮮館TAIGA 藤沢石川店`

Generated, non-stationary `Kuriero-bot` nie został objęty retirementem.

---

## 12. Ownership absent — poprawka kontraktu recovery

Podczas dry-run Recovery v2 wykryto, że 9 targetów istnieje w `captured_targets`, ale nie posiada odpowiadających rekordów w ownership registry.

Początkowo planner traktował to jako blocker:

```text
retirement_ownership_missing
```

Audyt workera wykazał jednak, że geometria jest budowana z:

```text
captured_targets WHERE stationary=1
```

Ownership registry nie jest wejściem canonical geometry.

Recovery zostało więc poprawione tak, aby obsługiwało jawnie:

```text
ownership_state = absent
```

Brak ownership row stał się legalnym, podpisanym precondition zamiast błędu.

---

## 13. Phase-aware resume

Podczas finalnego recovery wykryto jeszcze jeden błąd w maszynie stanów.

Po:

```text
retirement
→ rebuild 0 areas
→ bonus Tokio 8 targets
→ rebuild 1 area
```

kolejny apply ponownie wykonywał pre-bonus retirement verification i uznawał legalne Tokio za powrót historycznej geometrii.

Objaw:

```text
canonical_worker_stationary_input_count=8
canonical_worker_preview_area_count=1
```

czyli dokładnie nowe Tokio.

Recovery zostało poprawione tak, aby:

- retirement verification po milestone sprawdzało tylko historyczny scope,
- bonus Tokio posiadał osobną final geometry gate,
- istniejący receipt można było bezpiecznie wznowić bez rollbacku,
- settlement pozostał exactly-once.

---

## 14. Finalny apply

Po wznowieniu existing receipt:

```text
phase=APPLIED_READY_FOR_VERIFY
```

Finalny settlement:

```text
LVL=50
RSP=2560
HC=250000
wallet_version=121
profile_revision=6
```

Worker potwierdził:

```text
Tokio areas=1
conflicts=0
```

Finalny verify recovery:

```text
blockers=[]
ok=true
recovery_targets=8
active_area_count=1
recovery_conflicts=0
GhostNetwork recovery_reference_count=0
```

Następnie profil został promowany jako LKG.

---

## 15. Identity repair

Po zakończeniu gameplay recovery UI nadal pokazywało:

```text
nick = NowyHaker
avatar = default_avatar.png
profession = null
```

Nie przywracano całego starego profilu.

Wykonano osobną field-level identity repair.

Zatwierdzony contract:

```text
nick = Trolu 2
profession = Socjotechnik
avatar = /static/images/avatar-frakcja-2-player-2.png
```

Provenance:

- `Trolu 2` — historycznie potwierdzona nazwa gracza,
- `Socjotechnik` — nowy wybór gracza po recovery, nie historyczne odtworzenie,
- avatar — canonical mapping aktualnego klanu i wybranej profesji.

---

## 16. Post-recovery revision drift

Przed identity repair wykryto:

```text
recovery final = revision 6
LKG = revision 7
current profile = revision 8
```

Początkowo identity repair blokował się, ponieważ oczekiwał profilu identycznego z revision 6.

Read-only drift audit wykazał jednak:

- brak protected gameplay drift,
- brak identity drift,
- brak wallet drift,
- brak inventory apps/tools drift,
- późniejsze zapisy były `validated`,
- revision 7/8 powstały przez normalne `profile_manager.update_profile`.

Wniosek:

> Zakończone recovery jest historycznym milestone’em. Późniejsze prawidłowe zapisy profilu nie unieważniają recovery.

Identity repair zostało więc oparte na current canonical profile i CAS dla bieżącej revision.

---

## 17. Finalny identity apply

Identity plan został wygenerowany dla current revision 8.

Dry-run przewidywał zmianę wyłącznie:

```text
avatar
nick
profession
```

Apply zakończył się:

```text
changed_fields = [avatar, nick, profession]
profile_revision = 9
status = applied
```

Verify:

```text
blockers=[]
ok=true
inventory=11/11
LVL=50
RSP=2560
HC=250000
Tokio targets=8
Tokio areas=1
recovery conflicts=0
GhostNetwork untouched
```

Następnie revision 9 został promowany jako nowy LKG.

Finalny identity receipt:

```text
status=complete
lkg_matches_identity_profile=true
```

---

## 18. Finalny stan Trollu2

Potwierdzony produkcyjnie stan końcowy:

```text
username: trolu2
nick: Trolu 2
clan: Echo Wolności
profession: Socjotechnik
avatar: /static/images/avatar-frakcja-2-player-2.png

LVL: 50
RSP: 2560
HC: 250000
EXP: 2217312.71 m² efektywne

apps: 11
tools: 11

recovery targets: 8
active Tokio areas: 1
recovery conflicts: 0

historical retirement audit: 9/9

GhostNetwork parts: 20
GhostNetwork recovery references: 0

final profile revision: 9
recovery receipt: complete
identity receipt: complete
final LKG matches profile: true
```

Stan został również sprawdzony manualnie w produkcyjnym UI.

---

## 19. Narzędzia operatorskie

Podczas Sprintu 130.11 powstały między innymi:

- `tools/repair_trollu2_profile.py`
- `tools/repair_trollu2_identity.py`
- `tools/audit_trollu2_geometry.py`

Narzędzia są plan-driven.

Nie wykonują recovery bez odpowiedniego planu i jawnego trybu zapisu.

Typowy bezpieczny lifecycle:

```text
status
→ audit
→ plan
→ dry-run
→ backup
→ apply
→ worker verification
→ verify
→ promote LKG
```

Skrypty nie są zwykłą ścieżką gameplayu.

Po zamknięciu Sprintu 130.11 nie należy ponownie uruchamiać starego recovery planu.

---

## 20. Najważniejsze testy i zabezpieczenia

Recovery oraz zabezpieczenia pokryto testami obejmującymi między innymi:

- profile CAS,
- checksum/revision,
- LKG,
- duplicate apply,
- exactly-once wallet settlement,
- retirement exact scope,
- ownership present/absent,
- worker rebuild resume,
- recovery conflict detection,
- world drift,
- inventory preservation,
- GhostNetwork non-interference,
- identity field-level mutation,
- current-profile rebase,
- post-recovery revision drift,
- final LKG verify.

Podczas kolejnych iteracji zestawy testów recovery i territory były rozszerzane wraz z wykrywanymi edge-case’ami.

---

## 21. Czego nie robić w podobnym incydencie

Nie należy:

- przywracać całego starego profilu bez analizy,
- kopiować profile JSON z cache/session/projection,
- wykonywać ręcznych SQL update’ów progression,
- usuwać targetów bez audit trail,
- odbierać terytoriów innym graczom tylko po to, aby odtworzyć historyczny snapshot,
- zakładać, że world state nie zmienił się od chwili incidentu,
- wykonywać wallet settlement bez idempotency key,
- promować LKG przed verify,
- pomijać CAS tylko dlatego, że operacja jest „operatorska”.

---

## 22. Najważniejsze wnioski architektoniczne

### 22.1 Projection nigdy nie jest profilem

Najważniejszy wniosek z całego incydentu:

```text
sparse projection != canonical profile
```

Każdy bounded projection musi mieć własny typ/kontrakt i nie może być akceptowany przez API pełnego profile write.

### 22.2 Recovery musi respektować aktualny świat

Historyczny stan gracza i obecny world state mogą się rozjechać.

Recovery musi korzystać z current canonical world i fail-closed przy nowych kolizjach.

### 22.3 Projection geometry nie jest canonical source

Usunięcie `player_areas` nie usuwa źródła geometrii.

Canonical stationary targets muszą posiadać poprawny lifecycle.

### 22.4 Recovery potrzebuje resumable milestones

Długie recovery zależne od workerów musi być:

- etapowe,
- exactly-once,
- resumable,
- phase-aware,
- możliwe do zweryfikowania po każdym kroku.

### 22.5 LKG jest checkpointem, nie zamrożonym profilem

Prawidłowe późniejsze zapisy mogą zastąpić wcześniejszy LKG.

Historyczne recovery LKG nie może blokować legalnego przyszłego gameplayu.

### 22.6 Operator tooling również wymaga kontraktów produkcyjnych

Skrypt recovery musi mieć takie same standardy jak krytyczny runtime:

- CAS,
- receipts,
- signatures,
- audit,
- dry-run,
- backup,
- fail-closed,
- exactly-once.

---

## 23. Powiązane dokumenty

Najważniejsze źródła powiązane z incydentem:

- `doc/sprint_130_11_trollu2_controlled_recovery.md`
- `doc/Incydent Trollu2 — utrata profilu, błędy sesji i plan odbudowy.md`
- `doc/sprint_130_10_profile_integrity_session_isolation.md`
- `doc/sprint_130_10_1_hot_path_recovery.md`
- `doc/profile_hot_path_contract_130_11_plus.md`
- `doc/project_journal.md`
- `doc/ghostnetwork_architecture.md`
- `database.py`
- `session_generation_store.py`
- `territory_geometry.py`
- `ghostnetwork/`

---

## 24. Powiązane commity

Istotne commity z końcowej części recovery:

- `818a676` — optional ownership recovery contract,
- `90ec033` — phase-aware Trollu2 recovery resume,
- `99bd14d` — identity repair tooling,
- `cc771ab` — drift audit / current-profile identity safety,
- `2ae469a` — formalne zamknięcie Sprintu 130.11.

Lista nie obejmuje wszystkich wcześniejszych commitów Sprintu 130.10/130.11.

---

## 25. Status końcowy

```text
SPRINT 130.11 — COMPLETE
TROLU2 CONTROLLED RECOVERY — COMPLETE
IDENTITY REPAIR — COMPLETE
RECOVERY RECEIPT — COMPLETE
IDENTITY RECEIPT — COMPLETE
FINAL LKG — VERIFIED
```

**Problem rozwiązany.**

Nie istnieje dalszy aktywny recovery backlog dla `trolu2`.

Jeśli podobny incydent wystąpi ponownie, należy utworzyć nowy plan i nowy artefakt `hardbugfix`, a nie reaktywować stare recovery.
