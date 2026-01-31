### 1. Mitä tekoäly teki hyvin?
- Tekoäly auttoi tekemään hyvät oletukset alusta asti: ISO-8601 + aikavyöhyke, vertailu UTC:na ja varaukset aikaväleinä [start, end) → back-to-back-varaukset toimivat ilman erikoistapauksia.
- Tuotti nopeasti minimaalisen ja toimivan FastAPI-API:n, jossa oli selkeät endpointit ja oikeat perusstatuskoodit (201/204/404/409/422).
- Antoi hyvän “checklistin” ylläpidettävyyteen: vastuualueiden erottaminen, globaali tila, validoinnin paikka, testattavuus.
- Toteutti annetun tehtävän vaatimukset pääosin oikein ja promptien mukaisesti

### 2. Mitä tekoäly teki huonosti? 
- Alkuperäinen ratkaisu oli liian “yhdessä tiedostossa” ja sekoitti vastuut: HTTP-kerros + liiketoimintalogiikka + tallennus + lukitus samassa paikassa → vaikeampi testata ja laajentaa tulevaisuudessa.
- In-memory-toteutuksessa huomasin kilpajuoksutilanteen: jos päällekkäisyystarkistus ja tallennus eivät tapahdu samaan aikaan, kaksi samanaikaista pyyntöä voisivat teoriassa mennä läpi.
- Testien kannalta ongelmana oli, että repository ja FastAPI-sovellus luotiin vain kerran ja samaa in-memory-tilaa käytettiin kaikissa testeissä. Tämän seurauksena testien välillä kertyi dataa, mikä ei tullut heti ilmi ennen kuin testejä oli useampia. Korjasin tämän lisäämällä repositoryyn reset-metodin ja pytest-fixturen testien eristämiseksi. 
- Tekoälylle piti olla hyvin spesifi mitä halusi tai ei halunnut, ja joskus tästä huolimatta se loi ylimääräisiä asioita mitä ei pyytänyt. 

### 3. Mitkä olivat tärkeimmät parannukset, jotka teit tekoälyn tuottamaan koodiin ja miksi?
- Vastuualueiden erottaminen (service + repository): siirsin varauslogiikan ja validoinnin endpointtien ulkopuolelle → koodi on luettavampi ja liiketoimintasäännöt on helpompi testata ilman HTTP:tä.
- Tiedostojako (main/api/services/repository/models): jaoin sovelluksen roolien mukaan → projektin rakenne selkeytyi ja jatkokehitys/helpompi navigointi parani ilman että API:n toiminta muuttui.
- Testien eristäminen (reset + pytest fixture): koska in-memory repository luotiin kerran sovelluksen käynnistyessä ja sama instanssi oli käytössä kaikissa testeissä, testit jakoivat samaa tilaa → lisäsin reset-metodin ja fixturen, jotta testien toimivuus ei riippuisi niiden ajojärjestyksestä.
- Päällekkäisyyksien eston korjaus: siirsin päällekkäisyystarkistuksen ja insertin saman lukon sisään (insert_if_no_overlap) → estää samanaikaisten pyyntöjen aiheuttamat päällekkäiset varaukset ja tekee säännöstä luotettavamman.