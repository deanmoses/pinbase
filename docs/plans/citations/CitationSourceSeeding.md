# Citation Source Pre-population

We want to pre-populate the system with all the Citation Sources relevant to Pinbase. Pinball books, pinball magazines, pinball websites.

## The Case for Pre-Seeding

We believe that pre-seeding the database with Citation Sources will:

- **Take an enormous burden off citation creation**. It should be MUCH easier to create a citation since you don't have to create the source, and especially much easier with the inline autocomplete UI we're planning. One of the biggest learnings from Wikipedia is that we _must_ make it easier to create citations - it's one of Wikipedia's biggest pains and a major impediment to editor retention.
- **Reduce one-off creation**. Bias people towards re-use of Citation Sources from day one, so that we don't have one-off Citation Sources entering the system.
- **Reduce duplicate creation**. If most sources already exist, and most citation entry is selecting an existing source, we train people to not create duplicates. Also, during the ingest/seeding process we can create rich metadata and synonyms/aliases so that it's easy to find the right source.
- **Avoiding retrofit cost**. If Pinbase wants shared sources, seeding early is much cheaper than trying to normalize thousands of ad hoc sources later. Preventing duplicate creation is cheaper than building workflows to merge and repair them afterward.
- **Stronger editorial consistency**. Seeding lets Pinbase decide canonical naming, types, and scope centrally instead of leaving those choices to whoever happens to cite something first.
- **Better hierarchy from day one**. Many source families need structure, not just flat names: publication → issue → article, work → edition, documentation set → manual. That hierarchy is hard to build correctly during casual authoring.
- **Better access-link enrichment**. Pre-seeded sources can accumulate scans, archive links, and canonical URLs over time, making sources more inspectable for readers and editors.

See [CitationSharing.md](CitationSharing.md) for more of the Wikipedia learnings.

## Feasibilty of Pre-seeding

### Books

Pre-seeding books appears to be very tractable. The likely scale is only several dozen distinct pinball books, and plausibly low hundreds once you include editions, translations, and adjacent technical/reference works.

A quick sample across Google Books, Open Library, and WorldCat surfaced bounded corpus of obvious pinball books, including:

