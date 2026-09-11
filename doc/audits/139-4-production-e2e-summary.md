# Sprint 139.4 — production E2E PASS

Data: 2026-09-11. Źródło dowodów: podsumowania raportów i obserwacje
przekazane przez operatora w rozmowie; brak bezpośredniego dostępu do serwera.

- Cykl: ghostnetwork_0001, po uzgodnionym restore checkpointu sprzed GS.
- Online preflight, worker verify, runtime, lifecycle i narrative: PASS.
- Show automatycznie widoczne w trzech sesjach; powrót karty i telefonu z tła
  zgodny ze scenariuszem. Operator potwierdził restart i Signal Registry.
- Restart event: event_d0853416ab75f181; created_at 2026-09-11T07:39:16.244206+00:00.
- Epoka: 0eaad45377d9ff8ee821ee9a786ddca7d93958d44142046b56c29bc4c2e4bbce.
- Jeden restart event, 3 boot receipts, 3 ACK, brak truncation.
- Końcowy strict endgame: ok=true, status=complete, brak integrity_errors/pending.
- Show created 07:24:15.001871 UTC; pierwszy skutek 07:24:15.167819 UTC;
  signal sent 07:24:15.950182 UTC. Chronologia valid, bez violations.
- Monitor zatrzymany poprawnie: 1216 próbek, zero błędów. Restart i nowy
  aktywny cykl zaobserwowane o 07:39:17.681769 UTC; ACK o 07:39:19.680102 UTC.

Pierwotny czerwony postflight błędnie uwzględniał daty nagród całego cyklu.
Poprawka ograniczyła je do badanego signal_id; 12 izolowanych testów PASS,
w tym odrzucenie rzeczywiście zbyt wczesnej nagrody sygnału. Ponowny audyt
tej samej transmisji przeszedł bez ponownego triggera lub mutacji danych.

Audyt konfliktów sprawdził dwa konflikty, bez naruszeń chronologii. Operator
obserwował dodatkową blokadę po rozwiązaniu S1. Dokładnej przyczyny różnicy
względem wcześniejszego preflightu nie ustalono. Przybliżonych godzin
obserwacji UI nie traktujemy jako precyzyjnego pomiaru opóźnień.

SFX wystąpił według operatora 2–3 min po początku show, równocześnie w sesjach.
Kod wiąże go z ghost.signal_sent. Decyzja operatora: pozostawić i wykorzystać
w Sprincie 140. Nie przypisujemy tego opóźnienia czasowi wykonywania skutków
transmisji; kanoniczne znaczniki wskazują mniej niż sekundę od utworzenia show.

Pełne dowody na serwerze:
`data/audits/139-4-restored-20260911T064618158666Z/` — monitor.jsonl,
monitor.summary.json, final-endgame.json (pierwotny), final-endgame-recheck.json,
final-runtime.json, final-lifecycle.json, final-narrative.json, final-restart.json.
Pełnych plików nie skopiowano lokalnie; niniejszy dokument utrwala przekazane summary.
