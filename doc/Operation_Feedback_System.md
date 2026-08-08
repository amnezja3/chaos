# Operation Feedback System

## Cel

Zastąpić wszystkie obecne „czarne dziury” podczas oczekiwania na odpowiedź backendu dynamicznym systemem prezentacji operacji.

Frontend podczas oczekiwania nie pokazuje spinnera ani jednego powtarzalnego zestawu logów.

Zamiast tego uruchamia lokalną narrację operacji złożoną z:

* krótkich scen,
* logów,
* reakcji zabezpieczeń,
* operacji technicznych,
* retry/reconnect,
* komunikatów serwisowych,
* pytań do operatora w aplikacjach `button_choice`,
* timeoutów,
* przejść między scenami,
* końcowego `payload received`.

Animacja istnieje tylko do momentu nadejścia prawdziwej odpowiedzi backendu.

Backend pozostaje źródłem prawdy.

---

# 1. Obsługiwane operacje

System obejmuje 12 operacji CHAOS:

### Główne operacje hackowania

1. `scan_ports`
2. `exploit`
3. `sniff`
4. `trace`

### Operacje specjalistyczne

5. `trace_gps`
6. `trace_device`
7. `mic_sniff`
8. `atm_logs`
9. `install_sniffer`
10. `camera_stream`
11. `camera_shutdown`
12. `car_hack`

Każda operacja posiada osobny profil.

Nie wolno używać scen `sniff` jako wypełnienia dla `scan_ports`, scen samochodowych dla kamer itd.

Wspólne mogą być wyłącznie zdarzenia techniczne typu reconnect, timeout, retry, handshake i synchronizacja.

---

# 2. Typ prezentacji aplikacji

Każde uruchomienie otrzymuje `presentation_mode`.

## `terminal`

Aplikacja zachowuje się jak terminal.

Pokazuje krótkie sekwencje 3–6 linii.

Po zakończeniu sceny ekran jest czyszczony lub zastępowany następną sceną.

Nie powstaje nieskończony scroll logów.

Brak pytań wymagających reakcji użytkownika.

Przykładowe zastosowanie:

* `exploit`
* `sniff`
* `mic_sniff`
* `atm_logs`

---

## `button_choice`

Logi są przeplatane interakcjami z graczem.

Schemat:

logi → zdarzenie → pytanie → countdown → decyzja/default → reakcja → czyszczenie → kolejna scena.

Przykładowe zastosowanie:

* `scan_ports`
* `install_sniffer`
* `camera_shutdown`
* `car_hack`

Pytanie nigdy nie może zatrzymać operacji.

Po wygaśnięciu czasu automatycznie stosowana jest odpowiedź domyślna.

---

## `window`

Operacja prezentowana bardziej jako aktywny moduł systemowy.

Może pokazywać:

* status kanału,
* wykryte urządzenia,
* aktywne moduły,
* zmiany routingu,
* analizowane źródła,
* stan sygnału,
* krótkie komunikaty,
* pulsujące wskaźniki,
* przełączanie kolejnych etapów.

Przykładowe zastosowanie:

* `trace`
* `trace_gps`
* `trace_device`
* `camera_stream`

Nie należy używać klasycznego paska `0–100%`, jeżeli frontend nie zna prawdziwego postępu backendu.

Można pokazywać aktywność, etap lub intensywność, ale nie fałszywy procent wykonania.

---

# 3. Profil operacji

Każda operacja w JSON-ie posiada:

`action_key`

Jednoznaczny klucz operacji.

`presentation_modes`

Dozwolone sposoby prezentacji.

`default_presentation_mode`

Domyślna prezentacja.

`security_keys`

Zabezpieczenia związane z operacją.

`security_effects`

Rodzaj oddziaływania operacji na zabezpieczenia.

`scene_pools`

Dostępne rodziny scen.

`choice_pools`

Pytania operatora, jeżeli aplikacja obsługuje wybory.

`service_event_pools`

Ogólne wydarzenia techniczne.

`duration_profiles`

Sposób składania scen zależnie od przewidywanego czasu.

`completion_pool`

Warianty przejścia do prawdziwego payloadu.

---

# 4. Zabezpieczenia

System korzysta z istniejących parametrów:

`stealth_mode`
`scan_detection`
`exploit_protection`
`vpn_enabled`
`browser_protection`
`os_hardening`
`log_guardian`
`process_monitor`
`firewall`
`log_integrity`
`network_anomaly_detection`
`spoofing_protection`
`activity_monitor`
`player_tracking`
`system_visibility`
`firewall_core`
`kernel_guard`
`system_integrity_check`
`heap_protection`
`memory_lock`
`background_injection`
`memory_guard`
`vpn_blocker`

Jedno zabezpieczenie może należeć do kilku operacji.

Operacja nie może jednak generować przypadkowego zabezpieczenia spoza swojej grupy.

---

# 5. Mapowanie operacji na zabezpieczenia

## `scan_ports`

Główne:

`scan_detection`
`firewall`
`firewall_core`
`system_visibility`
`network_anomaly_detection`
`vpn_blocker`

Efekty narracyjne:

`probe`
`detect`
`enumerate`
`bypass`
`route`

Narracja dotyczy portów, filtrowania, sond, odpowiedzi usług, fingerprintingu i reakcji sieci.

---

## `exploit`

Główne:

`exploit_protection`
`os_hardening`
`kernel_guard`
`system_integrity_check`
`heap_protection`
`memory_lock`
`background_injection`
`memory_guard`

Pomocnicze:

`process_monitor`
`firewall_core`

