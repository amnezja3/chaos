# .2 ? pozycje kanoniczne, propozycja do pierwszej pary

Status: DRAFT / DO AKCEPTACJI. To plan prezentacji, nie geometria ?wiata.

?r?d?o: TOPOLOGY_ANCHOR i PART_DEFINITIONS w ghostnetwork/catalog.py.
Para: [parts-pair.html](../../static/references/ghostsignal/parts-pair.html).
Wiersz,kolumna liczone od 1. Desktop 5?4, portrait 4?5.

| Indeks ringu | Kod | Nazwa | Desktop W,K | Portrait W,K | Maszyna / slot |
| --- | --- | --- | --- | --- | --- |
| 01 | V1 | Ledger Nexus | 1,1 | 1,1 | virex_oracle / 1 |
| 02 | S5 | Judgment Core | 1,2 | 1,2 | sentinel_aegis / 5 |
| 03 | E4 | Resonance Beacon | 1,3 | 1,3 | echo_libertas / 4 |
| 04 | P3 | Paranoia Loop | 1,4 | 1,4 | phantom_veil / 3 |
| 05 | V2 | Backdoor Forge | 1,5 | 2,1 | virex_oracle / 2 |
| 06 | E1 | Breach Voice | 2,1 | 2,2 | echo_libertas / 1 |
| 07 | S4 | Accord Relay | 2,2 | 2,3 | sentinel_aegis / 4 |
| 08 | P5 | Mirror Kernel | 2,3 | 2,4 | phantom_veil / 5 |
| 09 | V3 | Mimicry Engine | 2,4 | 3,1 | virex_oracle / 3 |
| 10 | S2 | Bastion Matrix | 2,5 | 3,2 | sentinel_aegis / 2 |
| 11 | E5 | Spark Chamber | 3,1 | 3,3 | echo_libertas / 5 |
| 12 | P1 | Mirage Projector | 3,2 | 3,4 | phantom_veil / 1 |
| 13 | V4 | Acquisition Drive | 3,3 | 4,1 | virex_oracle / 4 |
| 14 | E3 | Truth Lens | 3,4 | 4,2 | echo_libertas / 3 |
| 15 | S1 | Deep Sensor | 3,5 | 4,3 | sentinel_aegis / 1 |
| 16 | P4 | Fracture Engine | 4,1 | 4,4 | phantom_veil / 4 |
| 17 | V5 | Probability Core | 4,2 | 5,1 | virex_oracle / 5 |
| 18 | S3 | Restoration Engine | 4,3 | 5,2 | sentinel_aegis / 3 |
| 19 | E2 | Influence Relay | 4,4 | 5,3 | echo_libertas / 2 |
| 20 | P2 | Glitch Reactor | 4,5 | 5,4 | phantom_veil / 2 |

## Przej?cie mi?dzy stanami

- Cz??? ? w?ze?: pocz?tkowo ten sam ?rodek slotu; wygaszamy obraz cz??ci,
  ods?aniamy reprezentacj? w?z?a bez utraty kodu. To?samo?? nie zale?y od indeksu DOM.
- W?ze? ? ring: proponowany k?t to -90? + 18? ? indeks liczony od zera.
  P?ynne przej?cie ?rodka slotu do elipsy; reflow ustala osobne promienie
  dla obu format?w. Nie losujemy nowej topologii.
- Ring ? grupa: kod prowadzi do swojej maszyny i slotu 1?5 z katalogu.
  Kolejno?? maszyn: Virex Oracle, Echo Libertas, Phantom Veil, Sentinel Aegis.
  ?rodek grupy i docelowa pozycja hero zostan? rozpisane z kompozycjami .4;
  r??ne kompozycje korzystaj? z tego samego mapowania kod ? maszyna ? slot.
- Historia odkrycia zmienia kolejno?? ods?aniania, nie sta?e adresy slot?w.
- Seek/reconnect oblicza pozycj? z bie??cego czasu sceny, bez odtwarzania
  wcze?niejszych animacji; reduced motion pokazuje w?a?ciwy stan statyczny.

Para u?ywa katalogowego ringu, bez odczytu produkcji. W integracji .2/.3
uk?ad sieci i jej po??czenia musz? respektowa? zweryfikowany ring_codes
zamro?onego cyklu. Nie zast?pujemy brakuj?cej historii katalogowym faktem.
Brak historycznej topologii ma jawny fallback; nie dopisujemy po??cze?.

Nie implementowano jeszcze transformacji ani ca?ej grupy .2. Najpierw
akceptacja tej jednej pary desktop/portrait i propozycji pozycji.
