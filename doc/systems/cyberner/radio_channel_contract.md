# Ghost Hack Radio - Channel Contract

Ten dokument definiuje kontrakt `meta.channel` dla Ghost Hack Radio.

Sprint 53 przygotowuje format kanalow pod przyszly BlackNet, ale nie zaklada,
ze BlackNet istnieje juz fizycznie w runtime.

## Zasada glowna

`meta.channel` jest jedynym zrodlem prawdy dla zasad streamu kanalu.

Player:

* nie trzyma recznej playlisty w UI,
* pobiera katalog MP3 przez lekki resolver kanalu,
* stosuje `mode`, `sort` i `exclude` z `meta.channel`,
* buduje kolejke odtwarzania z plikow MP3 lezacych w katalogu kanalu.

## Struktura katalogu

```text
static/mp3/radio/channel/{channel_id}/
├── meta.channel
├── 001_track.mp3
└── 002_track.mp3
```

Kazdy kanal ma wlasny katalog. Pliki audio musza lezec w tym samym katalogu co
`meta.channel`.

## Minimalny kontrakt schema = 1

```json
{
  "schema": 1,
  "id": "ghost_streem_1",
  "name": "Ghost Hack Radio",
  "slug": "ghost-streem-1",
  "description": "Pierwszy piracki kanal systemowy GhostNet.",
  "source": "ghost_radio",
  "autoplay": true,
  "loop": true,
  "mode": "random",
  "sort": "name",
  "exclude": []
}
```

## Pola

### Język — sprint 154

`language` kanału i każdego wpisu `programs["nazwa.mp3"]` przyjmuje zatwierdzony
kod języka z manifestu i18n albo `neutral`, `mixed`, `unknown`. `ANY` jest wyłącznie
filtrem, nigdy językiem nagrania. Brak metadanych oznacza `unknown`.

```json
{
  "language": "pl",
  "programs": {
    "audycja.mp3": {"language": "pl"},
    "instrumental.mp3": {"language": "neutral"}
  }
}
```

Resolver kanału PL/EN dopuszcza tylko programy o tym samym języku lub neutralne;
kanał neutralny tylko programy neutralne. Nowy plik bez metadanych nie odziedziczy
deklaracji kanału. Kanały mieszane i niepotwierdzone pozostają dostępne pod ANY.
Panel administratora zwraca `language_validation` i wyświetla błędy kontraktu
oraz niezgodne pliki. Walidator publikacyjny: `radio_locale.validate_contract`.

UI zapamiętuje jawny filtr w `chaos:radio:language-filter` w tej przeglądarce.
Bez takiego wyboru korzysta z języka interfejsu. Zmiana filtra/języka nie zmienia
źródła audio, czasu ani stanu odtwarzania; przełączenie kanału wymaga wyboru.
Pusty wynik oferuje przycisk ANY. Bieżąca audycja pokazuje własny język.

Pola `presentation.name` / `presentation.description` zawierają opcjonalne
jawne klucze `radio.channel.*` dla kanałów systemowych. Nazwy bez takich kluczy
oraz autorskie tytuły utworów pozostają dosłowne.

Inwentaryzacja 7 X 2026: `blacknet_radio_2` zawiera 9 plików MP3,
`ghost_streem_1` zawiera 25. Każdy ma wpis `programs`. Dotychczasowe kontrakty
nie deklarowały języka, a nazwa pliku nie potwierdza języka nagrania. Wpisy
muzyczne otrzymały `unknown` do czasu potwierdzenia treści. Są dostępne pod ANY.
Autor potwierdził, że wszystkie 9 audycji BlackNet Radio jest po polsku;
ich wpisy oraz kanał mają `language: "pl"` i są dostępne pod PL/ANY.

| Pole | Typ | Wymagane | Znaczenie |
| --- | --- | --- | --- |
| `schema` | number | tak | Wersja kontraktu. Sprint 53 uzywa `1`. |
| `id` | string | tak | Stabilny identyfikator katalogu kanalu. |
| `name` | string | tak | Nazwa kanalu pokazywana w UI. |
| `slug` | string | tak | Czytelny identyfikator przyszlych list kanalow. |
| `description` | string | nie | Opis kanalu dla UI albo dokumentacji. |
| `source` | string | tak | Typ zrodla kanalu, np. `ghost_radio` albo przyszle `blacknet`. |
| `autoplay` | boolean | nie | Preferencja kanalu, nie wymuszenie autoplay w przegladarce. |
| `loop` | boolean | nie | Czy po ostatnim utworze wracac do pierwszego. |
| `mode` | string | nie | Tryb kolejki, np. `random` albo `ordered`. |
| `sort` | string | nie | Sortowanie katalogu przed zbudowaniem kolejki, np. `name`. |
| `exclude` | array | nie | Nazwy plikow MP3, ktorych nie odtwarzac. |

## Kolejka odtwarzania

Resolver kanalu czyta pliki `.mp3` z katalogu:

```text
static/mp3/radio/channel/{channel_id}/
```

Nastepnie:

* pomija pliki z `exclude`,
* sortuje zgodnie z `sort`,
* dla `mode: "random"` miesza kolejke i wybiera losowy start,
* zwraca read model dla `GhostRadio`.

Player tworzy URL pliku jako:

```text
/static/mp3/radio/channel/{channel_id}/{file}
```

## Source

`source` opisuje pochodzenie kanalu, nie playlisty i nie misji.

Dozwolone wartosci Sprintu 53:

```text
ghost_radio
blacknet
system
unknown
```

`blacknet` jest wartoscia kontraktowa dla przyszlosci. Sprint 53 nie dodaje
runtime BlackNet ani endpointow BlackNet.

## Czego kontrakt nie robi

Kontrakt kanalu nie jest:

* backendem radia,
* systemem misji,
* Cybernerem,
* dynamicznym streamingiem,
* mechanizmem pobierania MP3,
* lista kanalow.

## Zasada przyszlej integracji BlackNet

Przyszly BlackNet ma dokladac kanaly przez:

```text
meta.channel + pliki audio w katalogu kanalu
```

Nie powinien wymagac przebudowy `GhostRadio`, jesli zachowa `schema = 1` oraz
zasady `mode`, `sort` i `exclude`.