- [_Pinball!_](https://www.amazon.com/dp/0525474811) (Roger C. Sharpe, 1977)
- _Pinball wizardry_ (Robert Polin, 1979)
- [_Pinball Machines_](https://www.amazon.com/dp/0764308955) (Heribert Eiden and Jürgen Lukas, 1992)
- [_The Complete Pinball Book_](https://www.amazon.com/dp/0764337858) (Marco Rossignoli, 1999/2002/2011)
- [_The Pinball Compendium: Electro-Mechanical Era_](https://www.amazon.com/dp/0764330284) (Michael Shalhoub, 2008)
- [_Your Pinball Machine_](https://www.amazon.com/dp/0764361805) (B. B. Kamoroff, 2021)
- [_Pinball: A Graphic History of the Silver Ball_](https://www.amazon.com/dp/125024921X) (Jon Chad, 2024)
- _Pinball: A Quest for Mastery_ (Tasker Smith, 2026)

### Print Magazines

Pre-seeding paper magazines/newsletters/fanzines appears to be very tractable. It appears to be in the low dozens at most.

A quick AI search surfaced a small, bounded set of obvious pinball-first or pinball-relevant print titles, including:

- _PinGame Journal_ - hobbyist pinball periodical, active since May 1991. <https://en.wikipedia.org/wiki/PinGame_Journal>
- _Pinball Magazine_ - current print pinball glossy edited by Jonathan Joosten; first issue launched in August 2012. <https://www.pinball-magazine.com/?page_id=583>
- _Pinhead Classified_ - pinball fanzine; defunct by January 1999, with final issue No. 29 noted in the rec.games.pinball FAQ. <https://gamefaqs.gamespot.com/pinball/916391-pinball-hardware/faqs/1325>
- _Pinball Trader Newsletter_ - earlier collector publication that predates _PinGame Journal_; active by the late 1980s and still represented in 1991-1992 holdings. <https://library.arcade-museum.com/magazine/pinball-trader>
- _GameRoom Magazine_ - general gameroom hobbyist magazine with steady pinball coverage; January 1989 to July 2016, with a short relaunch after 2014. <https://en.wikipedia.org/wiki/Gameroom_magazine>
- _Play Meter_ - major coin-op trade magazine with regular pinball coverage; founded in 1974 and ended in 2018. <https://en.wikipedia.org/wiki/Play_Meter>
- _RePlay_ - major coin-op trade magazine with regular pinball coverage; founded in October 1975 and still active. <https://www.replaymag.com/about-replay/about-replay-magazine/>
- _Coin Slot_ - enthusiast coin-op magazine with pinball coverage; published from September 1974 into at least the late 1990s in library holdings. <https://library.arcade-museum.com/magazine/coin-slot>
- _Canadian Coin Box_ - long-running Canadian coin-op trade magazine with pinball coverage; library holdings run from 1953 into 2000. <https://library.arcade-museum.com/magazine/canadian-coin-box>
- _Coin-Op Newsletter_ - hobbyist coin-op publication with some pinball relevance; library holdings include issues from 1988-1991 and later. <https://library.arcade-museum.com/magazine/coin-op-newsletter>
- _Coin Drop International_ - electromechanical coin-op magazine; the 1999 rec.games.pinball FAQ specifically notes its coverage of older and pre-flipper pinball. <https://gamefaqs.gamespot.com/pinball/916391-pinball-hardware/faqs/1325>

If scoped to pinball-dedicated paper publications, the universe appears to be well under twenty roots; if expanded to broader coin-op trade titles with regular pinball coverage, it is still likely only low dozens.

### Major Pinball Websites

Pre-seeding the major pinball websites appears to be highly tractable. We'd pre-seed site/publication/provider roots, not every article, forum post, or product page. The root-site universe appears to be only low dozens overall, with current manufacturer roots in the single digits to low teens.

- **Reference / database / community sites**:
  - _IPDB_ - the long-running Internet Pinball Database, a comprehensive machine encyclopedia now hosted at ipdb.org. <https://www.ipdb.org/aboutus.html>
  - _OPDB_ - the Open Pinball Database, a current API-first machine archive. <https://opdb.org/about>
  - _Pinside_ - the largest general-purpose pinball community/forum/marketplace site. <https://pinside.com/pinball/help/>
  - _PinWiki_ - community-maintained pinball wiki, launched April 21, 2011. <https://www.pinwiki.com/wiki/index.php/PinWiki%3AAbout>
  - _Kineticist_ - digital publication and community resource, launched in 2022. <https://www.kineticist.com/about>
  - _Pinball News_ - independent pinball news and reporting site, started at the end of 1999. <https://www.pinballnews.com/site/2000/01/01/about-pinball-news/>
  - _This Week in Pinball_ - weekly pinball news site/newsletter, now part of Kineticist. <https://twip.kineticist.com/>
- **Manufacturer sites**:
  - _Stern Pinball_ - current major manufacturer; official site includes company history, game pages, and support materials. <https://sternpinball.com/About/>
  - _Jersey Jack Pinball_ - current major manufacturer founded in 2011. <https://jerseyjackpinball.com/pages/company>
  - _American Pinball_ - current major manufacturer. <https://www.american-pinball.com/about>
  - _Spooky Pinball_ - current boutique manufacturer; company founded February 1, 2013. <https://www.spookypinball.com/about-us/>
  - _Multimorphic_ - current manufacturer/platform company; began as PinballControllers.com in 2009. <https://www.multimorphic.com/about/>
  - _Pinball Brothers_ - current European manufacturer, formed in 2020. <https://www.pinballbrothers.com/about-us/>
  - _Chicago Gaming Company_ - current remake/manufacturing company with official product and service resources. <https://www.chicago-gaming.com/>
