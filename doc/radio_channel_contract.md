# Ghost Hack Radio - Channel Contract

Ten dokument definiuje kontrakt `meta.channel` dla Ghost Hack Radio.

Sprint 53 przygotowuje format kanalow pod przyszly BlackNet, ale nie zaklada,
ze BlackNet istnieje juz fizycznie w runtime.

## Zasada glowna

`meta.channel` jest jedynym zrodlem prawdy dla playlisty kanalu.

Player:

* nie skanuje katalogu na slepo,
* nie zgaduje kolejnosci plikow,
* nie pobiera listy MP3 z backendu,
* buduje playliste wylacznie z `tracks[]`.

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
  "tracks": [
    {
      "title": "Ghost System",
      "file": "Ghost System.mp3"
    }
  ]
}
```

## Pola

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
| `tracks` | array | tak | Jawna playlista kanalu. |

## Tracks

Kazdy wpis `tracks[]` ma minimalnie:

| Pole | Typ | Wymagane | Znaczenie |
| --- | --- | --- | --- |
| `title` | string | tak | Tytul utworu w UI. |
| `file` | string | tak | Nazwa pliku MP3 w katalogu kanalu. |

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

Nie powinien wymagac przebudowy `GhostRadio`, jesli zachowa `schema = 1` i jawne
`tracks[]`.
