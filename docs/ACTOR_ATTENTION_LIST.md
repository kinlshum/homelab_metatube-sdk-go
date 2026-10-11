# Actor identity attention list

Use MetaTube Admin2 **LOGS-METATUBE-ACTOR** → request → provider events,
**EMBY-ACTOR-DIC-RESULT**, and **IDENTIFY-ACTOR-WF** for each name. Use JAV-Master
Actor Editor → Emby People maintenance → **Inspect matching People folders**
for artwork ownership. The entries below are observations, not authorization
to merge, delete, or replace Emby records.

| Actor | Tool finding | Current hold |
| --- | --- | --- |
| `AIKA (JAP、1990、あいか)` | Dictionary preview mixed AV-LEAGUE actress 18 with Aika Miura sources and formed `Also known as: 三浦あいか` as a name. The [official T-POWERS AIKA profile :live](https://www.t-powers.co.jp/talent/aika/) and [AV-LEAGUE actress 18 :live](https://www.av-league.com/actress/18.html) both give 1990-08-25, but disagree on height. Actor Editor exact-Person preview also found Yui Miho and a 1992 birth-year alias in saved Emby provider IDs. | Do not link the exact Person, assign movies, publish INI, copy art, or delete folders until the provider IDs and linked movies establish one identity. Resolver parser v9 candidate blocks the bad formation; it has not repaired saved data. |
| `Aika Miura (JAP、三浦あいか)` | Admin2 dictionary tool reads Actor DB revision 1, ID `48d8509e-7589-4878-b709-278168ab7bc0`, with `AIKA（三浦あいか）` and `長谷川優` mapped to this actor. Resolver request `54437525-1c0e-4c89-9dbb-b38b890e7358` took 75.6 seconds and formed `Aika Miura (JAP、1975、三浦あいか)`, but the first dictionary UI request timed out; the second displayed three URLs: [Minnano-AV :live](https://www.minnano-av.com/actress611128.html), [JAV.LINK :live](https://jav.link/jav/aika-miura/), [JAVModel :live](https://javmodel.com/jav/aika-miura/). Minnano reported 1975-11-02 while JAV.LINK reported 1976-12-24. The [Aika Miura profile :live](https://avprofiles.com/1079/) explicitly lists both aliases and a 1975-11-02 birthday; [IMDb :live](https://www.imdb.com/name/nm0594229/) independently lists the 1975-11-02 birthday and Yuu Hasegawa alternative name. The live overview included malformed `熟女) （あいか`; parser candidate now rejects unbalanced labels. The Actor DB canonical omits the birth year. | Keep the qualified `AIKA（三浦あいか）` alias distinct from bare `AIKA`. Review the conflicting birthday and exact Emby Person, provider IDs, and movie evidence before adding a year or copying the alternate folder's fanart. Admin2 must surface the completed resolver result without a timeout/retry. |
| `Aika Natsume (JAP、夏目藍果)` | Admin2 dictionary found [AV-LEAGUE :live](https://www.av-league.com/actress/33649.html), [Minnano-AV :live](https://www.minnano-av.com/actress424687.html), [XsList :live](https://xslist.org/zh/model/122757.html), and [JAVDatabase :live](https://www.javdatabase.com/idols/aika-natsume/). AV-LEAGUE reported 2000-02-02; Minnano and JAVDatabase reported 2000-11-30. Live formed `Aika Natsume (JAP、2000、夏目藍果)` but also printed ambiguous `あいか` / `Aika` aliases and the literal `Blood Type: n/a`. Actor DB revision 1 has the distinct canonical name and no publication receipt. | Review the birthday conflict before adding a date. Resolver and Windmill candidates remove bare `AIKA`/`あいか` from named Aika actors, and the resolver no longer prints `n/a` as a fact. Preserve both Natsume People folders pending exact Person review. |
| `Aika Suzuki (JAP、鈴木あいか)` | Admin2 dictionary loaded Actor DB revision 1 with aliases `北嶋あん` and `鈴木あいか`, then reported resolver unavailable/timed out with zero URLs. The actor request view and individual URL traces had no Suzuki receipt; Graylog search returned no retained lines. A [SETFLIX profile :live](https://setflix.kr/service/actor/view.asp?pk=6396) lists `Aika Suzuki`/`鈴木あいか` and 1991-11-06. Another [profile :live](https://www.cscsh.com/wh/74788.html) relates `北嶋あん` and `鈴木あいか` to `大島あいる` but reports 1991-01-29. These sources do not establish one exact Emby Person. Actor Editor shows canonical Person 43776 with 163 linked items, its `folder.png`, plus an unowned alternate `folder.jpg`. | Hold birthday, alias expansion, video reassignment and art copy until provider profile, exact Person IDs and linked movies resolve the conflict. Resolver candidate now emits an immediate `started` request receipt so a slow lookup appears in Admin2 while it runs. |
| `Aika Yamagishi (JAP、山岸逢花)` | Admin2 dictionary found seven source profiles: [AV-LEAGUE :live](https://www.av-league.com/actress/9376.html), [Minnano-AV :live](https://www.minnano-av.com/actress221691.html), [XsList :live](https://xslist.org/zh/model/358.html), [JAVDatabase :live](https://www.javdatabase.com/idols/aika-yamagishi/), [JAV.LINK :live](https://jav.link/jav/aika-yamagishi/), [JAVModel :live](https://javmodel.com/jav/aika-yamagishi/), and [Babepedia :live](https://www.babepedia.com/babe/Aika_Yamagishi). It formed `Aika Yamagishi (JAP、1992、山岸逢花)` and birthday 1992-11-30, but printed `Nationality: 神奈川県`; height, cup and measurements conflict across sources. The candidate parser classifies the prefecture as birthplace. [Publisher Kodansha :live](https://www.kodansha.co.jp/book/products/0000381896) identifies 山岸あや花 as formerly 山岸逢花 and gives birth date 1992-11-30. Actor DB revision 1 has `山岸あや花` as an alias and no publication receipt. Exact Emby Person 13338 has XsList ID 358, 172 linked items, no saved birthday field and an older overview. The clean People folder contains `folder.jpg` and `folder.png` and is referenced by three Emby Person IDs (13338, 1192462, 1255983); the separate `-imdb-https xslist.org ...` folder has no images or image-reference owner. | Keep the clean folder and all Person records untouched until each linked movie is reviewed. The empty suffixed folder can be considered for verified quarantine only after exact ownership checks and backup. No `-imdb-` suffix may be published as the canonical name. |
| `Aikarin (JAP、1983、あいかりん)` | Admin2 dictionary found [AV-LEAGUE :live](https://www.av-league.com/actress/27.html), [Minnano-AV :live](https://www.minnano-av.com/actress573548.html), and [XsList :live](https://xslist.org/zh/model/3771.html). Their birthday values conflict: 1993-11-03, 1992-03-11, and 1993-11-02 respectively. The resolver formed `Aikarin (JAP、1993、あいかりん)`, but saved Actor DB revision 1 (`08280378-9ebe-43e1-877a-a586d404dbbd`) still has the 1983 name and INI mapping with no publication receipt. Exact Emby Person 729771 has 14 linked items and saved birthday 1993-11-02, while its saved name also says 1983. Its Japanese People folder has `folder.jpg`. The Windmill candidate now aborts enrichment if an existing actor birth year or date conflicts with sourced values; without that guard the database would retain 1983 while receiving a 1993 overview. | Resolve the year/day with identity and movie evidence in Actor Editor before correcting the saved name or publishing. Preserve the existing photo and all 14 links; do not merge, replace, or move files based on name alone. |
| `Aika Yumeno (JAP、1994、夢乃あいか)` | Admin2 dictionary found seven source URLs. [AV-LEAGUE :live](https://www.av-league.com/actress/9657.html), [Minnano-AV :live](https://www.minnano-av.com/actress545220.html), [JAVDatabase :live](https://www.javdatabase.com/idols/aika-yumeno/), and [Babepedia :live](https://www.babepedia.com/babe/Aika_Yumeno) reported 1994-08-26, while [XsList :live](https://xslist.org/zh/model/9.html) reported 1994-08-25 and [JAV.LINK :live](https://jav.link/jav/yumeno-aika/) reported 1993-09-13. The [manufacturer profile :live](https://tameikegoro.jp/actress/detail/245419) also says 1994-08-26. Live resolver still printed 1994-08-25 because its mounted override was stale, and mislabeled `東京都` as nationality. Candidate parser now prefers verified AV-LEAGUE/Minnano birthdays over a conflicting override and treats prefecture as birthplace; source-controlled override is corrected. Actor DB revision 1 is already named correctly but has no publication receipt. | Keep Aika Yumeno separate from bare AIKA and preserve both existing Yumeno People folders. Verify the corrected resolver preview and live mounted override behavior after release before any Emby Identify, INI publication, folder copy, or cleanup. |
| `ANRI (JAP、1991、坂口杏里)` | Admin2 dictionary replay returned no formed source result. Resolver request `b8f2949f-a0ef-45ad-9a92-4adee1a51e5e` ended `not_found` after 75 seconds. Provider trace showed AV-LEAGUE and Minnano search results but zero accepted actor records; XsList bridge returned 404. Actor DB already has the canonical record, revision 1, with no publication receipt. A [Sponichi profile :live](https://www.sponichi.co.jp/person/UDAR10235372/) confirms 1991-03-03 and the `Sakaguchi Anri` romanization, but is not a resolver provider. | Keep for source-profile discovery and exact-match rule review. Do not infer a profile from a generic `ANRI` search. |

Artwork inventory for the Aika family found 50 folders. The canonical AIKA
folder has `folder.png`; a separate Japanese `あいか` folder has `folder.jpg`.
The Aika Miura alternate folder holds `fanart.png`, `fanart1.png`, and
`landscape.png`. A Rin Aikawa `-imdb-` folder holds `fanart.jpg`, `folder.png`,
and `landscape.jpg` and is referenced by two distinct Emby Person IDs. The
Aika Yamagishi `-imdb-` folder has no images. Names and shared ownership alone
do not prove which images belong on a canonical Person; preserve every file
until exact identity and byte-verified backups are established.

## Aika Miura exact-Person check

JAV-Master Actor Editor → Emby People maintenance returned exact Emby Person
`165649`, named `Aika Miura (JAP、三浦あいか)`, with 14 linked library items.
The Person has no saved birthday field, but its overview says **Born August 24,
1990** and lists `佐藤聖羅`, `優木あいか`, and `香川さくら` among its aliases. That
overview resembles the bare `AIKA` identity, whereas the Admin2 dictionary
forms `Aika Miura (JAP、1975、三浦あいか)`. Its saved provider IDs include MetaTube
`Gfriends:三浦あいか`, JavdbActor `J012`, JavLibraryIdol `ke7q`, SextbActress
`aika-miura`, and XsList `824`. Actor Editor → Actor records shows no Actor DB
link and no recorded source URL or field evidence for the Miura record. This is
an **identity contamination hold**, not a date field to fill automatically.
Do not use common folder ownership to move the three fanart files: the saved
Person itself contains mixed facts. Review the 14 linked items and provider IDs
in the tools before editing or linking either actor.

A later Admin2 exact-ID read showed the same Person `165649` renamed to
`Aika Miura (JAP、1975、三浦あいか)` with saved birthday `1975-11-02`,
`MetaTube=Minnano-AV:611128`, and a newly formed overview. The new overview
still contains the malformed `熟女) （あいか` alias. This happened without an
Actor DB Person link or publication receipt in the read-only audit; do not
interpret the name change as verified end-to-end publication or infer that
the earlier mixed identity was safely repaired.

## Aika Suzuki later dictionary result

A later Admin2 lookup for `鈴木あいか` with exact Emby Person `43776` returned
[Minnano-AV](https://www.minnano-av.com/actress107218.html),
[XsList](https://xslist.org/zh/model/4333.html),
[JAV.LINK](https://jav.link/jav/airu-oshima/),
[JAVModel](https://javmodel.com/jav/airu-oshima/), and
[Babepedia](https://www.babepedia.com/babe/Airu_Oshima). The resolver formed
`Aika Suzuki (JAP、1991、鈴木あいか)`: Minnano and Babepedia reported
1991-01-30, XsList 1991-01-29, and JAV.LINK 1991-11-06. Emby Person
`43776` is now saved under the formed name with birthday 1991-01-30 and
`MetaTube=Minnano-AV:107218`. Actor DB revision 1 still has a yearless name,
no exact Person link, and no publication receipt. Keep the birthday/alias and
artwork hold until exact linked movies and source identities are reviewed.

## Aika Yumeno exact-Person check

JAV-Master Actor Editor → Emby People maintenance returned exact Emby Person
`397993`, named `Aika Yumeno (JAP、1994、夢乃あいか)`, with birthday stored as
`1994-08-25T04:00:00Z` and **455 linked library items**. Its provider-ID table
contains XsList `224`, AV-LEAGUE `1617`, Gfriends `上原花恋`, JAVDatabase
`mako-oda`, Babepedia `Mako_Oda`, and `JAV_CUSTOM_PROVIDER=lookup:上原花恋`;
other keys refer to bare `AIKA`. These do not describe one Yumeno identity.
The matching display name and birth year therefore cannot justify linking the
Actor DB row `02156d03-92af-47cf-8660-512d6478fb13` to this Person or
copying photos. The People maintenance preview currently exposes the full ID
table but does not highlight or block this cross-identity contamination. Review
the linked movies and correct the exact Person metadata through the tools
before any link, INI publication, refresh, or People folder move.

## Aika Suzuki exact-Person check

JAV-Master Actor Editor → Emby People maintenance returned exact Emby Person
`43776`, named `Aika Suzuki (JAP、鈴木あいか)`, OriginalTitle `鈴木あいか`, with
162 linked library items at this readback. The saved birthday is
`1991-01-28T05:00:00Z`, while one external profile in the table above reports
1991-01-29 and another reports 1991-11-06. The 13 Emby provider IDs are more
internally coherent than the Miura and Yumeno examples: MetaTube names
`GFriends:鈴木あいか`, XsList is `4333`, SextbActress is `aika-suzuki`, and the
saved JavScraper profile names `Aika Suzuki - 鈴木あいか`. The stored cover URL
contains `大島あいる`, however, so it is still important to check the image and
exact linked movies before merging aliases or moving artwork. Keep the Actor
DB birth year unknown pending a resolved source date; a one-day Emby date
offset is possible but not proven by the tool. The read-only People inventory
found canonical `Aika Suzuki (JAP、鈴木あいか)` owned by Person `43776` with
`folder.png`, an unowned alternate `Aika Suzuki (鈴木あいか)` with `folder.jpg`,
and Japanese `鈴木あいか` owned by **another** Person `502208` with `folder.jpg`.
Do not copy either alternate into the canonical folder based on name alone.

## Aika Natsume split Emby Persons

MetaTube Admin2 → EMBY ACTORS found two exact Natsume-named People records
with library links. `1650960` is named `Aika Natsume (JAP、夏目藍果)`, has four
linked items, no saved birthday, and a single `MetaTube=AV-LEAGUE:33649`
provider ID. Older Person `6995` is named `Aika Natsume (夏目藍果)`, has 29
linked items and saved birthday `2000-02-02T05:00:00Z`. Actor Editor's exact-ID
preview explicitly holds `6995`: it contains
`JAV_CUSTOM_PROVIDER=lookup:Aisha Yuzuki (悠月アイシャ)`, AV-LEAGUE `9620`, XsList
`469`, and `SextbActress=aisha-yuzuki`. This is stronger than a birthday
disagreement: the stored provider identity describes another performer.
Neither Person is safe to delete or merge while linked items remain. The
current People preview shows item counts but not the individual 29 movie
links; a paged linked-item inspector is needed in the Actor Editor before
movie-by-movie correction can proceed through the tool.
The read-only People inventory assigns canonical `Aika Natsume (JAP、夏目藍果)`
with `folder.jpg` to Person `1650960`; legacy `Aika Natsume (夏目藍果)` with
both `folder.jpg` and `folder.png` belongs to Person `6995`. The separate
`夏目藍果` folder is unowned and contains no images. Preserve both owned image
sets while the 29 links and contaminated legacy metadata are investigated.
