# Smart Heating – Handleiding

*English version: [manual.en.md](manual.en.md)*

Smart Heating regelt de verwarming per kamer: elke kamer wordt warm wanneer dat nodig is, en de cv-ketel brandt alleen als een kamer echt warmte vraagt. Je hoeft er meestal niets voor te doen; deze handleiding legt uit wat er gebeurt en wat je ziet op het scherm Overzicht.

## In het kort

In huis is één cv-ketel en hangen verschillende radiatoren. Normaal stookt de ketel voor het hele huis tegelijk. Smart Heating kijkt per kamer: alleen een kamer die op dat moment warm moet zijn, krijgt warmte. Kamers waar niemand is, blijven koeler. Zo bespaar je gas zonder dat je het koud hebt.

Dat werkt zo:

- **Slimme radiatorkranen** op de radiatoren openen en sluiten vanzelf. Elke kraan krijgt van Smart Heating te horen hoe warm zijn kamer moet zijn.
- **De cv-ketel** gaat alleen branden als minstens één kamer warm moet zijn en nog duidelijk te koud is. Op het scherm heet de ketel ‘boiler’.
- **Elke kamer heeft een schema**: de tijden waarop het daar warm moet zijn. Buiten die tijden zakt de kamer naar een lagere temperatuur.
- **Het systeem let op wat er in huis gebeurt**: is iedereen weg, staat er een raam open, ben je met vakantie? Dan past het de temperatuur vanzelf aan.

Je hoeft er dus meestal niets voor te doen. Wil je het eens anders, dan zijn er een paar knoppen, zoals **Boost** om een kamer nu meteen warm te stoken.

## Het scherm Overzicht

Klik in de zijbalk van Home Assistant op **Smart Heating**. Je komt dan meteen op het Overzicht: het eerste icoontje linksboven, het huisje. Hier zie je in één keer wat de verwarming doet, en hier staan alle knoppen die je nodig hebt. De andere icoontjes (een radiator, een ketel en een vraagteken) zijn de tabbladen Verwarming, Boiler en Help. Die zijn bedoeld voor de beheerder; je kunt ze gewoon laten liggen.

Links staat het blok **Nu**, rechts staan de knoppen. Is er iets mis, dan verschijnt er ook een blok **Meldingen**. Op een telefoon staan de blokken onder elkaar in plaats van naast elkaar.

### Nu

Bovenaan staat één korte zin over het hele huis, bijvoorbeeld:

> Verwarmen: Woonkamer, Slaapkamer. Boiler aan.

- **Verwarmen:** de kamers die nu nog te koud zijn en waar de radiator dus open staat. Staat er *Er wordt niets verwarmd*, dan zijn alle kamers op temperatuur.
- **Boiler aan / Boiler uit:** of de cv-ketel op dit moment gevraagd wordt om te branden.
- Soms staat er nog iets achter: *Niemand is thuis.* of *Vakantiemodus staat aan.*

Daaronder staat *Geen meldingen.* Is er iets mis, dan staat daar bijvoorbeeld **2 meldingen hebben aandacht nodig**.

Dan volgt een tabel met één regel per kamer:

| Kolom | Wat je ziet |
| --- | --- |
| Ruimte | De naam van de kamer. |
| Nu | Hoe warm het nu in de kamer is. Een streepje (–) betekent dat de temperatuur even niet bekend is. |
| Doel | De temperatuur waar de kamer nu naartoe werkt. |
| Wat gebeurt er | Een korte zin, zoals *Warm tot 23:00*. Wat al die zinnen betekenen, staat in de volgende paragraaf. |

### Meldingen

Dit blok verschijnt alleen als er iets aandacht nodig heeft, bijvoorbeeld een bijna lege batterij. Zie je het niet, dan is alles in orde. Elke melding staat er als gewone zin; verderop in deze handleiding lees je wat je ermee kunt.

### Bediening

Hier staan de knoppen:

