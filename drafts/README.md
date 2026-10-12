# Games not yet in the book

Every game in Wikipedia's [list of chess games](https://en.wikipedia.org/wiki/List_of_chess_games) that this book does not have: **80** of them. Nothing here was left out for want of a source. The book stops at forty because that is where the selection stopped.

## How to add one

1. Open the game's page in your browser and copy its PGN.
2. Save it in this folder as `<game id>.pgn` -- the id is the number at the
   end of the URL, so the Steinitz-Mongredien game below becomes
   `drafts/1001497.pgn`. The name matters: it is how the record learns which
   page to cite.
3. Run `make import`. Each PGN becomes `games/<year>-<white>-<black>.yml`
   with the players, date, event, opening code, result and moves already
   filled in, and the source pointing back at the page.
4. Open the new record and give the game a `title`, and a `why` if you want
   a subtitle. Rename the file if you would rather it had a different slug.
5. `make all`, then `make check`.

Every move is replayed on a board at import and again at build, so a PGN
that did not copy cleanly will be refused rather than published.

A game with its own Wikipedia article is marked **W** below: for those the
move list can be taken from the article instead, and cited to it.

## The games

| Year | Game | PGN from |
| ---: | --- | --- |
| 1912 | Edward Lasker vs Sir George Thomas, London | [1259009](https://www.chessgames.com/perl/chessgame?gid=1259009) |
| 1918 | Akiba Rubinstein vs Milan Vidmar, Berlin | [1119780](https://www.chessgames.com/perl/chessgame?gid=1119780) |
| 1920 | Edwin Ziegler Adams vs Carlos Torre Repetto, New Orleans | [1143989](https://www.chessgames.com/perl/chessgame?gid=1143989) |
| 1922 | Alexander Alekhine vs Efim Bogoljubow, Pistyan **W** | [1006949](https://www.chessgames.com/perl/chessgame?gid=1006949) |
| 1923 | Friedrich Sämisch vs Aron Nimzowitsch, Copenhagen **W** | [1102400](https://www.chessgames.com/perl/chessgame?gid=1102400) |
| 1924 | José Raúl Capablanca vs Savielly Tartakower, New York | [1102104](https://www.chessgames.com/perl/chessgame?gid=1102104) |
| 1925 | Richard Réti vs Alexander Alekhine, Baden-Baden | [1012326](https://www.chessgames.com/perl/chessgame?gid=1012326) |
| 1930 | Glucksberg vs Miguel Najdorf, Warsaw **W** | [1100774](https://www.chessgames.com/perl/chessgame?gid=1100774) |
| 1932 | Salo Flohr vs Max Euwe | [1042371](https://www.chessgames.com/perl/chessgame?gid=1042371) |
| c. 1933 | Albert Einstein vs  Oppenheimer | _no id in the list_ |
| 1934 | Esteban Canal vs NN, Budapest **W** | [1264050](https://www.chessgames.com/perl/chessgame?gid=1264050) |
| 1935 | Max Euwe vs Alexander Alekhine, 26th Match Game, Zandvoort **W** | [1013180](https://www.chessgames.com/perl/chessgame?gid=1013180) |
| 1938 | Frank Parr vs George Wheatcroft, London | [1284171](https://www.chessgames.com/perl/chessgame?gid=1284171) |
| 1943 | B Molinari vs Luis Roux Cabral, Montevideo **W** | [1278766](https://www.chessgames.com/perl/chessgame?gid=1278766) |
| 1946 | Yuri Gusev vs E Auerbach, Chelyabinsk **W** | [1472988](https://www.chessgames.com/perl/chessgame?gid=1472988) |
| 1953 | Efim Geller vs Max Euwe, Zurich | [1042835](https://www.chessgames.com/perl/chessgame?gid=1042835) |
| 1954 | Mikhail Botvinnik vs Vasily Smyslov, 14th Match Game, Moscow | [1032320](https://www.chessgames.com/perl/chessgame?gid=1032320) |
| 1957 | Bogdan Śliwa vs David Bronstein, Gotha **W** | [1252391](https://www.chessgames.com/perl/chessgame?gid=1252391) |
| 1959 | Mikhail Tal vs Vasily Smyslov, Bled | [1139475](https://www.chessgames.com/perl/chessgame?gid=1139475) |
| 1959 | Bobby Fischer vs Tigran Petrosian, Zagreb **W** | [1106430](https://www.chessgames.com/perl/chessgame?gid=1106430) |
| 1961 | Milunka Lazarević vs Nona Gaprindashvili, Candidates Tournament, Vrnjacka Banja | [1270326](https://www.chessgames.com/perl/chessgame?gid=1270326) |
| 1962 | Eduard Gufeld vs Lubomir Kavalek, Marianske Lazne | [1261710](https://www.chessgames.com/perl/chessgame?gid=1261710) |
| 1963 | Robert Byrne vs Bobby Fischer, New York | [1008419](https://www.chessgames.com/perl/chessgame?gid=1008419) |
| 1964 | Lajos Portisch vs Mikhail Tal, Amsterdam Interzonal **W** | [1113065](https://www.chessgames.com/perl/chessgame?gid=1113065) |
| 1965 | Efim Geller vs Vasily Smyslov, 5th Match Game, Moscow | [1049156](https://www.chessgames.com/perl/chessgame?gid=1049156) |
| 1966 | Tigran Petrosian vs Boris Spassky, 10th Match Game, Moscow | [1106725](https://www.chessgames.com/perl/chessgame?gid=1106725) |
| 1967 | Bobby Fischer vs Leonid Stein, Sousse Interzonal **W** | [1044022](https://www.chessgames.com/perl/chessgame?gid=1044022) |
| 1968 | Frank Poole vs HAL 9000 | _no id in the list_ |
| 1969 | Boris Spassky vs Tigran Petrosian, 19th Match Game, Moscow | [1106864](https://www.chessgames.com/perl/chessgame?gid=1106864) |
| 1970 | Bent Larsen vs Boris Spassky, Belgrade | [1128831](https://www.chessgames.com/perl/chessgame?gid=1128831) |
| 1971 | Bruce Harper vs Robert Zuk, Burnaby | [1289113](https://www.chessgames.com/perl/chessgame?gid=1289113) |
| 1972 | Boris Spassky vs Bobby Fischer, 11th Match Game, Reykjavik | [1044724](https://www.chessgames.com/perl/chessgame?gid=1044724) |
| 1972 | Boris Spassky vs Bobby Fischer, 13th Match Game, Reykjavik | [1128889](https://www.chessgames.com/perl/chessgame?gid=1128889) |
| 1973 | David Bronstein vs Ljubomir Ljubojević, Petropolis Interzonal | [1034661](https://www.chessgames.com/perl/chessgame?gid=1034661) |
| 1974 | Anatoly Karpov vs Boris Spassky, 9th Match Game, Leningrad | [1067812](https://www.chessgames.com/perl/chessgame?gid=1067812) |
| 1975 | Dragojub Minić vs Albin Planinc, Rovinj/Zagreb | [1262429](https://www.chessgames.com/perl/chessgame?gid=1262429) |
| 1976 | Smbat Lputian vs Garry Kasparov, Tbilisi | [1069599](https://www.chessgames.com/perl/chessgame?gid=1069599) |
| 1977 | Stefano Tatai vs Anatoly Karpov, Las Palmas | [1068020](https://www.chessgames.com/perl/chessgame?gid=1068020) |
| 1979 | Igor Ivanov vs Anatoly Karpov, Moscow | [1060854](https://www.chessgames.com/perl/chessgame?gid=1060854) |
| 1980 | Anatoly Karpov vs Tony Miles, European Team Championship, Skara | [1068157](https://www.chessgames.com/perl/chessgame?gid=1068157) |
| 1981 | Garry Kasparov vs Viktor Gavrikov, USSR Championship, Frunze | [1069905](https://www.chessgames.com/perl/chessgame?gid=1069905) |
| 1982 | Lubomir Kavalek vs Garry Kasparov, Bugojno | [1069989](https://www.chessgames.com/perl/chessgame?gid=1069989) |
| 1983 | Anatoly Karpov vs Efim Geller, USSR Championship, Moscow | [1050206](https://www.chessgames.com/perl/chessgame?gid=1050206) |
| 1984 | Lajos Portisch vs József Pintér, Hungarian Championship, Budapest **W** | [1063968](https://www.chessgames.com/perl/chessgame?gid=1063968) |
| 1985 | Anatoly Karpov vs Garry Kasparov, 24th Match Game, Moscow | [1067179](https://www.chessgames.com/perl/chessgame?gid=1067179) |
| 1986 | Garry Kasparov vs Anatoly Karpov, 16th Match Game, Leningrad | [1067209](https://www.chessgames.com/perl/chessgame?gid=1067209) |
| 1988 | Carsten Høi vs Boris Gulko, Thessaloniki Olympiad | [1053943](https://www.chessgames.com/perl/chessgame?gid=1053943) |
| 1989 | Jeroen Piket vs Garry Kasparov, Tilburg | [1070485](https://www.chessgames.com/perl/chessgame?gid=1070485) |
| 1990 | Anatoly Karpov vs Garry Kasparov, World Chess Championship, Lyon, 23rd Match Game | [1067300](https://www.chessgames.com/perl/chessgame?gid=1067300) |
| 1992 | Mikhail Tal vs Joël Lautier, Barcelona | [1089819](https://www.chessgames.com/perl/chessgame?gid=1089819) |
| 1992 | Vasyl Ivanchuk vs Viswanathan Anand, Linares, 1st Match Game | [1060292](https://www.chessgames.com/perl/chessgame?gid=1060292) |
| 1993 | Nigel Short vs Garry Kasparov, PCA World Championship, London, 8th Match Game | [1070680](https://www.chessgames.com/perl/chessgame?gid=1070680) |
| 1995 | Roberto Cifuentes vs Vadim Zvjaginsev, Wijk aan Zee **W** | [1262430](https://www.chessgames.com/perl/chessgame?gid=1262430) |
| 1995 | Veselin Topalov vs Vladimir Kramnik, Belgrade **W** | [1086001](https://www.chessgames.com/perl/chessgame?gid=1086001) |
| 1996 | Deep Blue versus Garry Kasparov, Game 1 **W** | _no id in the list_ |
| 1997 | Deep Blue versus Garry Kasparov, Game 6 **W** | _no id in the list_ |
| 1999 | Garry Kasparov vs Veselin Topalov, Wijk aan Zee **W** | _no id in the list_ |
| 1999 | Garry Kasparov vs The World | [1252350](https://www.chessgames.com/perl/chessgame?gid=1252350) |
| 2000 | Garry Kasparov vs Vladimir Kramnik, Classical World Chess Championship, 3rd Match Game,  **W** | [1252043](https://www.chessgames.com/perl/chessgame?gid=1252043) |
| 2002 | Ruslan Ponomariov vs Vassily Ivanchuk, FIDE World Championship Tournament, Final Match,  | [1240662](https://www.chessgames.com/perl/chessgame?gid=1240662) |
| 2004 | Vladimir Kramnik vs Peter Leko, Classical World Chess Championship, 14th Match Game, Bri **W** | [1311652](https://www.chessgames.com/perl/chessgame?gid=1311652) |
| 2005 | Viswanathan Anand vs Veselin Topalov, Sofia **W** | [1338514](https://www.chessgames.com/perl/chessgame?gid=1338514) |
| 2006 | Sergey Karjakin vs Viswanathan Anand, Corus chess tournament, Round 1, Wijk aan Zee | [1385670](https://www.chessgames.com/perl/chessgame?gid=1385670) |
| 2006 | Vladimir Kramnik vs Veselin Topalov, World Chess Championship, 16th Match Game, Elista | [1431697](https://www.chessgames.com/perl/chessgame?gid=1431697) |
| 2013 | Viswanathan Anand vs Magnus Carlsen, World Championship, Game 9, Chennai | [1737896](https://www.chessgames.com/perl/chessgame?gid=1737896) |
| 2016 | Magnus Carlsen vs Sergey Karjakin, World Championship, Game 16, New York | [1848607](https://www.chessgames.com/perl/chessgame?gid=1848607) |
| 2017 | Bai Jinshi vs Ding Liren, China | [1891363](https://www.chessgames.com/perl/chessgame?gid=1891363) |
| 2019 | Alireza Firouzja vs Karthikeyan Murali, Xingtai | [1964305](https://www.chessgames.com/perl/chessgame?gid=1964305) |
| 2021 | Magnus Carlsen vs Ian Nepomniachtchi, World Chess Championship, Game 6 **W** | _no id in the list_ |
