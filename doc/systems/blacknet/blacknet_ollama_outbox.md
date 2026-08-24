# BlackNet Ollama Outbox

Sprint 83 dodaje bezpieczny kontrakt paczki dla lokalnego procesu Ollamy.

Outbox nie uruchamia modelu i nie daje mu dostepu do bazy danych, profilu,
mapy ani systemow gry. Model moze pobrac tylko zamkniety, walidowany JSON z
faktami swiata i zasadami redakcyjnymi.

## Flow

```text
blacknet_world_facts
+
blacknet_world_signals
+
editorial context
↓
blacknet_ollama_outbox
↓
Ollama worker
↓
future validated inbox
```

## Endpointy

```text
POST /api/blacknet/ollama/outbox/generate
GET  /api/blacknet/ollama/outbox/latest
GET  /api/blacknet/ollama/outbox/<digest_id>
POST /api/blacknet/ollama/outbox/<digest_id>/status
```

Wszystkie endpointy Sprintu 83 sa kontrolowane przez konto admin/dev. Nie sa
czescia zwyklego UI gracza.

## Statusy

Dozwolone statusy paczki:

* `created`,
* `ready`,
* `processing`,
* `processed`,
* `failed`,
* `expired`,
* `archived`.

Pakiet z bledami walidacji nie moze zostac oznaczony jako `ready`.

## Schema v1

Najwazniejsze pola paczki:

* `schema_version`,
* `digest_id`,
* `status`,
* `world_version`,
* `world_signals_version`,
* `generated_at`,
* `valid_until`,
* `facts`,
* `selected_signals`,
* `trends`,
* `important_regions`,
* `available_products_and_markets`,
* `allowed_signal_types`,
* `allowed_actions`,
* `existing_identifiers`,
* `author_personas`,
* `limits`,
* `language`,
* `world_tone`,
* `forbidden_claims`,
* `editorial_rules`,
* `recent_publications`,
* `diagnostics`,
* `validation`.

## Zasady bezpieczenstwa

Outbox:

* zachowuje `fact_id` i wersje z `blacknet_world_facts`,
* usuwa prywatne pola metadanych, np. `username`, `email`, `participants`,
  `token`, `secret`,
* nie przekazuje pelnego profilu,
* nie przekazuje pelnej mapy,
* nie przekazuje bazy danych,
* nie tworzy nowych CTA,
* nie uruchamia Ollamy,
* nie wykonuje zadnych akcji gameplayowych.

Ollama moze pisac narracje tylko na podstawie faktow, ktore dostala w paczce.
Nie moze wymyslac cen, targetow, wspolrzednych, URL ani nagrod.

## Walidacja

Walidator sprawdza:

* wersje schematu,
* obecny `digest_id`,
* obecna liste faktow,
* obecny `fact_id` w kazdym fakcie,
* czy `allowed_actions` mieszcza sie w whitelist BlackNet CTA,
* maksymalny rozmiar paczki.

## Przechowywanie

Paczki sa zapisywane atomowo w katalogu instancji aplikacji:

```text
instance/blacknet_ollama_outbox/
```

Nazwa pliku pochodzi z `digest_id`. Zapis uzywa pliku tymczasowego i
`os.replace()`, zeby worker nie przeczytal polowicznej paczki.

## Granica Sprintu 83

Sprint 83 konczy sie na outboxie.

Poza zakresem:

* uruchamianie Ollamy,
* odbior odpowiedzi modelu,
* mieszanie feedu AI z deterministic publisher,
* publikacja kandydatow w BlackNecie.

Te elementy nie startuja automatycznie po Sprincie 83.

## Decyzja po Sprincie 83

Sprint 84 zostaje zamrozony do czasu domkniecia stabilnego kontraktu odpowiedzi
Ollamy i daemonowego feedback loop.

Kolejny etap powinien najpierw opisac:

* kanoniczny rejestr `signal_type`,
* format kandydatow zwracanych przez model,
* statusy walidacji kandydatow,
* zasady insertu zaakceptowanych kandydatow do strumienia BlackNet,
* kwarantanne dla kandydatow odrzuconych,
* diagnostyke powodow odrzucenia.

Outbox pozostaje jednostronnym, bezpiecznym kontraktem wyjsciowym. Dopoki ingest
nie jest gotowy, BlackNet dziala na `world_generated`, realnych generatorach i
`out_of_signal`.
