# Single-name actor identity guard

The Admin2 dictionary preview for `AIKA` exposed one resolver request that combined
AV-LEAGUE actress `18` with XsList `824` and Babepedia `Aika_Miura`. Those
profiles did not establish one person: the supplied Japanese names and birth
years disagreed. The resolver formed the invalid name
`AIKA (JAP、1990、Also known as: 三浦あいか)`.

Parser version 9 invalidates earlier resolver cache entries. For a one-word
Latin search such as `AIKA`, the resolver now requires a Japanese profile
identity and refuses to merge profiles with different Japanese names or birth
years. The no-match response exposes an `identity conflict` or
`identity unverified` status and the candidate source URLs. A source caption
beginning `Also known as:` cannot become the Japanese component of a name.
Two-word names and exact Japanese-name searches retain their existing behavior.
Legacy Emby names with a trailing `-imdb-...` provider/URL suffix are stripped
before lookup and before accepting a preferred canonical name. This prevents
that suffix from being reused in a newly formed People-folder name; existing
folders are only inventoried and are never renamed by the resolver.

To investigate without direct log or database reads, use MetaTube Admin2
**LOGS-METATUBE-ACTOR** to select the Identify request, expand its provider
URL traces, then open **EMBY-ACTOR-DIC-RESULT** and **IDENTIFY-ACTOR-WF** for
the same actor and exact Emby Person ID. Keep conflicting profiles in the
attention list and resolve their identity before changing Actor DB, INI, Emby
Person links, videos, or People-folder art. The resolver deployment itself
must not modify any of those records or files.