Efekty:

`probe`
`bypass`
`inject`
`allocate`
`execute`
`verify`

Narracja dotyczy pamięci, procesów, kernela, injekcji, payloadu i integralności systemu.

---

## `sniff`

Główne:

`vpn_enabled`
`network_anomaly_detection`
`spoofing_protection`
`activity_monitor`
`system_visibility`

Pomocnicze:

`browser_protection`
`log_guardian`
`stealth_mode`

Efekty:

`intercept`
`capture`
`decode`
`filter`
`mask`

Narracja dotyczy pakietów, ramek, kanałów, ruchu sieciowego i filtrowania danych.

---

## `trace`

Główne:

`stealth_mode`
`player_tracking`
`activity_monitor`
`system_visibility`
`spoofing_protection`

Pomocnicze:

`vpn_enabled`
`log_guardian`
`log_integrity`

Efekty:

`locate`
`correlate`
`follow`
`resolve`
`reconstruct`

Narracja dotyczy śladów, sesji, źródeł, tras i korelacji aktywności.

---

## `trace_gps`

Główne:

`player_tracking`
`system_visibility`
`spoofing_protection`
`activity_monitor`

Pomocnicze:

`vpn_enabled`
`network_anomaly_detection`

Efekty:

`locate`
`triangulate`
`correlate`
`resolve`

Narracja dotyczy telemetrii, pozycji, próbek GPS i rekonstrukcji trasy.

---

## `trace_device`

Główne:

`player_tracking`
`system_visibility`
`activity_monitor`
`spoofing_protection`

Pomocnicze:

`browser_protection`
`vpn_enabled`

Efekty:

`identify`
`fingerprint`
`correlate`
`resolve`

Narracja dotyczy identyfikacji urządzenia, fingerprintu, sesji i jego aktywności.

---

## `mic_sniff`

Główne:

`browser_protection`
`activity_monitor`
`process_monitor`
`system_visibility`

Pomocnicze:

`log_guardian`
`vpn_enabled`

Efekty:

`capture`
`open_channel`
`decode`
`filter`

Narracja dotyczy wejścia audio, procesu urządzenia, strumienia i kanału transmisji.

---

## `atm_logs`

Główne:

`log_guardian`
`log_integrity`
`system_integrity_check`
`activity_monitor`

Pomocnicze:

`process_monitor`
`os_hardening`

Efekty:

`read`
`extract`
`verify`
`reconstruct`

Narracja dotyczy logów ATM, historii operacji, bloków danych i weryfikacji integralności.

---

## `install_sniffer`

Główne:

`process_monitor`
`background_injection`
`memory_guard`
`memory_lock`

Pomocnicze:

`os_hardening`
`exploit_protection`
`network_anomaly_detection`

Efekty:

`inject`
`persist`
`hide`
`attach`
`verify`

Narracja dotyczy osadzania procesu sniffera, pamięci i utrzymania procesu w systemie ATM.

---

## `camera_stream`

Główne:

`firewall`
`firewall_core`
`system_visibility`
`activity_monitor`

Pomocnicze:

`vpn_blocker`
`process_monitor`

Efekty:

`connect`
`negotiate`
`decode`
`stream`

Narracja dotyczy połączenia z kamerą, kodeka, strumienia, kanału i transmisji obrazu.

---

## `camera_shutdown`

Główne:

`system_integrity_check`
`process_monitor`
`os_hardening`
`kernel_guard`

Pomocnicze:

`firewall_core`
`log_guardian`

Efekty:

`interrupt`
`override`
`terminate`
`verify`

Narracja dotyczy zatrzymania procesu kamery, kontrolera urządzenia i odcięcia streamu.

---

## `car_hack`

Główne:

`exploit_protection`
`system_integrity_check`
`kernel_guard`
`memory_guard`
`process_monitor`

Pomocnicze:

`firewall`
`spoofing_protection`
`network_anomaly_detection`

Efekty:

`connect`
`inject`
`override`
`control`
`verify`

Narracja dotyczy magistrali pojazdu, ECU, systemu pokładowego, sterowników i przejęcia sesji.

---

# 6. Security Event Library

Każdy `security_key` posiada własną bibliotekę mikrozdarzeń.

Nie przechowujemy jedynie gotowych logów operacji.

Przykład logiczny dla `firewall`:

* wykrycie filtracji,
* sprawdzenie reguł,
* zamknięty kanał,
* alternatywna ścieżka,
* ponowienie sondy,
* przejście innym portem.

Dla `memory_guard`:

* odmowa zapisu,
* zmiana obszaru pamięci,
* ponowna alokacja,
* zmiana offsetu,
* izolacja regionu,
* druga próba injekcji.

Dzięki temu operacja składa swoją narrację z właściwych zabezpieczeń.

---

# 7. Scene System

Podstawową jednostką nie jest linia logu.

Podstawową jednostką jest `scene`.

Typowa scena:

`enter`

krótkie wejście.

`activity`

2–5 zdarzeń związanych z aktualną operacją.

`security_event`

opcjonalna reakcja jednego z zabezpieczeń.

`service_event`

opcjonalny problem infrastrukturalny.

`choice`

opcjonalna decyzja użytkownika.

`resolution`

wynik lokalnej sceny.

`transition`

przejście dalej.

`clear`

wyczyszczenie ekranu przed kolejną sceną.

---

# 8. Rodziny scen

System powinien posiadać przynajmniej:

`boot`

Rozpoczęcie konkretnej operacji.

`probe`

Pierwszy kontakt z elementem systemu.

