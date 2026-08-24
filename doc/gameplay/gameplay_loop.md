# CHAOS — Gameplay Loop

Ten dokument domyka Sprint 0 i opisuje pełną pętlę gameplayu.

CHAOS:

```text
Cyber Hacking Adventure Of Senses
```

Hasło:

```text
Hack the digital senses of the modern world.
Hakuj cyfrowe zmysły współczesnego świata.
```

Pełna pętla:

```text
World Object
↓
Map Action
↓
Application
↓
Operation
↓
Movement
↓
Resource
↓
File
↓
Ghost Exchange
↓
Mail
↓
HackCoins
↓
New Apps
↓
Back to Map
```

---

## 1. World Object

### Wejście

Gracz widzi obiekt świata na mapie.

Obiekt może pochodzić z:

* realnej mapy,
* skanu,
* podatności zgłoszonej przez gracza,
* konfliktu terytoriów,
* aktywnej operacji,
* innego gracza.

### Akcja gracza

Gracz klika obiekt, sprawdza menu albo wybiera interakcję.

### Akcja systemu

System rozpoznaje:

* `source_type`,
* `target_type`,
* `target_mode`,
* dostępne `map_action_id`.

### Rezultat

Obiekt dostaje menu kontekstowe zgodne z typem celu.

### Następny krok

`Map Action`.

---

## 2. Map Action

### Wejście

Gracz wybiera akcję z menu mapy.

Przykłady:

* `scan_ports`,
* `trace_gps`,
* `camera_stream`,
* `install_sniffer`,
* `mic_sniff`,
* `car_hack`.

### Akcja gracza

Kliknięcie akcji mapy.

### Akcja systemu

System sprawdza:

* czy akcja wymaga aplikacji,
* jakie aplikacje mają `app.map_actions`,
* czy target_type pasuje,
* czy akcja generuje risk signal.

### Rezultat

System wybiera aplikację automatycznie albo otwiera `/tools` z podświetleniem pasujących narzędzi.

Jeśli gracz nie ma aplikacji:

```text
Brak aplikacji obsługującej tę akcję.
```

### Następny krok

`Application`.

---

## 3. Application

### Wejście

Wybrana aplikacja z `/tools` albo automatycznie dopasowana aplikacja.

### Akcja gracza

Gracz uruchamia aplikację lub zatwierdza wybór narzędzia.

### Akcja systemu

System używa:

* `app.interface` do otwarcia UI,
* `app.map_actions` do potwierdzenia zgodności z akcją mapy,
* `app.operation_types` do uruchomienia procesu,
* `app.resource_types` do określenia możliwych wyników.

### Rezultat

Aplikacja wykonuje akcję natychmiastową albo tworzy instancję operacji.

### Następny krok

`Operation`.

---

## 4. Operation

### Wejście

Aplikacja tworzy instancję operacji.

Przykłady:

* `vehicle_tracking`,
* `device_tracking`,
* `camera_stream`,
* `persistent_sniffer`,
* `atm_log_extraction`.

### Akcja gracza

Gracz może obserwować, przerwać albo kontynuować operację, zależnie od kontraktu.

### Akcja systemu

System zapisuje:

* `operation_id`,
* `operation_type`,
* `owner_username`,
* `source_app_id`,
* `map_action_id`,
* `target_type`,
* `status`,
* `started_at`,
* `expires_at`,
* `risk_state`,
* `resource_buffer`.

### Rezultat

Operacja działa, kończy się natychmiast albo przechodzi w aktywny stan świata.

### Następny krok

`Movement`.

---

## 5. Movement

### Wejście

Operacja ma `movement_model` albo aktywny stan.

Przykłady:

* `road_movement`,
* `local_walk`,
* `carrier_movement`,
* `static_active_timer`,
* `implant_timer`.

### Akcja gracza

Gracz odświeża mapę, obserwuje aktywny obiekt albo wraca do operacji.

### Akcja systemu

System nie liczy świata co sekundę.

Stan jest wyliczany na podstawie:

* `started_at`,
* `last_updated_at`,
* `duration`,
* `operation_type`,
* `target_type`,
* `procedural_seed`,
* `movement_model`.

### Rezultat

Mapa pokazuje:

* marker ruchomego celu,
* licznik streamu,
* aktywny implant,
* timer zakłócenia,
* checkpointy, jeśli mają wartość gameplayową.

### Następny krok

`Resource`.

---

## 6. Resource

### Wejście

Operacja kończy się albo produkuje dane w czasie.

### Akcja gracza

