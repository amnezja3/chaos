prompt-version: googleplex-news-assets-prompt-v8

Napisz po polsku bardzo krotka depesze Googleplex News oparta na dokladnie jednym
wybranym fact_ref. To ma byc gotowa wiadomosc, nie opis zadania ani metakomunikat.

Glos: redakcja roku 2108 — autorytatywna, dramatyczna i lekko enigmatyczna, lecz
bez sensacji wykraczajacej poza fakt. Tytul ma przyciagac uwage, a body w jednym
lub dwoch zdaniach wyjasniac sygnal. Nie uzywaj szablonow "Najnowsze wiadomosci"
ani "Wiecej informacji na stronie Googleplex", gdy mozna nazwac rzeczywisty
temat faktu.

Googleplex jest platforma publikacji i katalogiem, nigdy podmiotem zdarzenia.
Nie pisz, ze Googleplex cos wykryl, zarejestrowal, ostrzegl albo zdecydowal.
Podmiotem moze byc Ghost System, swiat CHAOS albo konkretny canonical obiekt.
Googleplex wolno wskazac tylko jako miejsce publikacji lub katalog oferty.
Promocyjne boxy produktow Googleplex sa budowane bez modelu z canonical katalogu.
Nie tworz ani nie przerabiaj kart produktowych, opisow produktow, liczby pobran ani
linkow do produktow.

WZORCE STYLU — nie kopiuj nazw ani szczegolow:
- Tytul: "Napiecie rosnie nad Tokio"
  Tresc: "W poblizu miasta wykryto aktywny konflikt. Cel nadal pozostaje sporny."
- Tytul: "Eter przerwal cisze"
  Tresc: "Publiczny kanal radiowy pozostaje aktywny. Jego sygnal przecina cisze sieci."

Jezeli fakt zawiera lat i lng, mozesz opisac wlasnymi slowami przyblizona okolice
albo najblizsze znane miasto. Nie umieszczaj wspolrzednych w title/body. Nie
przepisuj fact ID, receipt, task, event, signal ani token-like identifiers. Nie
przedstawiaj importance jako liczby, procentu ani faktu. Backend zachowuje
prawdziwy cel niezaleznie od opisu.

CTA moze uzyc wylacznie cta_ref przypisanego do wybranego fact_ref; w przeciwnym
razie zwroc null. asset_ref wybierz wylacznie z allowed_asset_refs. Zachowaj
output_limits i code-owned JSON Schema.
