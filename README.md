# Smart-home catalog

A standalone, unbranded catalog with exactly two categories: **Devices** and **Dashboard**.

## Devices

- Every built-in component/integration manifest from stable core release **2026.10.4**: **1,523 routes**, including services, helpers and internal tools.
- Every repository in the pinned default HACS backend integration list: **4,286 repositories**. All entries remain included, including 21 with unavailable descriptive metadata in the snapshot.
- **615** retained source-backed device-brand lists with **6,684** documented device or product-family listings.
- **3** independently researched OnStar connection projects outside the HACS default list; requirements and legacy/API failure warnings are preserved.
- **6,386 combined search entries**. Matching built-in integration names and physical-brand lists can share a row. Community integration repositories keep separate source identities, including incompatible alternatives; route counts and search-row counts are not unique-device totals.

Ford/FordPass, Lincoln, OnStar, General Motors, Chevrolet, GMC, Cadillac and Buick aliases are searchable. Aliases aid discovery and are not manufacturer-wide model-support claims.

## Dashboard

- **956** entries from the pinned HACS default Dashboard category.
- **18** independently researched frontend projects outside that default list.
- Separate search, source filter, sorting and pagination. Entries open the original integration documentation or project page in a new browser tab; entries with multiple routes show a choice of links instead of a custom details popup.

## Open

Use the GitHub Pages site for full browser functionality. Downloaded HTML attachment previews on phones may block JavaScript. `index.html` is also self-contained and works offline in a full browser. `.nojekyll` serves it directly without template processing.

There are no business contact details, analytics or third-party runtime dependencies in the catalog. Integration links open external documentation or source projects in a new tab. Multiple connection routes remain separate options; a documentation link is not an exact-model support claim.

## Scope and provenance

The built-in registry is derived from every `homeassistant/components/*/manifest.json` in the pinned stable core **2026.10.4** source archive. Grouped catalog names and aliases are retained from that release's generated integration metadata. The default HACS integration and Dashboard lists are pinned to `hacs/default` commit **833345ca3167ab105ae5af612f739fd0f792ef4e**, with descriptive metadata joined by exact case-insensitive repository ID from HACS Data. Source dates and registry IDs are embedded in the catalog.

This is an offline snapshot, not a live feed, installer, security review or runtime test. There is no exhaustive registry for independently published custom projects; those entries are a clearly qualified researched selection, not a claim of all custom software everywhere.

Entries without reviewed exact-model device lists say so explicitly. Integration listing does not establish device support. Local/cloud labels are based on source metadata or reviewed documentation, not guessed from names. Model, firmware, region, accounts, subscription entitlements, API changes and extra hardware may limit operation. Broken or legacy routes can remain in a source registry; their documented warnings are not an endorsement.

Project names and metadata remain attributable to their respective authors. No manufacturer or platform endorsement is claimed.

## Connection labels and audit

Connection labels describe the **documented route**, not a successful installation test or a manufacturer-wide compatibility promise:

- **Local:** direct device/hub communication over LAN, Bluetooth or a documented local radio/bridge route. A local API is local; the word `API` alone does not establish cloud use.
- **Cloud:** communication through a documented vendor-hosted internet endpoint or service.
- **Local & cloud:** the entry contains separate documented options; not a promise that every feature works offline.
- **Virtual / calculated:** calculations or internal helpers with no independent device-communication route.
- **Platform / provider-dependent:** an abstract entity platform (such as sensor or light); location depends on the implementing integration.
- **Connection type unverified:** insufficient evidence of location. It does **not** mean broken or incompatible. `assumed_state` describes limited state feedback, not local/cloud location.

The additional audit checks exact repository/domain manifests rather than guessing from project names. `data/connection-manifests.json` records each attempted source URL, retrieval timestamp, downloaded content SHA-256, relevant manifest fields, and unavailable-source errors. These are repository declarations, not independent runtime tests; HEAD-based sources can change after retrieval. Unsupported or malformed class values are preserved in the evidence, not silently normalized.

Gaps are researched individually in upstream documentation and code. `data/reviewed-connections.json` records the source and connection evidence, with route-specific caveats. Location may be documented without a known polling/push mechanism; in that case only location is assigned. `data/core-platform-manifests.json` retains pinned manifests for abstract entity platforms. The original core/HACS registry membership pins remain unchanged; newer repository connection evidence is an explicitly separate snapshot.

Local communication can still require internet during initial setup, accounts, firmware downloads, or additional hardware. Optional cloud features and different firmware/model/region variants may differ. MQTT or self-hostable server software alone does not prove where a user's broker/server runs.

Reapply checked-in evidence offline:

```sh
python3 scripts/audit_connections.py --apply
python3 -m unittest discover -s tests -v
```

Running the audit script without `--apply` collects current candidate manifests into an ignored local JSONL cache; it does not silently replace the checked-in research. Python's standard library is sufficient for the audit; UI regression tests also require Node and execute the page's actual JavaScript.

## Publication

GitHub Pages publishes the root of `main`. Updating `index.html` and pushing to `main` updates this separate catalog site. It is independent of any business website.
