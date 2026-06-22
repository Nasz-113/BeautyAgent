import asyncio
import logging
from typing import List, Tuple, Optional

import httpx
import psycopg2
from psycopg2 import pool as pgpool

# Local imports
from pydantic_basemodel import Reviews
from db_config import host, user, password, db_name

# ------------------------------
# Logging
# ------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------
# Database configuration (from db_config.py)
# ------------------------------
DB_CONFIG = {
    "host": host,
    "port": 5432,
    "dbname": db_name,
    "user": user,
    "password": password,
}

# psycopg2 thread-safe connection pool (minconn=1, maxconn=10)
db_pool = pgpool.ThreadedConnectionPool(1, 30, **DB_CONFIG)

# ------------------------------
# API configuration
# ------------------------------
BASE_URL = (
    "https://apps.bazaarvoice.com/bfd/v1/clients/sephora-au/api-products/cv2/resources/data/reviews.json"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-MY,en;q=0.9",
    "Accept": "application/json",
    "Referer": "https://www.sephora.my/",
    "origin": "https://www.sephora.my",                 # ✅ new
    "bv-bfd-token": "19416,main_site,en_MY",
    "x-swa": "web",
    "Connection": "keep-alive",
    # The following sec-* headers are optional but you can include them
    "sec-ch-ua": '"Chromium";v="137", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
}

# List of (key, value) tuples – allows duplicate keys like 'filter'
PARAMS_TEMPLATE = [
    ("resource", "reviews"),
    ("action", "REVIEWS_N_STATS"),
    # These two static filters will be present in every request
    ("filter", "contentlocale:eq:en_MY,en_SG,en_PH,en_AU,en_NZ,en_TH,en_HK,en_ID,en_US,en_GB,en_MY"),
    ("filter", "isratingsonly:eq:false"),
    ("filter_reviews", "contentlocale:eq:en_MY,en_SG,en_PH,en_AU,en_NZ,en_TH,en_HK,en_ID,en_US,en_GB,en_MY"),
    ("include", "authors,products,comments"),
    ("filteredstats", "reviews"),
    ("Stats", "Reviews"),
    ("limit_comments", "3"),
    ("sort", "relevancy:a1"),
    ("apiversion", "5.5"),
    ("displaycode", "19416-en_my"),
]
# limit and offset will be added per request
MAX_CONCURRENT_REQUESTS = 50
MAX_CONCURRENT_PRODUCTS = 30
request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
product_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PRODUCTS)

# ------------------------------
# Database helpers (sync, run in threads)
# ------------------------------
def get_product_variant_ids_sync() -> List[Tuple[int, int]]:
    """Fetch all product_id, variant_id pairs from the database."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.product_id, v.variant_id
                FROM product_info p
                JOIN variant_info v ON p.product_id = v.product_id
                ORDER BY p.product_id, v.variant_id
            """)
            rows = cur.fetchall()
        return [(row[0], row[1]) for row in rows]
    finally:
        db_pool.putconn(conn)