`security_contact`

Reakcja zabezpieczenia.

`processing`

Normalna praca aplikacji.

`operator_choice`

Decyzja operatora.

`retry`

Ponowienie operacji.

`reconnect`

Odbudowanie połączenia.

`fallback`

Zmiana sposobu wykonania operacji.

`verification`

Sprawdzenie rezultatu etapu.

`payload_wait`

Backend jeszcze nie odpowiedział.

`extended_wait`

Przekroczono przewidywany czas.

`completion`

Payload został odebrany.

`recovery`

Frontend wykrył problem komunikacyjny, ale nadal oczekuje.

---

# 9. Biblioteka zdarzeń wspólnych

Zdarzenia ogólne mogą być współdzielone między wszystkimi operacjami:

`handshake`

`reconnect`

`retry`

`timeout`

`route_change`

`channel_switch`

`session_rebuild`

`process_restart`

`fallback`

`response_pending`

`payload_wait`

`verification`

`sync`

`remote_busy`

`packet_loss`

`delayed_response`

`source_of_truth_sync`

Ich tekst powinien zostać przepisany stylistycznie pod CHAOS/GhostSystem, a nie wyglądać jak komunikaty zwykłej aplikacji webowej.

---

# 10. Profile czasu

Czas nie określa długości jednej animacji.

Określa liczbę i gęstość scen.

## `instant`

0–4 s

1 krótka scena.

2–4 komunikaty.

Bez obowiązkowego pytania.

---

## `short`

4–15 s

1–2 sceny.

3–6 komunikatów na scenę.

Maksymalnie jedno szybkie pytanie.

---

## `medium`

15–40 s

2–4 sceny.

Możliwa jedna interakcja.

Możliwy retry albo security event.

---

## `long`

40–90 s

4–7 scen.

1–3 interakcje.

Więcej zmian kontekstu.

Retry/reconnect/fallback może pojawiać się naturalnie.

---

## `very_long`

90–180+ s

6–10 scen.

2–4 interakcje w `button_choice`.

Kilka zabezpieczeń.

Co najmniej jedno zdarzenie techniczne.

Możliwa scena `extended_wait`.

Operacja nie może wyglądać jak jedna animacja rozciągnięta do dwóch minut.

Powinna przypominać serię kolejnych działań systemu.

---

# 11. Scheduler

Scheduler otrzymuje:

`action_key`

`presentation_mode`

`expected_duration`

`security_state`

oraz identyfikator bieżącej operacji.

Na tej podstawie wybiera plan scen.

Plan nie musi mieć z góry ustalonej końcówki.

Jeżeli backend odpowie wcześniej, scheduler natychmiast przechodzi do `completion`.

Jeżeli backend odpowie później niż przewidywano, scheduler nie zatrzymuje się.

Przechodzi do puli:

`payload_wait`

`reconnect`

`verification`

`extended_wait`

i może z nich tworzyć kolejne sceny aż do prawdziwej odpowiedzi.

---

# 12. Button Choice

Pytania istnieją wyłącznie tam, gdzie `presentation_mode = button_choice`.

Typowe zestawy odpowiedzi:

`TAK / NIE`

`ZEZWÓL / ODMÓW`

`PONÓW / POMIŃ`

`MASKUJ / KONTYNUUJ`

`IZOLUJ / IGNORUJ`

`TRYB CICHY / TRYB SZYBKI`

`KANAŁ A / KANAŁ B`

Każdy wybór definiuje:

`prompt`

Treść.

`options`

Dostępne przyciski.

`timeout`

Przeważnie 6–12 sekund.

`default_option`

Opcja wybrana automatycznie.

`selected_response`

Komunikat po kliknięciu.

`timeout_response`

Komunikat po braku reakcji.

`effect_scope`

Domyślnie:

`presentation`

Oznacza to, że wybór wpływa na dalszą narrację, ale nie zmienia prawdziwego gameplayu.

W przyszłości można dopuścić:

`gameplay`

ale wyłącznie dla decyzji posiadających prawdziwy kontrakt backendowy.

---

# 13. Timeout operatora

Brak odpowiedzi użytkownika nie zatrzymuje sceny.

Przykład przebiegu:

`10`

`9`

`8`

...

`1`

następnie:

`operator timeout`

`standard profile selected`

krótka pauza,

`clear`

następna scena.

Frontend nigdy nie czeka bezterminowo na kliknięcie.

---

# 14. Przerwanie pytania przez payload

Jeżeli prawdziwa odpowiedź backendu pojawi się podczas countdownu:

* countdown zostaje anulowany,
* przyciski są blokowane,
* aktualna scena dostaje status zakończenia,
* wykonywana jest scena `completion`,
* publikowany jest prawdziwy wynik.

Nie czekamy, aż użytkownik odpowie na pytanie narracyjne.

---

# 15. Randomizacja

Każda rodzina scen powinna posiadać minimum kilka wariantów.

Docelowo:

5–8 wariantów wejścia,

5–10 wariantów security event,

5–8 wariantów service event,

5–8 wariantów transition,

5–8 wariantów completion,

kilka pytań dla każdego właściwego zabezpieczenia.

Randomizacja działa warstwowo.

Najpierw wybierana jest scena.

Potem zabezpieczenie.

Potem zdarzenie.

Potem wariant tekstu.

Potem timing.

Nie losujemy wszystkich linii niezależnie, bo powstałby chaos semantyczny.

---

# 16. Anti-repeat

System pamięta kilka ostatnio wykorzystanych:

