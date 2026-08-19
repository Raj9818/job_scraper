import asyncio

from stealth_browser import StealthSession
from scrapers import naukri
import db
import config


async def run_naukri():

    keyword = config.KEYWORD
    location = config.LOCATION
    max_pages = config.MAX_PAGES
    urls_limit = config.URLS_LIMIT

    run_id = db.start_scrape_run("naukri")

    session = StealthSession()
    await session.start()

    consecutive_failures = 0

    total_saved = 0
    total_found = 0

    pages_attempted = 0
    pages_succeeded = 0
    failures = 0

    final_status = "completed"
    final_note = ""

    try:

        for page_num in range(1, max_pages + 1):

            # Stop when URL/listing limit is reached
            if total_found >= urls_limit:
                print(f"[limit] URL limit reached: {urls_limit}")
                break

            pages_attempted += 1

            # Rotate browser identity if required
            if session.needs_rotation():

                await session.close()

                session = StealthSession()

                await session.start()

            url = naukri.build_search_url(
                keyword,
                location,
                page_num
            )

            try:

                html = await naukri.fetch_page(
                    session,
                    url
                )

                listings = naukri.parse_listings(
                    html,
                    selector_version=config.NAUKRI_SELECTOR_VERSION
                )

                # ------------------------------------------------
                # Successful extraction
                # ------------------------------------------------

                if listings:

                    consecutive_failures = 0

                    # Number of listings still allowed
                    remaining = urls_limit - total_found

                    # Do not exceed URL limit
                    listings = listings[:remaining]

                    pages_succeeded += 1

                    total_found += len(listings)

                    saved = db.save_listings(listings)

                    total_saved += saved

                    print(
                        f"[page {page_num}] "
                        f"{len(listings)} listings found, "
                        f"{saved} new"
                    )

                    db.log_health(
                        "naukri",
                        "healthy",
                        f"page {page_num}: "
                        f"{len(listings)} found, "
                        f"{saved} new"
                    )

                # ------------------------------------------------
                # Empty extraction
                # ------------------------------------------------

                else:

                    print(
                        f"[page {page_num}] "
                        f"WARNING: ZERO LISTINGS EXTRACTED"
                    )

                    consecutive_failures += 1
                    failures += 1

                    db.log_health(
                        "naukri",
                        "degraded",
                        f"empty parse on page {page_num}"
                    )

                session.request_count += 1

            except Exception as e:

                consecutive_failures += 1
                failures += 1

                print(
                    f"[ERROR] Page {page_num} failed: "
                    f"{type(e).__name__}: {e}"
                )

                db.log_health(
                    "naukri",
                    "error",
                    f"page {page_num}: "
                    f"{str(e)[:200]}"
                )

            # ------------------------------------------------
            # Circuit breaker
            # ------------------------------------------------

            if (
                consecutive_failures
                >= config.MAX_CONSECUTIVE_FAILURES
            ):

                final_status = "blocked"

                final_note = (
                    "Circuit breaker tripped after "
                    f"{consecutive_failures} "
                    "consecutive failures"
                )

                db.log_health(
                    "naukri",
                    "blocked",
                    final_note
                )

                break

            # ------------------------------------------------
            # Stop immediately if URL limit was reached
            # ------------------------------------------------

            if total_found >= urls_limit:
                print(f"[limit] URL limit reached: {urls_limit}")
                break

            await session.human_pause()

        # --------------------------------------------------------
        # Normal completion
        # --------------------------------------------------------

        if not final_note:

            final_note = (
                f"Run completed: "
                f"{pages_succeeded}/"
                f"{pages_attempted} pages succeeded"
            )

    except Exception as e:

        final_status = "error"

        final_note = (
            f"Run-level error: "
            f"{type(e).__name__}: "
            f"{str(e)[:200]}"
        )

        raise

    finally:

        await session.close()

        db.update_scrape_run(
            run_id,
            status=final_status,
            pages_attempted=pages_attempted,
            pages_succeeded=pages_succeeded,
            listings_found=total_found,
            listings_saved=total_saved,
            failures=failures,
            note=final_note,
            finished=True,
        )

    print(
        f"Done. {total_saved} new listings saved."
    )


if __name__ == "__main__":
    asyncio.run(run_naukri())