# Ollama — ograniczenie CPU na serwerze CHAOS

## Incydent i potwierdzone działanie

5 października 2026 operator zgłosił konieczność ograniczenia Ollamy i zastosował:

```bash
sudo systemctl set-property --runtime ollama.service CPUQuota=300%
```

Załączony zrzut htop pokazuje 8 logicznych CPU, RAM 7,70 / 11,7 GB,
swap 3,2 / 8,0 GB oraz load average 5,54 i 7,76 dla pierwszych dwóch okresów.
Nie ma porównania przed/po ani widocznego procesu Ollamy, dlatego sam zrzut
nie rozstrzyga źródła całego obciążenia ani aktywnego swapowania.

Status: **ograniczenie runtime zastosowane przez operatora**. Trwałe ustawienie
oraz pomiary opóźnień po zmianie nie zostały jeszcze potwierdzone.

## Znaczenie poprawki

Limit dotyczy całej usługi `ollama.service`, łącznie z jej procesami potomnymi.
`300%` oznacza łączny budżet czasu CPU odpowiadający trzem logicznym CPU;
nie przypina procesu do trzech konkretnych rdzeni. Ogranicza konkurencję
inferencji z pozostałymi usługami CHAOS. Może wydłużyć czas generowania.
Nie jest limitem RAM ani swapu.

Potwierdzona interwencja dotyczy zarządzania zasobami hosta. Nie ustalono
jeszcze, czy obciążenie nasilały równoległe generacje, konkretny model,
ponowienia zadań czy inny czynnik. Nie zmieniano logiki workerów ani kolejek.

## Utrwalenie po restarcie hosta

Opcja `--runtime` oznacza ustawienie tymczasowe, tracone po restarcie hosta.
Aby utrwalić ten sam limit, operator może wykonać:

```bash
sudo systemctl set-property ollama.service CPUQuota=300%
```

Systemd stosuje zmianę od razu i zapisuje ją na kolejne uruchomienia;
nie trzeba restartować Ollamy tylko w celu zastosowania tego limitu.
To procedura do wykonania na serwerze, nie potwierdzenie jej wdrożenia.

## Weryfikacja operacyjna

```bash
systemctl show ollama.service -p CPUQuotaPerSecUSec -p ControlGroup
systemctl cat ollama.service
systemd-cgtop
journalctl -u ollama.service --since '15 minutes ago' --no-pager
```

Sprawdzić efektywny budżet odpowiadający 3 s CPU na sekundę, zapis konfiguracji
oraz obciążenie grupy usługi podczas generacji. Po utrwaleniu powtórzyć odczyt
przy następnym planowanym restarcie hosta. Porównać czas odpowiedzi CHAOS,
czas generowania, timeouty i zaległości kolejki; nie uznawać samego spadku
wykorzystania CPU za pełną walidację działania aplikacji.

## Źródła

- Zgłoszenie operatora i zrzut htop z 2026-10-05.
- [systemctl — set-property i --runtime](https://manpages.debian.org/bookworm/systemd/systemctl.1.en.html).
- [systemd.resource-control — CPUQuota](https://manpages.debian.org/bookworm/systemd/systemd.resource-control.5.en.html).