Gracz czeka na wynik, kończy operację albo odbiera dane.

### Akcja systemu

System tworzy `resource_type`, jeśli aplikacja i operacja to deklarują.

Przykłady:

* `gps_logs`,
* `location_history`,
* `audio_transcript`,
* `camera_dump`,
* `financial_records`,
* `credentials`.

### Rezultat

Powstaje zasób:

* techniczny,
* plikowy,
* handlowy,
* wspierający,
* dowodowy.

### Następny krok

`File`.

---

## 7. File

### Wejście

Zasób jest widoczny dla gracza i powinien trafić do inventory.

### Akcja gracza

Gracz otwiera File Manager, ogląda dane, grupuje pliki, usuwa je albo przygotowuje do sprzedaży.

### Akcja systemu

System zapisuje plik w odpowiednim katalogu:

* `/data/gps`,
* `/data/device`,
* `/data/audio`,
* `/data/camera`,
* `/data/atm`,
* `/data/credentials`,
* `/data/financial`,
* `/data/personal`,
* `/data/network`,
* `/data/vehicle`.

### Rezultat

Plik staje się częścią gameplay inventory.

### Następny krok

`Ghost Exchange`.

---

## 8. Ghost Exchange

### Wejście

Gracz ma sprzedawalny plik.

### Akcja gracza

Gracz wystawia plik albo używa automatycznego skupu.

### Akcja systemu

Ghost Exchange:

* sprawdza kategorię rynku,
* sprawdza kompletność,
* liczy cenę,
* symuluje kupującego,
* tworzy sale flow.

### Rezultat

Plik przechodzi przez:

```text
stored → listed → sold
```

### Następny krok

`Mail`.

---

## 9. Mail

### Wejście

Sprzedaż została wykonana.

### Akcja gracza

Gracz odbiera powiadomienie w skrzynce.

### Akcja systemu

System wysyła wiadomość z:

* nazwą paczki,
* kategorią,
* ceną,
* typem kupującego,
* timestampem,
* statusem pliku po sprzedaży.

### Rezultat

Gracz ma potwierdzenie sprzedaży i informację o wyniku.

### Następny krok

`HackCoins`.

---

## 10. HackCoins

### Wejście

Sprzedaż danych zakończyła się sukcesem.

### Akcja gracza

Gracz widzi wzrost salda.

### Akcja systemu

System dodaje HC do profilu/walleta.

To nie jest zwykły przelew między graczami, tylko transakcja rynku danych.

### Rezultat

Gracz ma środki na rozwój.

### Następny krok

`New Apps`.

---

## 11. New Apps

### Wejście

Gracz ma HackCoins.

### Akcja gracza

Gracz kupuje aplikacje w Googleplex:

* narzędzia mapy,
* pro-system-tools,
* creatory,
* GhostLab,
* przyszłe aplikacje specjalistyczne.

### Akcja systemu

System sprawdza:

* cenę,
* wymagany level,
* wymagany respect,
* frakcję,
* dostępność aplikacji.

### Rezultat

Aplikacja trafia do:

* `profile.apps`,
* `/tools`,
* launchera,
* pulpitu.

### Następny krok

`Back to Map`.

---

## 12. Back to Map

### Wejście

Gracz ma nowe aplikacje i nowe możliwości.

### Akcja gracza

Gracz wraca na mapę.

### Akcja systemu

Mapa pokazuje:

* obiekty świata,
* targety,
* aktywne operacje,
* konflikty,
* graczy,
* zasięg,
* nowe możliwe akcje.

### Rezultat

Gracz może wykonywać trudniejsze, cenniejsze lub bardziej ryzykowne działania.

### Następny krok

Pętla wraca do `World Object`.

---

## Risk jako warstwa przekrojowa

Ryzyko nie jest osobnym krokiem pętli, ale warstwą przekrojową.

Może pojawić się przy:

* `Map Action`,
* `Application`,
* `Operation`,
* `Movement`,
* `Resource`,
* `Ghost Exchange`.

Risk pipeline:

```text
Action → Risk signal → Risk score → Risk event → Consequence
```

Decision:

* Przyjęto: ryzyko nie przerywa pętli domyślnie, tylko może zmienić jej wynik, koszt albo tempo.

---

## Definition of Done Gameplay Loop

Gameplay loop jest kompletny, gdy:

* każdy krok ma wejście,
* każdy krok ma akcję gracza,
* każdy krok ma akcję systemu,
* każdy krok ma rezultat,
* każdy krok ma następny krok,
* pętla wraca do mapy przez zakup nowych aplikacji.
