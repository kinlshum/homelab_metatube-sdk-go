# Actor identity attention list

Use MetaTube Admin2 **LOGS-METATUBE-ACTOR** → request → provider events,
**EMBY-ACTOR-DIC-RESULT**, and **IDENTIFY-ACTOR-WF** for each name. Use JAV-Master
Actor Editor → Emby People maintenance → **Inspect matching People folders**
for artwork ownership. The entries below are observations, not authorization
to merge, delete, or replace Emby records.

The resolver cache can make an Identify search return in a few hundred milliseconds
without new provider URL calls. A live Aikarin request
`e4e0442e-04ba-41e5-ba65-ea2d3a831fd3` finished in 291 ms and listed
AV-LEAGUE, Minnano-AV and XsList but had no linked URL traces. That observation
alone does not prove a cache hit; the pending resolver candidate now records
`cache_status` (`hit` or `fresh`) and `cache_saved_at` in the result and request
receipt. The pending Admin2 tool displays these fields and marks cached
collection unverified for a fresh-source check. Older receipts have no cache
field and must remain labelled unknown.

| Actor | Tool finding | Current hold |
| --- | --- | --- |
| `AIKA (JAP、1990、あいか)` | Dictionary preview mixed AV-LEAGUE actress 18 with Aika Miura sources and formed `Also known as: 三浦あいか` as a name. The [official T-POWERS AIKA profile :live](https://www.t-powers.co.jp/talent/aika/) and [AV-LEAGUE actress 18 :live](https://www.av-league.com/actress/18.html) both give 1990-08-25, but disagree on height. Actor Editor exact-Person preview also found Yui Miho and a 1992 birth-year alias in saved Emby provider IDs. | Do not link the exact Person, assign movies, publish INI, copy art, or delete folders until the provider IDs and linked movies establish one identity. Resolver parser v9 candidate blocks the bad formation; it has not repaired saved data. |
| `Aika Miura (JAP、三浦あいか)` | Admin2 dictionary tool reads Actor DB revision 1, ID `48d8509e-7589-4878-b709-278168ab7bc0`, with `AIKA（三浦あいか）` and `長谷川優` mapped to this actor. Resolver request `54437525-1c0e-4c89-9dbb-b38b890e7358` took 75.6 seconds and formed `Aika Miura (JAP、1975、三浦あいか)`, but the first dictionary UI request timed out; the second displayed three URLs: [Minnano-AV :live](https://www.minnano-av.com/actress611128.html), [JAV.LINK :live](https://jav.link/jav/aika-miura/), [JAVModel :live](https://javmodel.com/jav/aika-miura/). Minnano reported 1975-11-02 while JAV.LINK reported 1976-12-24. The [Aika Miura profile :live](https://avprofiles.com/1079/) explicitly lists both aliases and a 1975-11-02 birthday; [IMDb :live](https://www.imdb.com/name/nm0594229/) independently lists the 1975-11-02 birthday and Yuu Hasegawa alternative name. The live overview included malformed `熟女) （あいか`; parser candidate now rejects unbalanced labels. The Actor DB canonical omits the birth year. | Keep the qualified `AIKA（三浦あいか）` alias distinct from bare `AIKA`. Review the conflicting birthday and exact Emby Person, provider IDs, and movie evidence before adding a year or copying the alternate folder's fanart. Admin2 must surface the completed resolver result without a timeout/retry. |
| `Aika Natsume (JAP、夏目藍果)` | Admin2 dictionary found [AV-LEAGUE :live](https://www.av-league.com/actress/33649.html), [Minnano-AV :live](https://www.minnano-av.com/actress424687.html), [XsList :live](https://xslist.org/zh/model/122757.html), and [JAVDatabase :live](https://www.javdatabase.com/idols/aika-natsume/). AV-LEAGUE reported 2000-02-02; Minnano and JAVDatabase reported 2000-11-30. Live formed `Aika Natsume (JAP、2000、夏目藍果)` but also printed ambiguous `あいか` / `Aika` aliases and the literal `Blood Type: n/a`. Actor DB revision 1 has the distinct canonical name and no publication receipt. | Review the birthday conflict before adding a date. Resolver and Windmill candidates remove bare `AIKA`/`あいか` from named Aika actors, and the resolver no longer prints `n/a` as a fact. Preserve both Natsume People folders pending exact Person review. |
| `Aika Suzuki (JAP、鈴木あいか)` | Admin2 dictionary loaded Actor DB revision 1 with aliases `北嶋あん` and `鈴木あいか`, then reported resolver unavailable/timed out with zero URLs. The actor request view and individual URL traces had no Suzuki receipt; Graylog search returned no retained lines. A [SETFLIX profile :live](https://setflix.kr/service/actor/view.asp?pk=6396) lists `Aika Suzuki`/`鈴木あいか` and 1991-11-06. Another [profile :live](https://www.cscsh.com/wh/74788.html) relates `北嶋あん` and `鈴木あいか` to `大島あいる` but reports 1991-01-29. These sources do not establish one exact Emby Person. Actor Editor shows canonical Person 43776 with 163 linked items, its `folder.png`, plus an unowned alternate `folder.jpg`. | Hold birthday, alias expansion, video reassignment and art copy until provider profile, exact Person IDs and linked movies resolve the conflict. Resolver candidate now emits an immediate `started` request receipt so a slow lookup appears in Admin2 while it runs. |
| `Aika Yamagishi (JAP、山岸逢花)` | Admin2 dictionary found seven source profiles: [AV-LEAGUE :live](https://www.av-league.com/actress/9376.html), [Minnano-AV :live](https://www.minnano-av.com/actress221691.html), [XsList :live](https://xslist.org/zh/model/358.html), [JAVDatabase :live](https://www.javdatabase.com/idols/aika-yamagishi/), [JAV.LINK :live](https://jav.link/jav/aika-yamagishi/), [JAVModel :live](https://javmodel.com/jav/aika-yamagishi/), and [Babepedia :live](https://www.babepedia.com/babe/Aika_Yamagishi). It formed `Aika Yamagishi (JAP、1992、山岸逢花)` and birthday 1992-11-30, but printed `Nationality: 神奈川県`; height, cup and measurements conflict across sources. The candidate parser classifies the prefecture as birthplace. [Publisher Kodansha :live](https://www.kodansha.co.jp/book/products/0000381896) identifies 山岸あや花 as formerly 山岸逢花 and gives birth date 1992-11-30. Actor DB revision 1 has `山岸あや花` as an alias and no publication receipt. Exact Emby Person 13338 has XsList ID 358, 172 linked items, no saved birthday field and an older overview. The clean People folder contains `folder.jpg` and `folder.png` and is referenced by three Emby Person IDs (13338, 1192462, 1255983); the separate `-imdb-https xslist.org ...` folder has no images or image-reference owner. | Keep the clean folder and all Person records untouched until each linked movie is reviewed. The empty suffixed folder can be considered for verified quarantine only after exact ownership checks and backup. No `-imdb-` suffix may be published as the canonical name. |
| `Aikarin (JAP、1983、あいかりん)` | Admin2 dictionary found [AV-LEAGUE :live](https://www.av-league.com/actress/27.html), [Minnano-AV :live](https://www.minnano-av.com/actress573548.html), and [XsList :live](https://xslist.org/zh/model/3771.html). Their birthday values conflict: 1993-11-03, 1992-03-11, and 1993-11-02 respectively. The resolver formed `Aikarin (JAP、1993、あいかりん)`, but saved Actor DB revision 1 (`08280378-9ebe-43e1-877a-a586d404dbbd`) still has the 1983 name and INI mapping with no publication receipt. Exact Emby Person 729771 has 14 linked items and saved birthday 1993-11-02, while its saved name also says 1983. Actor Editor's exact linked-item table includes `TEK-044 HAT TRICK Aikarin` (2012, item 1192240); a [contemporary debut notice :live](https://avactress.blog.jp/tag/%E3%81%82%E3%81%84%E3%81%8B%E3%82%8A%E3%82%93) names the same debut title and reports 1993-11-03. Its Japanese People folder has `folder.jpg`. The Windmill candidate now aborts enrichment if an existing actor birth year or date conflicts with sourced values; without that guard the database would retain 1983 while receiving a 1993 overview. | The debut evidence supports the 1993 profile but does not explain Minnano's 1992 date or Emby's one-day offset. Resolve the exact source identity/year/day through Actor Editor before correcting the saved name or publishing. Preserve the photo and all 14 links; do not merge, replace, or move files based on name alone. |
| `Aika Yumeno (JAP、1994、夢乃あいか)` | Admin2 dictionary found seven source URLs. [AV-LEAGUE :live](https://www.av-league.com/actress/9657.html), [Minnano-AV :live](https://www.minnano-av.com/actress545220.html), [JAVDatabase :live](https://www.javdatabase.com/idols/aika-yumeno/), and [Babepedia :live](https://www.babepedia.com/babe/Aika_Yumeno) reported 1994-08-26, while [XsList :live](https://xslist.org/zh/model/9.html) reported 1994-08-25 and [JAV.LINK :live](https://jav.link/jav/yumeno-aika/) reported 1993-09-13. The [manufacturer profile :live](https://tameikegoro.jp/actress/detail/245419) also says 1994-08-26. Live resolver still printed 1994-08-25 because its mounted override was stale, and mislabeled `東京都` as nationality. Candidate parser now prefers verified AV-LEAGUE/Minnano birthdays over a conflicting override and treats prefecture as birthplace; source-controlled override is corrected. Actor DB revision 1 is already named correctly but has no publication receipt. | Keep Aika Yumeno separate from bare AIKA and preserve both existing Yumeno People folders. Verify the corrected resolver preview and live mounted override behavior after release before any Emby Identify, INI publication, folder copy, or cleanup. |
| `ANRI (JAP、1991、坂口杏里)` | Admin2 dictionary replay returned no formed source result. Resolver request `b8f2949f-a0ef-45ad-9a92-4adee1a51e5e` ended `not_found` after 75 seconds. Provider trace showed AV-LEAGUE and Minnano search results but zero accepted actor records; XsList bridge returned 404. Actor DB already has the canonical record, revision 1, with no publication receipt. A [Sponichi profile :live](https://www.sponichi.co.jp/person/UDAR10235372/) confirms 1991-03-03 and the `Sakaguchi Anri` romanization, but is not a resolver provider. | Keep for source-profile discovery and exact-match rule review. Do not infer a profile from a generic `ANRI` search. |

The 2026-10-11 Admin2 **bare `あいか`** replay is another concrete search-rank
failure. Resolver request `4c940b1f-cd77-4f61-8c84-7d68f134563e` from
Admin2 `192.168.10.167` ended `not_found` after 75,007 ms with no formed name
or accepted source row. Its exact linked MetaTube 1 run
`5f8edf54-66ea-4063-b971-2f3d94db0218` had 17 broad search results and
selected AV-LEAGUE ID `9657`, the separate **Aika Yumeno** profile, even
though the saved Actor DB row is `AIKA (JAP、1990、あいか)` with no Person link or
publication receipt. This search is an Admin2 replay, not native Emby Apply.
The resolver candidate now rejects a bare `AIKA`/`あいか` profile unless its
Japanese subject is exactly `あいか` and its sourced birth year is 1990,
including when a saved Actor DB identity exists. Do not fill the AIKA source
table with Yumeno's URL or propagate its metadata to Person `1195996`.

JAV-Master 2.1.97's read-only **Compare two exact Emby Persons** paired
Miura `165649` against bare AIKA `1195996`. The former now has a saved
1975-11-02 birthday and 14 movie links; the latter has **821** links and a
saved 1990 birth year. The bare record's provider table contains
`Gfriends=美保結衣`, `JAV_CUSTOM_PROVIDER=lookup:Yui Miho (美保結衣)`,
`babepedia=Yui_Miho`, and `javdatabase=yui-miho`, plus IDs and an
overview from other names. Its `AV-LEAGUE=8822` differs from the verified
bare-AIKA profile 18. Only the first 100 of 821 linked movies were visible
in the comparison, so an apparent lack of shared links is **not** proof.
Examples of exact Miura movie links were `ADN-076` item `1454975` and
`JUC-922` item `1609710`; the bare AIKA sample included `ABG-006`
item `1457608` and `AVSW-050` item `1172992`. Resolve the mismatched
provider IDs and review all movie pages through Actor Editor before any
Person link, cast rewrite, metadata refresh, or artwork copy.

Artwork inventory for the Aika family found 50 folders. The canonical AIKA
folder has `folder.png`; a separate Japanese `あいか` folder has `folder.jpg`.
The Aika Miura alternate folder holds `fanart.png`, `fanart1.png`, and
`landscape.png`. A Rin Aikawa `-imdb-` folder holds `fanart.jpg`, `folder.png`,
and `landscape.jpg` and is referenced by two distinct Emby Person IDs. The
A fresh Admin2 replay for `山岸逢花` on 2026-10-11 returned only three live
source rows (Babepedia, JAV.LINK, JAVModel), although exact Emby Person `13338`
retains seven source IDs/links from a prior Identify. The resolver's current
source search is therefore incomplete for this replay; saved Emby IDs are
readback evidence, not freshly verified dictionary rows. The Babepedia row
also supplied `32B show conversions - UK: 32B, EU: 70B, AU: 10B, JP: 70B`
as `cup_size`. The candidate parser now reduces that field to `B` and tests it.
Do not publish the three-source replay as a complete seven-source enrichment.

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

## Noa Aikawa needs an Actor DB identity

Admin2 dictionary for `愛川のあ` returned
[Minnano-AV](https://www.minnano-av.com/actress436242.html),
[JAVDatabase](https://www.javdatabase.com/idols/noa-aikawa/), and
[XsList](https://xslist.org/zh/model/13149.html). Minnano and JAVDatabase
reported 1988-08-08; XsList reported 1988-08-07. The live resolver formed
`Noa Aikawa (JAP、1988、愛川のあ)` but still printed `Blood Type: n/a`. Exact Emby
Person `1655277` has one linked item, while the read-only Admin2 Actor DB
trace found no exact record or publication receipt. The JAV-Master Actor
Editor standalone Person inspector is live in 2.1.96. It identifies the sole
linked item as compilation `GAS-223` (Emby item `1606580`,
`MetaTube=JavBus:GAS-223`), with Noa Person `1655277` in a 27-Person cast.
That broad compilation cast is insufficient by itself to create/link a new
canonical identity or move an image; verify the provider cast/profile first.

## Aikawa Mika source and saved-Person conflict

Admin2 dictionary for `藍川美夏` returned
[AV-LEAGUE](https://www.av-league.com/actress/45.html),
[JAVDatabase](https://www.javdatabase.com/idols/mika-aikawa/),
[Minnano-AV](https://www.minnano-av.com/actress136293.html), and
[XsList](https://xslist.org/en/model/439.html). The displayed birthday values
are 1988-02-10 (AV-LEAGUE), 1988-06-29 (XsList), and 1988-06-30
(Minnano/JAVDatabase). The live resolver forms
`Aikawa Mika (JAP、1988、藍川美夏)`, while XsList presents the Western name as
`Mika Aikawa`. The [ATTACKERS official actress index](https://attackers.net/actress/a)
lists `藍川美夏` as `AIKAWA MIKA` in Japanese surname-first order. The
source-controlled resolver candidate therefore forms `Mika Aikawa` without
overriding the disputed birthday. The resolver container reads the mounted
`/data/overrides.json`, while the scoped resolver image deploy script preserves
that mount. Release verification must compare and safely update the mounted
override before claiming this name fix is live. The live
overview also accepts `なつみさん33歳 夫に内緒で他人棒SEX` as an alias, prints
`Blood Type: n/a`, and labels Osaka prefecture as nationality. Exact Emby
Person `36375` has 33 linked items and saved birthday 1988-02-10 with the
polluted overview; the Actor DB trace found no exact identity or publication
receipt. Review the source identities and linked movies before importing an
Actor DB record, changing Emby, publishing INI, or moving People artwork.

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

The later Admin2 Emby search also found Person `1193369`, named `夢乃あいか`,
with no linked movies and a saved 1994-08-25 birthday. It is **not** a safe
zero-link delete: Actor Editor shows that its Japanese-name People folder
owns a custom `folder.jpg`, while the 455-link Person `397993` owns a separate
canonical-folder `folder.png`. The zero-link Person also has conflicting
`XsList=20` versus XsList URL `/9.html` and `javtube=GFriends:AIKA` IDs.
Keep both Person records and photos until exact identity and artwork backup
are verified. The local Admin2 candidate now disables its zero-link-only
delete path; owner review and deployment remain pending.

The 2.1.97 Actor Editor exact-Person comparison confirms `397993` has
**455** movie links while `1193369` has zero, but the 455-link record's
saved provider IDs are still contaminated: `AV-LEAGUE=1617`,
`Gfriends=上原花恋`, `JAV_CUSTOM_PROVIDER=lookup:上原花恋`,
`JAVDatabase=mako-oda`, and `Babepedia=Mako_Oda`. This is not the
verified Yumeno AV-LEAGUE profile 9657. The comparison displayed only the
first 100 of 455 links, including several titles naming bare AIKA; do not
assign all 455 movies to Yumeno or delete the zero-link Japanese Person.
The new isolated Actor Editor candidate adds 100-movie comparison windows
so every exact item-ID page can be inspected in the UI before a decision.

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

The first read of `6995` found `lookup:Aisha Yuzuki`, AV-LEAGUE `9620`, and
XsList `469`, while another Natsume Person `1650960` had four links. A later
Identify changed the live state without this audit writing it: Admin2 on
2026-10-11 now reads `6995` as `Aika Natsume (JAP、2000、夏目藍果)`, birthday
2000-02-02, with the matching AV-LEAGUE `33649`, Minnano `424687`, XsList
`122757`, and JAVDatabase `aika-natsume` IDs. The wrong Aisha provider is
absent in that readback. Actor Editor then showed `6995` with 33 mixed movie
links and Person `1650960` with zero links. The change's native Identify
trigger, exact cast corrections, and publication receipt were not verified.
Admin2's fresh source replay still conflicts on birth date: AV-LEAGUE says
2000-02-02, while Minnano/JAVDatabase say 2000-11-30. No Actor DB Person link
or publication receipt exists. The current People folder inventory gives
`folder.png` in the 2000-named folder to `6995` and `folder.jpg` in a
different undated folder to `1650960`. Preserve both image sets and use the
Actor Editor's paged linked-item inspector before any movie-by-movie change.

The 2.1.97 read-only comparison of these exact IDs shows `6995` with 33
links and `1650960` with zero. The 33-link list includes a direct debut
`EBOD-808` (item `1451383`) and `GVH-315` (item `1608140`), but also
`BBAN-195` (item `1639051`), whose title names Seira Hoshisaki and
Ai Hoshina, and `KTKC-053` (item `1623886`), whose title names Maika.
Titles alone cannot decide each cast entry. The isolated comparison-tool
candidate exposes each movie's provider IDs and cast inside the same row,
so these particular links can be checked before reassigning.

## Maika Hoshizaki duplicate source profiles and Emby Persons

The live Admin2 dictionary replay for `星咲マイカ` formed
`Maika Hoshizaki (JAP、1987、星咲マイカ)` by taking a 1987-11-30 birthday from
one Minnano profile. Its conflict list also contained 1996-07-15 from
Minnano/JAV.LINK/JAVDatabase and 1996-07-14 from XsList. The displayed
Minnano profile `https://www.minnano-av.com/actress623867.html` is explicitly
headed `星咲マイカ` and lists 1996-07-15. The previous Admin2 table collapsed
multiple Minnano profiles into one provider row, hiding the dissenting
profile's ID and URL. The resolver candidate now holds an unresolved
multi-year conflict, or excludes a singleton outlier only when an exact-name
profile and another independent provider corroborate the same year. It
returns every profile row and its acceptance/rejection reason for Admin2.

The candidate also checks material **same-year** date disagreements before
formation. For Suzuki, a distant November JAV.LINK date is excluded only when
the exact Japanese-name profile and another provider corroborate the January
date; a one-day XsList difference stays visible. For Natsume, AV-LEAGUE and
Minnano both name the exact Japanese identity yet disagree by months, so the
resolver returns an identity-review hold rather than selecting a birthday by
priority. These are regression-tested rules, not claims about a deployed
resolver or a completed Emby cleanup.

Live Emby search returned two linked Persons with the same clean name:
`12094` has 20 linked items and saved birthday 1996-07-14; `1129000` has
nine linked items. Actor DB `a496d41e-2c06-4273-bb3f-c85b093cbdd6` has
no exact Person link or publication receipt. The clean People folder with
`folder.jpg` is owned by `12094`; an unowned Japanese folder has no image.
Do not merge the Persons, reassign movies, overwrite artwork, or publish the
1987 resolver result. Inspect both exact Persons and movie IDs through the
tools once the exact-name finder and profile-level source table are deployed.

JAV-Master 2.1.97's read-only exact-Person comparison now shows both
`12094` and `1129000` saved as `Maika Hoshizaki (JAP、星咲マイカ)` with the
same 1996-07-14 Emby date and the same XsList profile `36532`; provider
keys differ mainly in capitalization. It displayed all 20 versus nine
movie links and found no identical Emby item IDs. The nine-link Person
includes `JUY-797` item `1423172`, but also `COSQ-022` item `1444380`
whose title names other performers. Common IDs/name/date make these
**candidate** duplicates, not an automatic merge: verify every movie's
provider cast and the custom `folder.jpg` ownership before any cast move
or Person deletion. The comparison is complete for this pair because both
movie totals are below 100.