* scen,
* pytań,
* komunikatów,
* security events.

Nie powinien wybierać tego samego wariantu w dwóch kolejnych uruchomieniach tej samej operacji, jeżeli dostępna jest alternatywa.

Dzięki temu ponowne `scan_ports` na drugim obiekcie nie wygląda identycznie.

---

# 17. Security-aware narrative

Jeżeli frontend zna aktualny stan zabezpieczenia, może używać go do wyboru narracji.

Przykład:

aktywny `firewall`

→ firewall odpowiada na sondę.

brak `firewall`

→ scena związana z firewallem nie jest wybierana.

Nie wolno jednak lokalnie stwierdzić:

`FIREWALL DISABLED`

jeżeli backend jeszcze tego nie potwierdził.

Podczas oczekiwania można używać określeń:

`bypass attempt`

`rule probe`

`alternate route`

`temporary channel`

`verification pending`

Dopiero prawdziwy payload może potwierdzić zmianę stanu.

---

# 18. Oddziaływanie operacji na zabezpieczenia

Każda relacja:

`operation → security_key`

powinna dodatkowo określać `interaction_type`.

Dozwolone typy bazowe:

`probe`

`read`

`detect`

`identify`

`intercept`

`capture`

`locate`

`correlate`

`bypass`

`inject`

`override`

`interrupt`

`terminate`

`hide`

`persist`

`verify`

`control`

`decode`

`stream`

Dzięki temu ten sam `process_monitor` może zachowywać się inaczej podczas `exploit`, inaczej podczas `camera_shutdown`, a jeszcze inaczej podczas `install_sniffer`.

---

# 19. Stary boot aplikacji

Obecny boot/log loader nie może pozostawać jako osobna faza oczekiwania.

Po rozpoczęciu operacji aktualny viewport aplikacji zostaje przejęty przez Operation Feedback System.

Pierwsza scena systemu pełni rolę bootu operacji.

Może być za każdym razem inna.

Przykładowo `scan_ports` może rozpocząć się od:

inicjalizacji interfejsu,

handshake,

sprawdzenia celu,

enumeracji adaptera,

weryfikacji routingu,

albo szybkiej sondy.

Dzięki temu użytkownik nie widzi za każdym razem tego samego początku.

---

# 20. Zachowanie terminala

Terminal nie powinien produkować kilometrowego logu.

Preferowany rytm:

3–6 linii,

krótka reakcja,

zmiana stanu,

clear/fade,

nowa scena.

Ma wyglądać jak kolejne ekrany działającego narzędzia, a nie `console.log()` lecący bez końca.

---

# 21. Zachowanie window

Widok okienkowy powinien pokazywać zmianę informacji.

Przykładowo podczas `trace_gps`:

źródła sygnału,

liczbę aktywnych próbek,

zmianę kanału,

status korelacji,

kolejny sektor,

utratę źródła,

ponowną synchronizację.

Elementy mogą znikać i być zastępowane kolejnymi, podobnie jak sceny terminalowe.

---

# 22. Completion

Każda operacja posiada kilka wariantów krótkiego zakończenia.

Nie należy od razu brutalnie zamieniać animacji na odpowiedź serwera.

Najpierw 300–1000 ms wizualnego potwierdzenia:

`PAYLOAD RECEIVED`

`REMOTE RESPONSE`

`STATE CONFIRMED`

`RESULT CHANNEL OPEN`

`SOURCE OF TRUTH UPDATED`

następnie wynik backendu pojawia się dokładnie w obecnym miejscu aplikacji.

Completion nie zmienia ani nie interpretuje wyniku.

Jest wyłącznie przejściem wizualnym.

---

# 23. Failure

Prawdziwy błąd backendu również przerywa feedback.

System może wyświetlić krótkie zakończenie:

`REMOTE OPERATION FAILED`

`PAYLOAD REJECTED`

`SESSION CLOSED`

ale właściwy komunikat błędu nadal pochodzi z backendu.

Animacja nie może maskować rzeczywistego błędu.

---

# 24. Najważniejsza granica architektoniczna

Operation Feedback System:

**nie oblicza gameplayu,**

**nie decyduje o powodzeniu hacku,**

**nie zmienia zabezpieczeń,**

**nie zapisuje stanu celu,**

**nie symuluje odpowiedzi backendu.**

Jego zadaniem jest tylko prezentacja oczekiwania.

Backend jest jedynym źródłem prawdy.

---

# 25. Docelowa struktura JSON

Na najwyższym poziomie:

`version`

`global`

`security_library`

`service_library`

`operations`

`duration_profiles`

`completion_library`

`failure_library`

W `operations` znajduje się 12 profili.

Każdy profil zawiera:

`action_key`

`presentation`

`security`

`scene_pools`

`choice_pools`

`timing`

`completion`

---

# 26. Minimalna struktura pojedynczej sceny

Scena powinna umieć określić:

`id`

`type`

`weight`

`min_duration`

`max_duration`

`security_keys`

`interaction_types`

`lines`

`events`

`choice`

`transition`

`clear_mode`

Nie każda scena musi zawierać wszystkie pola.

Renderer interpretuje istniejące elementy.

---

# 27. Clear modes

Scena może zakończyć się:

`replace`

Natychmiastowa podmiana zawartości.

`clear`

Wyczyszczenie viewportu.

`fade`

Krótki fade poprzedniej sceny.

`keep_header`

Czyści zawartość, ale pozostawia status operacji.

`append_short`

Pozwala pozostawić kilka ostatnich komunikatów.

Domyślnie preferowane są `replace`, `clear` i `fade`.