def insert_reviews_sync(reviews: List[Reviews]):
    """Insert a batch of reviews, ignoring conflicts, using a single transaction."""
    if not reviews:
        return

    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            # Build the list of tuples for executemany
            values = [
                (
                    r.review_id,
                    r.submission_time,
                    r.product_id,
                    r.variant_id,
                    r.reviewed_from,
                    r.rating,
                    r.title,
                    r.review_text,
                    r.user_nickname,
                )
                for r in reviews
            ]
            # Use executemany for efficiency
            cur.executemany(
                """
                INSERT INTO reviews_info (
                    review_id, submission_time, product_id, variant_id,
                    reviewed_from, rating, title, review_text, user_nickname
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (review_id) DO NOTHING
                """,
                values,
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Database insert error: {e}")
        conn.rollback()
    finally:
        db_pool.putconn(conn)

async def get_product_variant_ids() -> List[Tuple[int, int]]:
    """Async wrapper for the sync DB call."""
    return await asyncio.to_thread(get_product_variant_ids_sync)


async def insert_reviews(reviews: List[Reviews]):
    """Async wrapper for the sync DB insert."""
    await asyncio.to_thread(insert_reviews_sync, reviews)


def build_productid(product_id: int, variant_id: int) -> str:
    return f"default-{product_id}-{variant_id}"


# ------------------------------
# Review extraction
# ------------------------------
def extract_review(review_data: dict, product_id: int, variant_id: int) -> Optional[Reviews]:
    try:
        raw_id = review_data.get("Id")
        review_id = int(raw_id) if raw_id else None
        return Reviews(
            review_id=review_id,
            submission_time=review_data.get("SubmissionTime"),
            product_id=product_id,
            variant_id=variant_id,
            reviewed_from=review_data.get("SourceClient"),
            rating=review_data.get("Rating"),
            title=review_data.get("Title"),
            review_text=review_data.get("ReviewText"),
            user_nickname=review_data.get("UserNickname"),
        )
    except Exception as e:
        logger.error(f"Failed to parse review {review_data.get('Id')}: {e}")
        return None


# ------------------------------
# API fetching with httpx
# ------------------------------
async def fetch_page(client: httpx.AsyncClient, productid: str, limit: int, offset: int) -> dict:
    params = list(PARAMS_TEMPLATE)
    params.append(("filter", f"productid:eq:{productid}"))
    params.append(("limit", str(limit)))
    if offset > 0:                          # <-- only send offset when it's not zero
        params.append(("offset", str(offset)))

    async with request_semaphore:
        try:
            response = await client.get(BASE_URL, params=params, headers=HEADERS)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching {productid} offset {offset}: {e}")
            raise


async def scrape_product(
    client: httpx.AsyncClient, product_id: int, variant_id: int
) -> None:
    async with product_semaphore:
        await _scrape_product(client, product_id, variant_id)


async def _scrape_product(
    client: httpx.AsyncClient, product_id: int, variant_id: int
) -> None:
    productid = build_productid(product_id, variant_id)
    logger.info(f"Scraping reviews for {productid} ...")

    # Fetch first page (limit=100, no offset → implicitly offset=0)
    try:
        first_page = await fetch_page(client, productid, limit=100, offset=0)
    except Exception:
        logger.warning(f"Skipping {productid} due to initial fetch error.")
        return

    total_results = first_page.get("response", {}).get("TotalResults", 0)
    if total_results == 0:
        logger.info(f"No reviews for {productid}.")
        return

    # Process the first page results
    all_reviews = []
    for review_data in first_page.get("response", {}).get("Results", []):
        parsed = extract_review(review_data, product_id, variant_id)
        if parsed:
            all_reviews.append(parsed)

    # Determine remaining offsets (start from 100, skip 0 because we already have it)
    limit = 100
    offsets = list(range(limit, total_results, limit))

    if offsets:
        # Fetch remaining pages concurrently
        tasks = [fetch_page(client, productid, limit, offset) for offset in offsets]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for i, resp in enumerate(responses):
            if isinstance(resp, Exception):
                logger.error(f"Page offset {offsets[i]} failed: {resp}")
                continue
            for review_data in resp.get("response", {}).get("Results", []):
                parsed = extract_review(review_data, product_id, variant_id)
                if parsed:
                    all_reviews.append(parsed)

    await insert_reviews(all_reviews)
    logger.info(f"Inserted {len(all_reviews)} reviews for {productid}.")


# ------------------------------
# Main
# ------------------------------
async def main():
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            product_variants = await get_product_variant_ids()
            logger.info(f"Found {len(product_variants)} product variants to scrape.")

            if not product_variants:
                logger.warning("No product/variant pairs in database. Exiting.")
                return

            tasks = [
                scrape_product(client, prod_id, var_id)
                for prod_id, var_id in product_variants
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"Task failed: {r}")

    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
    finally:
        # Always close the pool
        db_pool.closeall()
        logger.info("Database pool closed.")



if __name__ == "__main__":
    asyncio.run(main())