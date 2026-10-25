# Smart-home catalog

A standalone, unbranded catalog of smart-home devices and dashboard frontend add-ons.

- Devices: 615 brands with 6,684 documented device or product-family listings.
- Dashboards: 956 entries from the pinned HACS default Dashboard category plus 18 independently researched frontend projects.
- Separate searchable tabs, connection/source filters, pagination and detail dialogs.
- No business contact details, outbound links, analytics or third-party runtime dependencies.

## Open

Visit the repository's GitHub Pages site. Opening a downloaded HTML attachment in a phone document preview can block JavaScript; use the hosted page for full functionality.

`index.html` is also a self-contained HTML file usable in a full browser offline. `.nojekyll` serves it directly without template processing.

## Scope and provenance

This is an offline data snapshot, not a live feed or software installer. Device snapshot dates and requirements are retained inside the catalog. The HACS Dashboard list was pinned to `hacs/default` commit `833345ca3167ab105ae5af612f739fd0f792ef4e`; metadata was joined from the HACS Data plugin dataset. The independently researched projects are a non-exhaustive selection outside that default list; they may support HACS custom-repository installation.

Catalog inclusion is not a compatibility, maintenance, security or offline-operation guarantee. Check exact models, firmware, region, hardware prerequisites and each project's requirements before installation. Project names and source metadata remain attributable to their respective authors. No platform or manufacturer endorsement is claimed.

## Publication

GitHub Pages publishes the root of the `main` branch. Updating `index.html` and pushing to `main` updates this separate catalog site. It is independent of any business website.