---

# 28. Timing

JSON nie powinien zawierać jednej sztywnej sekwencji czasowej.

Element może posiadać zakres:

`min_delay`

`max_delay`

Dzięki temu trzy komunikaty nie pojawiają się zawsze:

0.5 s
0.5 s
0.5 s

ale np.:

0.4 s
1.1 s
0.7 s

Zmienia się również długość pauzy przed pytaniem i po odpowiedzi.

Animacja wygląda dzięki temu bardziej organicznie.

---

# 29. Finalny model działania

Klik użytkownika rozpoczyna prawdziwy request.

Równocześnie frontend uruchamia:

`Operation Feedback Session`.

Session pobiera profil `action_key`.

Dobiera typ prezentacji.

Sprawdza zabezpieczenia celu.

Dobiera profil czasowy.

Losuje pierwsze sceny.

Renderer prezentuje je użytkownikowi.

Scheduler produkuje następne sceny.

Użytkownik może odpowiadać na pytania.

Brak odpowiedzi powoduje default.

Backend odpowiada.

Feedback Session natychmiast otrzymuje sygnał końca.

Bieżąca scena jest domykana.

Pokazywany jest krótki `completion`.

Następnie aplikacja publikuje prawdziwy wynik dokładnie tak jak obecnie.

---

# 30. Definition of Done

Sprint można uznać za zamknięty, kiedy:

1. wszystkie 12 `action_key` posiada własny profil,
2. wszystkie 23 security keys są dostępne w security library,
3. operacje odwołują się tylko do właściwych grup zabezpieczeń,
4. istnieją trzy renderery: `terminal`, `button_choice`, `window`,
5. długość animacji dostosowuje się do czasu oczekiwania,
6. sceny mogą być dowolnie przerwane nadejściem payloadu,
7. button choice posiada timeout i default,
8. brak kliknięcia nigdy nie zatrzymuje requestu,
9. obecny boot zostaje zastąpiony pierwszą sceną Operation Feedback,
10. nie powstaje nieskończony scroll logów,
11. kolejne uruchomienia tej samej operacji mieszają warianty,
12. `scan_ports` nie może dostać narracji `sniff`, `trace`, kamery lub samochodu,
13. zabezpieczenia wpływają na wybór scen,
14. frontend nie deklaruje zmiany stanu zabezpieczenia przed odpowiedzią backendu,
15. prawdziwy payload zawsze ma pierwszeństwo przed animacją,
16. istnieje pula `extended_wait`, dzięki której nie powstaje nowa czarna dziura po przekroczeniu oczekiwanego czasu,
17. błędy backendu nie są ukrywane przez animację,
18. system umożliwia dodanie kolejnej operacji przez nowy profil JSON bez pisania osobnego loadera.

## Efekt końcowy

Gracz nie czeka już na backend.

Z jego punktu widzenia aplikacja przez cały czas **pracuje**.

120 sekund przestaje być 120 sekundami spinnera.

Staje się serią krótkich operacji:

kontakt z systemem → analiza → zabezpieczenie → decyzja → retry → kolejny moduł → problem z kanałem → reconnect → analiza → payload.

Każda aplikacja zachowuje przy tym własny charakter i własną ścieżkę techniczną.

---

Jasne — zanim cokolwiek kodować, najlepiej ustalić sam „język” tego systemu, czyli co opisujemy w słowniku, co ma być wspólne, a co specyficzne dla konkretnej operacji, bo od tego zależy później, czy to będzie elastyczne, czy szybko zamieni się w potwora.

Ja bym zaczął od bardzo prostego założenia: **nie robimy jednego wielkiego drzewa z gotowymi animacjami**, tylko kilka małych bibliotek, które potem operation profile składa ze sobą.

Na przykład mentalnie widzę to tak:

```js
const OPERATION_FEEDBACK = {
    operations: {},
    security: {},
    scenes: {},
    choices: {},
    service_events: {}
};
```

Ten blok nic jeszcze nie „robi” — to tylko podział odpowiedzialności: `operations` mówi, z czego dana akcja może korzystać, `security` opisuje konkretne zabezpieczenia, `scenes` trzyma typowe kawałki przebiegu, `choices` interakcje z graczem, a `service_events` rzeczy wspólne typu reconnect/retry/timeout.

I teraz najważniejsze: `operation` nie powinna mieć 50 tekstów. Powinna być raczej **receptą**.

Np.:

```js
operations: {
    scan_ports: {
        presentation: "button_choice",

        security: [
            "scan_detection",
            "firewall",
            "firewall_core",
            "network_anomaly_detection"
        ],

        scene_types: [
            "probe",
            "security_response",
            "enumeration",
            "verification"
        ],

        choices: [
            "scan_visibility",
            "retry_probe",
            "change_scan_mode"
        ]
    }
}
```

Czyli ten blok mówi frontendowi: „dla `scan_ports` używaj interfejsu z przyciskami, możesz gadać o tych czterech zabezpieczeniach, sceny powinny pochodzić z tych rodzin, a pytania tylko z tych trzech grup”; samych zdań tutaj nie ma, więc profil operacji pozostaje mały i czytelny.

Natomiast osobno mamy zabezpieczenie:

```js
security: {
    firewall: {
        tags: ["network", "filtering"],

        events: {
            probe: [
                "filter response detected",
                "checking active filtering rules",
                "remote filtering layer responded"
            ],

            bypass: [
                "testing alternate route",
                "switching probe channel",
                "rebuilding packet sequence"
            ]
        }
    }
}
```

