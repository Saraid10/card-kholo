# Harmless scan fixture

`Shaadi_Card_Priya.pdf.apk` is a harmless ZIP containing a plain-text demo note named `AndroidManifest.xml` and an empty `classes.dex`. It contains no executable code.

Regenerate it with `python demo/make_test_apk.py` and upload it to `POST /api/scan` with an identified user ID. Expect `DANGEROUS` from the archive markers and the filename. With the default packs enabled, `pack_hits` includes `pack_wedding_2026`.

## Sample wedding card

`sample-invite.pdf` is a fictional invitation with a timed Sangeet and an all-day wedding. Its SHA-256 has a manually seeded entry in `cache.json`. Set `DEMO_CACHE=on` before startup to try calendar links without using a Sarvam key. Turn the cache off to exercise live extraction for the same file.
