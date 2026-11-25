# Card Kholo review · 25 November 2026

Three reviewers examined the current backend against the project brief. The first covered identity, SQLite, Flagsmith and scan rules. The second covered Sarvam, calendars, cache retention and demo assets. The third covered HTTP contracts, deployment, documentation, test coverage and the new voice paths.

| Priority | Finding | Resolution |
|---|---|---|
| High | Scan requests could buffer an entire upload or JSON body before checking its size. | The API counts streamed bytes even without a Content-Length header. Oversized requests return 413. |
| High | Live invitation details could enter the demo JSON file and ship in the next Docker image. | The application reads the curated seed at startup. Live reads use a separate ten-minute memory cache. |
| High | Closing square brackets in prose could prevent risky links from being recognized. | URL parsing strips an unmatched closing bracket and preserves IPv6 address brackets. |
| Medium | Empty files and blank messages received an OK verdict. | The scan route rejects both with 422 before classification. |
| Medium | Dotted times could become all-day events, and large print-mode CMYK JPEGs could fail during vision fallback. | The normalizer accepts dotted hour/minute values. The image converter produces RGB JPEGs for CMYK input. |
| Medium | Replacing a container using the documented command discarded identities and scan history. | The image uses a data directory and the run command mounts a reusable named volume. The Sarvam and Flagsmith SDK versions are pinned to those tested. |
| Medium | Helper tests missed HTTP behavior across identify, scan, opened and calendar download. | Offline HTTP tests cover those routes, dangerous-file reader exclusion, empty inputs and size limits. |
| Medium | One failed startup speech request could silence a language until restart. | Missing clips receive two background retries. Successfully prepared clips remain available during retries. |

## Verification and limits

The offline suite passed 17 tests, including requests through FastAPI and the installed Sarvam SDK using a simulated service. The demo PDF matches its seeded hash. Live voice quality, live extraction and Flagsmith dashboard behavior still require provider credentials. Docker Desktop's Linux engine was unavailable for a build or restart test.

The application currently assumes one worker for temporary calendars and audio. A deployment with multiple workers would need shared calendar storage or request affinity to serve the same scan's download reliably. Telegram delivery, incident rollback and host invites remain scheduled phases.