Tu zaczyna się fajna rzecz: `firewall` ma własny charakter niezależnie od aplikacji. Jeśli za pół roku powstanie nowa operacja, która również dotyka firewalla, może użyć tej biblioteki bez kopiowania tekstów.

Ale zrobiłbym jeszcze jeden poziom, bo inaczej po chwili zaczną nam się mieszać konteksty.

Nie wystarczy powiedzieć:

`scan_ports → firewall`

Lepiej powiedzieć:

```js
security: {
    firewall: {
        interactions: {
            scan_ports: ["probe", "enumerate"],
            exploit: ["bypass", "verify"],
            camera_stream: ["connect", "route"]
        }
    }
}
```

Ten kawałek ogranicza zachowanie tego samego zabezpieczenia zależnie od operacji: skan portów tylko sonduje firewall, exploit próbuje go ominąć, a kamera traktuje go jako przeszkodę w zestawieniu połączenia; dzięki temu nie dostaniemy tekstu o „memory injection” przy skanowaniu portów tylko dlatego, że wszystko leży pod wspólnym `firewall`.

Sceny potraktowałbym jako coś jeszcze bardziej abstrakcyjnego:

```js
scenes: {
    probe: {
        lines: [2, 4],
        duration: [2, 5],
        allow_security_event: true,
        allow_service_event: true,
        allow_choice: false
    },

    security_response: {
        lines: [2, 3],
        duration: [3, 7],
        allow_security_event: true,
        allow_service_event: false,
        allow_choice: true
    },

    verification: {
        lines: [2, 4],
        duration: [2, 6],
        allow_choice: false
    }
}
```

Ten fragment opisuje nie treść, tylko **rytm ekranu**: ile mniej więcej komunikatów ma pokazać scena, ile może trwać i czy może w niej pojawić się reakcja zabezpieczenia, błąd techniczny albo pytanie; to bym chciał trzymać całkowicie niezależnie od tekstów.

I wtedy wybory:

```js
choices: {
    scan_visibility: {
        prompt: [
            "Scan detection increased. Reduce probe visibility?",
            "Remote system is reacting to probes. Switch to masked mode?"
        ],

        options: [
            {
                label: "MASKUJ",
                result: "masked"
            },
            {
                label: "KONTYNUUJ",
                result: "continue"
            }
        ],

        timeout: [7, 11],
        default: "continue"
    }
}
```

Ten blok definiuje gotową mikrointerakcję: losuje pytanie, pokazuje przyciski, ma zakres czasu na decyzję i wie, co wybrać po timeout; na razie `result` może wpływać tylko na dalszą animację, a nie na backend.

I dopiero service events dałbym jako najbardziej „wspólny worek”:

```js
service_events: {
    reconnect: [
        "runtime channel lost",
        "rebuilding remote session",
        "restoring operation stream"
    ],

    retry: [
        "probe rejected // retry",
        "remote response incomplete",
        "repeating current stage"
    ],

    delayed: [
        "remote process still active",
        "waiting for operation receipt",
        "response channel pending"
    ]
}
```

To są komunikaty techniczne, które mogą wejść praktycznie wszędzie i zamaskować szczególnie te momenty, gdy backend trwa dłużej niż zakładaliśmy.

Dla mnie kluczowe pytanie projektowe teraz brzmi trochę inaczej niż „jakie pola ma mieć JSON”: **kto ma składać historię?**

Widzę dwie możliwości.

Pierwsza: JSON zawiera prawie gotowe sceny:

`scene A → scene B → choice → scene C`

To jest łatwe, ale szybko stanie się powtarzalne.

Druga — i tę bym wybrał — JSON dostarcza **klocki i ograniczenia**, a JS układa przebieg na żywo:

`operation mówi, czego wolno użyć → scheduler wybiera scenę → scena wybiera security → security wybiera właściwy event → czasem wpada service event → czasem choice`.

Wtedy jeden `scan_ports` może za każdym razem wyglądać naprawdę inaczej, a jednocześnie nadal będzie semantycznie poprawny.

Na przykład jedno uruchomienie:

```text
probe
→ firewall
→ enumeration
→ choice
→ verification
```

Drugie:

```text
probe
→ scan_detection
→ retry
→ probe
→ network_anomaly_detection
→ verification
```

Trzecie:

```text
enumeration
→ firewall_core
→ choice
→ reconnect
→ verification
```

I wszystkie trzy nadal są ewidentnie `scan_ports`.

Ja bym więc na tym etapie nawet nie rozpisywał jeszcze całych 12 akcji. Najpierw zrobiłbym sobie **jeden eksperymentalny `scan_ports`** z 3–4 zabezpieczeniami, 4 typami scen i 3 pytaniami i zobaczył na papierze, czy z tej struktury da się ułożyć 10 sensownych różnych przebiegów bez pisania 10 gotowych animacji.

Bo jeśli to zadziała dla `scan_ports`, wtedy dopiero warto powielać model na pozostałe 11 operacji.

Pewnie — zrobiłbym to na początek jako mały, czytelny prototyp: słownik z danymi + prosty scheduler scen + renderer, bez żadnego spięcia z backendem.

Ten blok to przykładowy słownik dla jednej operacji `scan_ports`; opisuje tylko, z jakich zabezpieczeń, scen, pytań i eventów technicznych wolno jej korzystać.