- **Vakantiemodus** (een aan/uit-schakelaar) en **Vakantiedagen** (een schuifje): voor als je een paar dagen weg bent.
- **Handmatige ruimte-override** en **Handmatige ruimte-override annuleren**: voor kamers zonder slimme kraan.
- In een apart blok **Boost**: voor elke kamer een knop **Boost** en een knop **Boost annuleren**, bijvoorbeeld *Studeerkamer: Boost*.
- Onderaan een link naar de Smart Heating-opties (schema’s en temperaturen per kamer). Die is bedoeld voor de beheerder.

Hoe je de knoppen gebruikt, staat bij [De knoppen](#de-knoppen) verderop.

## Wat de zin bij een kamer betekent

In de kolom *Wat gebeurt er* staat per kamer één zin. De tijden en temperaturen hieronder zijn voorbeelden. Ligt een tijdstip niet vandaag, dan staat de dag erbij, bijvoorbeeld *ma 07:00*.

| Je ziet | Wat het betekent |
| --- | --- |
| Warm tot 23:00 | Het schema zegt dat het hier nu warm moet zijn, tot 23:00. |
| Warm | Het is hier warm en er staat geen eindtijd gepland. |
| Warm vanaf 07:00 | Nu staat de kamer lager. Om 07:00 begint de volgende warme periode. |
| Op 16 graden gehouden | De kamer staat op de lagere temperatuur en er is niets gepland. |
| Opwarmen, warm tot 17:00 | De kamer is al eerder begonnen met opwarmen, zodat hij op tijd warm is. |
| Boost tot 14:00 | Iemand heeft op Boost gedrukt. De kamer is warm tot 14:00, of tot je de Boost annuleert. |
| Raam lijkt open, verwarming gepauzeerd tot 14:20 | De kamer koelde heel snel af. Waarschijnlijk staat er een raam open, dus de verwarming wacht even. |
| Niemand thuis, op 16 graden gehouden | Iedereen is weg. Na twee dagen weg zakt dit naar 12 graden. |
| Persoon van deze ruimte is weg, op 16 graden gehouden | Deze kamer hoort bij iemand die nu weg is, dus het schema wordt overgeslagen. De kamer warmt weer op als die persoon thuis of onderweg is. |
| Wacht tot de vloerverwarming is opgewarmd, op 12 graden gehouden | De vloerverwarming warmt eerst op. Kamers die nu niet gebruikt worden, houden hun radiator zolang dicht. |
| Handmatig ingesteld op 22 graden, tot 17:00 | Iemand heeft de kraan zelf verdraaid. Die stand blijft tot 17:00, daarna neemt het schema het weer over. |
| Vakantie tot za 00:00, op 12 graden gehouden | De vakantiemodus staat aan. Het huis wordt net boven het vriespunt gehouden en warmt op tijd weer op. |

## Wanneer wordt een kamer warm?

Elke kamer kent drie temperaturen. De beheerder kan ze per kamer aanpassen; dit zijn de standaardwaarden:

| Temperatuur | Standaard | Wanneer |
| --- | --- | --- |
| Comfort | 19,5 °C | Als het volgens het schema warm moet zijn, of na een Boost. |
| Lager | 16 °C | Buiten het schema, of als niemand thuis is. |
| Vorstbeveiliging | 12 °C | Bij vakantie, als je langer dan twee dagen weg bent, of als er een raam open lijkt te staan. Net warm genoeg om het huis te beschermen. |

### Het schema

In het schema staat wanneer een kamer warm moet zijn. Standaard is dat:

- **Woonkamer:** elke dag van 06:00 tot 23:00.
- **Werkkamer:** maandag, woensdag en vrijdag van 08:00 tot 17:00.
- **Slaapkamer:** tijdens de werkuren, plus even opwarmen voor het slapengaan (21:30 tot 22:30).

Het schema aanpassen doet de beheerder in de instellingen.

### Op tijd warm

Een kamer begint al voor de geplande tijd met opwarmen, zodat hij op tijd warm is. In het begin is dat ruim een uur van tevoren. Daarna leert het systeem per kamer hoe lang opwarmen echt duurt, ook afhankelijk van hoe koud het buiten is. Je ziet dan *Opwarmen* bij de kamer staan.

### Wie wint er?

Soms gelden er meerdere dingen tegelijk. Dan wint de bovenste uit dit rijtje:

1. **Boost**: je wilt het nu warm.
2. **Open raam**: de verwarming pauzeert even.
3. **Vakantie**: het hele huis op vorstbeveiliging.
4. **Niemand thuis**: alle kamers op de lagere temperatuur.
5. **Het schema**, met op tijd opwarmen. Hoort de kamer bij iemand die weg is, dan wordt het schema overgeslagen.
6. Anders: **de lagere temperatuur**.

## Wat het systeem vanzelf doet

Deze dingen gebeuren automatisch. Je hoeft er niets voor te doen.

- **Raam open:** als een kamer ineens heel snel afkoelt, gaat het systeem ervan uit dat er een raam open staat. De verwarming in die kamer pauzeert dan een kwartier tot een half uur, zodat je niet de straat verwarmt.
- **Niemand thuis:** is iedereen de deur uit, dan gaan alle kamers naar de lagere temperatuur (16 °C). Ben je langer dan twee dagen weg, dan zakt het huis naar vorstbeveiliging (12 °C).
- **Kamer van iemand die weg is:** een kamer kan bij bepaalde personen horen, bijvoorbeeld een werkkamer. Zijn die allemaal weg, dan blijft die kamer op de lagere temperatuur, ook als het schema iets anders zegt. Een Boost werkt wel gewoon.
- **Onderweg naar huis:** als de beheerder dit heeft ingesteld, merkt het systeem dat je onderweg bent, bijvoorbeeld als je in de buurt van huis komt. Het huis begint dan alvast op te warmen, zodat het warm is als je binnenkomt.
- **Vloerverwarming:** vloerverwarming is traag. Een kamer met vloerverwarming begint daarom al een paar uur voor de geplande tijd. Zolang die opwarmt, blijven de radiatoren in kamers die niet gebruikt worden dicht, zodat de warmte naar de vloer gaat.
- **Kraan uitgezet:** staat een slimme radiatorkraan uit, dan zet het systeem hem vanzelf weer aan.
- **Weekrapport:** elke maandag om 08:00 krijg je een bericht in Home Assistant (bij het belletje). Daarin staat hoeveel gas er is gebruikt vergeleken met vorig jaar, rekening houdend met hoe koud het was, hoeveel uur elke kamer verwarmd is en of er problemen waren.

## De knoppen

Alle knoppen staan op het Overzicht, aan de rechterkant. Een knop gebruik je door op **Klik** ernaast te tikken.

### Boost: nu even warm

Is het koud in een kamer en wil je niet wachten op het schema? Druk dan bij die kamer op **Boost**. De kamer gaat meteen naar de comforttemperatuur en de ketel springt aan als dat nodig is. Een Boost duurt standaard een uur. Daarna gaat de kamer vanzelf terug naar het schema.

Wil je eerder stoppen, druk dan op **Boost annuleren**. Bij de kamer zie je zolang *Boost tot 14:00* staan.

### Vakantie: het huis op een laag pitje

Ga je een paar dagen weg? Zo zet je het huis op vorstbeveiliging:

1. Zet bij **Vakantiedagen** het schuifje op het aantal dagen dat je weg bent (1 tot 60, standaard 7). Tel het aantal nachten: vertrek je zaterdag en kom je volgende zaterdag terug, kies dan 7.
2. Zet **Vakantiemodus** aan.

Alle kamers gaan dan naar 12 °C. Op de dag dat je terugkomt, gaat het huis vanaf middernacht weer zijn gewone schema volgen. Zo is het warm als je thuiskomt. Ben je eerder terug, zet de vakantiemodus dan gewoon uit. Is ‘onderweg naar huis’ ingesteld, dan stopt de vakantie ook vanzelf als je eraan komt.

### Handmatige ruimte-override: voor kamers zonder slimme kraan

Sommige kamers hebben een gewone radiatorkraan die je met de hand draait. Die kamers kunnen de ketel zelf niet laten aanslaan. Wil je zo’n kamer toch warm hebben:

1. Draai de radiatorkraan in die kamer open.
2. Druk op **Handmatige ruimte-override**.

De ketel blijft dan twee uur lang branden. Ben je eerder klaar, druk dan op **Handmatige ruimte-override annuleren**, en vergeet niet de kraan weer dicht te draaien.

## Meldingen

Een melding verschijnt alleen als er echt iets aandacht nodig heeft. Hij verdwijnt vanzelf zodra het probleem is opgelost. In de meldingen staat de naam van de kamer; hieronder staat *de kamer*.

| Melding | Wat je kunt doen |
| --- | --- |
| De batterij van de radiatorkraan in de kamer is bijna leeg. | Vervang de batterijen binnenkort. De kraan werkt tot die tijd gewoon door. |
| De radiatorkraan in de kamer reageert niet. | Kijk of de batterij leeg is of de kraan los zit. Helpt dat niet, laat het de beheerder weten. |
| De radiatorkraan in de kamer staat uit en gaat niet weer aan. | Het systeem probeerde de kraan aan te zetten, maar dat lukte niet. Kijk op de kraan zelf of laat het de beheerder weten. |
| De radiatorkraan in de kamer neemt zijn temperatuur niet over. | De kraan kreeg een paar keer een temperatuur, maar nam die niet over. Vaak helpt nieuwe batterijen plaatsen. |
| De temperatuursensor in de kamer meldt niets meer. | De losse thermometer in die kamer is stil. Kijk of de batterij leeg is. Tot die tijd gebruikt het systeem de thermometer in de radiatorkraan. |
| De kamer is al lange tijd te koud en haalt zijn doel niet. | Kijk of er een raam of deur openstaat en of de radiator warm wordt. Blijft het zo, laat het de beheerder weten. |
| De Bosch-cloud is onbereikbaar. | De ketel kan even niet betrouwbaar worden aangestuurd. De radiatorkranen volgen gewoon het schema. Meestal lost dit zichzelf op. |

## Zelf iets verstellen

Je mag gewoon aan de knoppen in huis draaien. Smart Heating houdt daar rekening mee.

- **Aan een slimme radiatorkraan draaien:** de stand die je kiest, blijft staan tot het schema van die kamer de volgende keer verandert. Daarna neemt het systeem het weer over. Zet je de kraan hoger dan de lagere temperatuur en is de kamer kouder dan wat je instelde, dan slaat de ketel ook aan. Bij de kamer staat zolang *Handmatig ingesteld op …*.
- **Aan de EasyControl draaien** (de thermostaat van Bosch aan de muur): je instelling wordt ongeveer twee uur gerespecteerd. Daarna gaat Smart Heating weer verder.
- **In Home Assistant de temperatuur van een kamer veranderen:** dat kan niet. Je krijgt dan de melding dat het doel door Smart Heating wordt bepaald. Gebruik in plaats daarvan **Boost**, of vraag de beheerder het schema of de temperaturen aan te passen.

## Veelgestelde vragen

**Er staat ‘Verwarmen’, maar ook ‘Boiler uit’. Klopt dat?**
Ja. ‘Verwarmen’ betekent dat de radiator in die kamer open staat omdat het er nog iets te koud is. De ketel slaat alleen aan voor kamers die volgens het schema of een Boost echt warm moeten zijn. Een kamer die op de lagere temperatuur staat, krijgt alleen de warmte die nog in de leidingen zit.

**Mijn kamer wordt niet warm. Wat nu?**
Kijk eerst naar de zin bij de kamer op het Overzicht. Staat er bijvoorbeeld *Warm vanaf 17:00* of *Persoon van deze ruimte is weg*, dan doet het systeem precies wat het moet doen. Wil je het toch warm, druk dan op **Boost**. Staat er een melding, lees dan bij [Meldingen](#meldingen-1) wat je ermee kunt.

**Kan ik de tijden of temperaturen aanpassen?**
Ja, maar dat doet de beheerder in de instellingen. Vraag het gerust als een schema niet bij je dag past.

**Waarom staat er ‘Raam lijkt open’, terwijl alles dicht is?**
De kamer koelde ineens snel af, bijvoorbeeld door een deur die openstond. Na hooguit een half uur gaat de verwarming vanzelf weer verder. Wil je niet wachten, druk dan op **Boost**.

**Moet ik de vakantiemodus na mijn vakantie zelf uitzetten?**
Nee. Op de dag dat je terugkomt, volgt het huis weer het gewone schema, en de knop gaat uit zodra er iemand thuis is.
