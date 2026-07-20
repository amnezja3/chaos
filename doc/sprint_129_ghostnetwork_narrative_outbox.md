# Sprint 129 - GhostNetwork Narrative Outbox

## Cel

Sprint 129 podlacza final GhostNetwork do istniejacych mediow przez bezpieczny
narracyjny outbox. Backend tworzy fakty, a media moga je pozniej renderowac.
Narracja nie zmienia mechaniki gry.

## Zrodlo prawdy

Zrodlem prawdy pozostaja:

* zdarzenia domenowe GhostNetwork,
* `ghost_signals`,
* niezmienny `ghost_cycle_lock_snapshots`,
* katalog i wersja GhostSystemu.

`ghost_narrative_outbox` jest kolejka publikacji i nie liczy stanu gry.

## Wdrozone elementy

* `GhostNarrativePublisher`.
* Rozszerzony kontrakt `ghost_narrative_outbox`.
* Idempotentne rekordy publikacji per event, medium i odbiorca.
* Fakty `signal_sent`, `network_closed`, `restart_required`.
* Media outbox:
  * `blacknet`,
  * `cyberner`,
  * `radio`,
  * `ollama_outbox`.
* Dozwolone CTA:
  * `open_ghostnetwork_suite`,
  * `open_ghostsignal_archive`,
  * `open_cyberner_channel`,
  * `play_ghostnetwork_podcast`.
* Walidator odpowiedzi modelu narracyjnego.
* Retry publikacji `created/failed -> ready`.
* Integracja z `GhostNetworkService.start_transmission()`.

## Zasady bezpieczenstwa

Outbox nie zawiera pelnych profili, hasel, maili, sesji, ukrytych czesci,
pelnej topologii ani danych owner-only dla publikacji publicznej.

Ollama otrzymuje tylko zatwierdzone fakty i dozwolone CTA. Nie moze dopisac
nowych faktow, podniesc wiarygodnosci ani wykonac akcji gameplayowej.

Awaria outboxa nie cofa transmisji GhostSignalu.

## Poza zakresem

* Brak finalnego renderowania publikacji w BlackNecie.
* Brak bezposredniego wysylania wiadomosci Cybernera.
* Brak automatycznego uruchamiania radia.
* Brak integracji z realnym modelem Ollama.
* Brak odpowiedzi z 2108.

## Walidacja

Uruchomiono:

* `python -m py_compile ghostnetwork/repository.py ghostnetwork/narrative.py ghostnetwork/service.py`
* `python -m unittest tests.test_ghostnetwork_narrative tests.test_ghostnetwork_transmission`

Wynik: OK.