```js
const OPERATION_FEEDBACK = {
    operations: {
        scan_ports: {
            presentation: "button_choice",

            security: [
                "scan_detection",
                "firewall",
                "firewall_core",
                "network_anomaly_detection"
            ],

            scenes: [
                "probe",
                "security_response",
                "enumeration",
                "verification"
            ],

            choices: [
                "scan_visibility",
                "retry_probe",
                "scan_mode"
            ]
        }
    },

    security: {
        scan_detection: {
            probe: [
                "remote scan detector responded",
                "probe signature detected by target",
                "target is monitoring incoming probes"
            ],

            evade: [
                "reducing probe frequency",
                "randomizing packet interval",
                "switching to low visibility scan"
            ]
        },

        firewall: {
            probe: [
                "filter response detected",
                "checking firewall rules",
                "remote filtering layer responded"
            ],

            bypass: [
                "testing alternate route",
                "switching probe channel",
                "rebuilding packet sequence"
            ]
        },

        firewall_core: {
            probe: [
                "firewall core handshake rejected",
                "core filtering layer detected",
                "probing firewall control channel"
            ]
        },

        network_anomaly_detection: {
            probe: [
                "traffic anomaly detector active",
                "probe pattern classified as unusual",
                "network behavior monitor responded"
            ]
        }
    },

    scenes: {
        probe: {
            minLines: 2,
            maxLines: 4,
            duration: [1500, 4000],
            allowSecurity: true,
            allowChoice: false
        },

        security_response: {
            minLines: 2,
            maxLines: 3,
            duration: [2000, 5000],
            allowSecurity: true,
            allowChoice: true
        },

        enumeration: {
            minLines: 3,
            maxLines: 5,
            duration: [2000, 5000],
            allowSecurity: false,
            allowChoice: false
        },

        verification: {
            minLines: 2,
            maxLines: 4,
            duration: [1500, 3500],
            allowSecurity: true,
            allowChoice: false
        }
    },

    choices: {
        scan_visibility: {
            prompts: [
                "Scan visibility increased. Enable masked probing?",
                "Target reacted to scan. Reduce probe visibility?"
            ],

            options: [
                { label: "MASKUJ", value: "masked" },
                { label: "KONTYNUUJ", value: "continue" }
            ],

            timeout: 8000,
            default: "continue"
        },

        retry_probe: {
            prompts: [
                "Remote probe rejected. Retry with alternate sequence?"
            ],

            options: [
                { label: "PONÓW", value: "retry" },
                { label: "POMIŃ", value: "skip" }
            ],

            timeout: 7000,
            default: "retry"
        }
    },

    serviceEvents: {
        reconnect: [
            "connection=false // rebuilding channel",
            "remote session interrupted",
            "restoring operation stream"
        ],

        retry: [
            "probe rejected // retry",
            "response incomplete // repeating stage",
            "retrying remote request"
        ],

        waiting: [
            "waiting for operation receipt",
            "remote process still active",
            "payload response pending"
        ]
    }
};
```

Tutaj są tylko małe helpery do losowania; dzięki nim późniejszy scheduler nie musi wiedzieć, ile dokładnie wariantów tekstu znajduje się w danej tablicy.

```js
function randomItem(array) {
    return array[Math.floor(Math.random() * array.length)];
}

function randomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
```

A teraz najważniejszy kawałek: przykładowa sesja feedbacku; ona dostaje `actionKey`, losuje sceny zgodne z profilem operacji i pracuje tak długo, dopóki nie dostanie informacji, że prawdziwy payload już przyszedł.

