# Actor identity attention list

Use MetaTube Admin2 **LOGS-METATUBE-ACTOR** → request → provider events,
**EMBY-ACTOR-DIC-RESULT**, and **IDENTIFY-ACTOR-WF** for each name. Use JAV-Master
Actor Editor → Emby People maintenance → **Inspect matching People folders**
for artwork ownership. The entries below are observations, not authorization
to merge, delete, or replace Emby records.

| Actor | Tool finding | Current hold |
| --- | --- | --- |
| `AIKA (JAP、1990、あいか)` | Dictionary preview mixed AV-LEAGUE actress 18 with Aika Miura sources and formed `Also known as: 三浦あいか` as a name. The [official T-POWERS AIKA profile :live](https://www.t-powers.co.jp/talent/aika/) and [AV-LEAGUE actress 18 :live](https://www.av-league.com/actress/18.html) both give 1990-08-25, but disagree on height. Actor Editor exact-Person preview also found Yui Miho and a 1992 birth-year alias in saved Emby provider IDs. | Do not link the exact Person, assign movies, publish INI, copy art, or delete folders until the provider IDs and linked movies establish one identity. Resolver parser v9 candidate blocks the bad formation; it has not repaired saved data. |
| `ANRI (JAP、1991、坂口杏里)` | Admin2 dictionary replay returned no formed source result. Resolver request `b8f2949f-a0ef-45ad-9a92-4adee1a51e5e` ended `not_found` after 75 seconds. Provider trace showed AV-LEAGUE and Minnano search results but zero accepted actor records; XsList bridge returned 404. Actor DB already has the canonical record, revision 1, with no publication receipt. A [Sponichi profile :live](https://www.sponichi.co.jp/person/UDAR10235372/) confirms 1991-03-03 and the `Sakaguchi Anri` romanization, but is not a resolver provider. | Keep for source-profile discovery and exact-match rule review. Do not infer a profile from a generic `ANRI` search. |

Artwork inventory for the Aika family found 50 folders. The canonical AIKA
folder has `folder.png`; a separate Japanese `あいか` folder has `folder.jpg`.
The Aika Miura alternate folder holds `fanart.png`, `fanart1.png`, and
`landscape.png`. A Rin Aikawa `-imdb-` folder holds `fanart.jpg`, `folder.png`,
and `landscape.jpg` and is referenced by two distinct Emby Person IDs. The
Aika Yamagishi `-imdb-` folder has no images. Names and shared ownership alone
do not prove which images belong on a canonical Person; preserve every file
until exact identity and byte-verified backups are established.