```js
class OperationFeedbackSession {
    constructor(actionKey, renderer) {
        this.actionKey = actionKey;
        this.renderer = renderer;

        this.profile = OPERATION_FEEDBACK.operations[actionKey];

        this.running = false;
        this.payloadReceived = false;

        this.lastScene = null;
        this.lastSecurity = null;
    }

    async start() {
        if (!this.profile) {
            throw new Error(`Unknown feedback action: ${this.actionKey}`);
        }

        this.running = true;

        this.renderer.clear();

        while (this.running && !this.payloadReceived) {
            const sceneName = this.pickScene();

            await this.runScene(sceneName);

            if (!this.payloadReceived) {
                await sleep(randomInt(300, 900));
                this.renderer.clear();
            }
        }
    }

    stopWithPayload(payload) {
        this.payloadReceived = true;
        this.running = false;

        this.renderer.showCompletion("PAYLOAD RECEIVED");

        setTimeout(() => {
            this.renderer.showRealResult(payload);
        }, 500);
    }

    pickScene() {
        const available = this.profile.scenes.filter(
            scene => scene !== this.lastScene
        );

        const scene = randomItem(
            available.length ? available : this.profile.scenes
        );

        this.lastScene = scene;

        return scene;
    }

    async runScene(sceneName) {
        const scene = OPERATION_FEEDBACK.scenes[sceneName];

        this.renderer.showSceneTitle(sceneName);

        const lineCount = randomInt(
            scene.minLines,
            scene.maxLines
        );

        for (let i = 0; i < lineCount; i++) {
            if (this.payloadReceived) return;

            const line = this.makeSceneLine(sceneName);

            this.renderer.addLine(line);

            await sleep(randomInt(350, 1100));
        }

        if (
            scene.allowChoice &&
            this.profile.presentation === "button_choice" &&
            Math.random() < 0.55
        ) {
            await this.runChoice();
        }

        await sleep(
            randomInt(scene.duration[0], scene.duration[1])
        );
    }

    makeSceneLine(sceneName) {
        // Czasem wpuszczamy ogólny event techniczny.
        if (Math.random() < 0.2) {
            const eventType = randomItem([
                "reconnect",
                "retry",
                "waiting"
            ]);

            return randomItem(
                OPERATION_FEEDBACK.serviceEvents[eventType]
            );
        }

        const securityKey = this.pickSecurity();

        const security =
            OPERATION_FEEDBACK.security[securityKey];

        if (!security) {
            return `processing ${sceneName}`;
        }

        const availableEventTypes =
            Object.keys(security);

        const eventType =
            randomItem(availableEventTypes);

        return randomItem(
            security[eventType]
        );
    }

    pickSecurity() {
        const available =
            this.profile.security.filter(
                key => key !== this.lastSecurity
            );

        const security = randomItem(
            available.length
                ? available
                : this.profile.security
        );

        this.lastSecurity = security;

        return security;
    }

    async runChoice() {
        const availableChoices =
            this.profile.choices.filter(
                key => OPERATION_FEEDBACK.choices[key]
            );

        if (!availableChoices.length) {
            return;
        }

        const choiceKey =
            randomItem(availableChoices);

        const choice =
            OPERATION_FEEDBACK.choices[choiceKey];

        const prompt =
            randomItem(choice.prompts);

        const result =
            await this.renderer.showChoice({
                prompt,
                options: choice.options,
                timeout: choice.timeout,
                defaultValue: choice.default
            });

        this.renderer.addLine(
            `operator decision // ${result}`
        );

        await sleep(600);
    }
}
```

Ten kawałek jest już właściwie „mózgiem”: nie ma w nim tekstów konkretnych operacji, tylko interpretuje słownik, wybiera scenę, dobiera pasujące zabezpieczenie, czasami wrzuca reconnect/retry i opcjonalnie odpala pytanie; dzięki temu później `exploit` będzie korzystał dokładnie z tego samego engine'u, tylko z innym profilem JSON.

Renderer można na razie zrobić wręcz prymitywny, żeby zobaczyć, czy cały pomysł działa, zanim zaczniemy robić fajne GUI.

```js
const renderer = {
    container: document.querySelector("#operation-feedback"),

    clear() {
        this.container.innerHTML = "";
    },

    showSceneTitle(name) {
        const el = document.createElement("div");
        el.className = "feedback-scene";
        el.textContent = `[ ${name.toUpperCase()} ]`;

        this.container.appendChild(el);
    },

    addLine(text) {
        const el = document.createElement("div");
        el.className = "feedback-line";
        el.textContent = `> ${text}`;

        this.container.appendChild(el);
    },

    showCompletion(text) {
        this.clear();

        const el = document.createElement("div");
        el.className = "feedback-complete";
        el.textContent = text;

        this.container.appendChild(el);
    },

    showRealResult(payload) {
        this.clear();

        const el = document.createElement("pre");
        el.textContent = JSON.stringify(payload, null, 2);

        this.container.appendChild(el);
    },

    showChoice({ prompt, options, timeout, defaultValue }) {
        return new Promise(resolve => {
            const box = document.createElement("div");
            box.className = "feedback-choice";

            const question = document.createElement("div");
            question.textContent = prompt;

            const timer = document.createElement("div");

            box.appendChild(question);
            box.appendChild(timer);

            let finished = false;
            let remaining = Math.ceil(timeout / 1000);

            timer.textContent = `${remaining}s`;

            for (const option of options) {
                const button = document.createElement("button");

                button.textContent = option.label;

                button.onclick = () => {
                    if (finished) return;

                    finished = true;

                    clearInterval(interval);
                    clearTimeout(timeoutId);

                    box.remove();

                    resolve(option.value);
                };

                box.appendChild(button);
            }

            const interval = setInterval(() => {
                remaining--;

                timer.textContent = `${remaining}s`;
            }, 1000);

            const timeoutId = setTimeout(() => {
                if (finished) return;

                finished = true;

                clearInterval(interval);

                box.remove();

                resolve(defaultValue);
            }, timeout);

            this.container.appendChild(box);
        });
    }
};
```

Ten renderer tylko pokazuje mechanizm: linie trafiają do jednego kontenera, `showChoice()` tworzy pytanie i przyciski z countdownem, a gdy user nic nie zrobi, Promise sam zwraca wartość domyślną i animacja leci dalej.

A użycie przy prawdziwym requestcie wyglądałoby mniej więcej tak:

```js
const feedback = new OperationFeedbackSession(
    "scan_ports",
    renderer
);

feedback.start();

fetch("/hack-action", {
    method: "POST",
    body: JSON.stringify({
        action: "scan_ports",
        target_id: targetId
    }),
    headers: {
        "Content-Type": "application/json"
    }
})
    .then(response => response.json())
    .then(payload => {
        feedback.stopWithPayload(payload);
    })
    .catch(error => {
        feedback.running = false;

        renderer.showCompletion(
            "REMOTE OPERATION FAILED"
        );

        console.error(error);
    });
```

Tutaj właśnie dzieje się najważniejsza rzecz: **request i przedstawienie lecą równolegle**; feedback nie ma pojęcia, kiedy serwer odpowie, więc może sobie zmieniać sceny przez 5, 30 albo 120 sekund, a kiedy `fetch()` w końcu wróci, `stopWithPayload()` ucina wszystko w dowolnym miejscu i pokazuje prawdziwy wynik.

Ja bym właśnie od takiej wersji zaczął — nawet bez CSS — bo po puszczeniu jej kilka razy od razu zobaczymy, czy **losowanie scen daje wrażenie jednej sensownej operacji**, czy zaczyna gadać od rzeczy i wtedy poprawimy sam model słownika, zanim urośnie do 12 operacji.

