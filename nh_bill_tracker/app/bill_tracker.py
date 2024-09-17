import asyncio
import aiohttp
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from app.extensions import db, cache
from app.models import Bill
import re
import logging

RSS_FEED_URL = "https://www.gencourt.state.nh.us/rssFeeds/rssQueryResults.aspx?&txtsessionyear=2024&sortoption="
BASE_URL = "https://www.gencourt.state.nh.us/bill_status/legacy/bs2016/billText.aspx"


async def fetch_with_retry(session, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            logging.warning(
                f"Attempt {attempt + 1} failed for URL {url}: {str(e)}")
            if attempt == max_retries - 1:
                logging.error(
                    f"Failed to fetch {url} after {max_retries} attempts")
                return None
            await asyncio.sleep(1 * (2 ** attempt))  # Exponential backoff


async def fetch_full_bill_text(session, url):
    content = await fetch_with_retry(session, url)
    if content:
        soup = BeautifulSoup(content, 'html.parser')
        bill_text_elem = soup.find('pre', class_='aaaCtype')
        return bill_text_elem.text if bill_text_elem else "Full bill text not available"
    return "Failed to fetch full bill text"


def categorize_bill(bill_text):
    categories = {
        'Education': ['education', 'school', 'student', 'teacher', 'university', 'college'],
        'Health': ['health', 'medical', 'hospital', 'doctor', 'patient', 'healthcare'],
        'Transportation': ['transport', 'road', 'highway', 'vehicle', 'traffic', 'transit'],
        'Environment': ['environment', 'climate', 'pollution', 'energy', 'conservation'],
        'Economy': ['economy', 'tax', 'budget', 'finance', 'business', 'employment'],
        'Public Safety': ['police', 'crime', 'prison', 'fire', 'emergency', 'safety'],
        'Housing': ['housing', 'rent', 'property', 'zoning', 'development'],
    }

    bill_text = bill_text.lower()
    for category, keywords in categories.items():
        if any(keyword in bill_text for keyword in keywords):
            return category
    return 'Other'  # Default category if no match is found


async def process_bill(session, entry):
    bill_number = entry.title
    bill_url = entry.link
    bill_id = extract_bill_id(bill_url)
    session_year = entry.get('sessionyear', '2024')
    html_link = get_bill_html_link(session_year, bill_id)

    full_text = await fetch_full_bill_text(session, html_link)
    category = categorize_bill(full_text)

    summary = entry.get('description', entry.get('lsrtitle', ''))
    if isinstance(summary, dict):
        summary = summary.get('value', '')
    summary = BeautifulSoup(summary, 'html.parser').get_text()

    return {
        'number': bill_number,
        'summary': summary,
        'sponsor': entry.get('latestcommittee', ''),
        'last_updated': datetime.now(),
        'status': f"House: {entry.get('housestatus', '')}, Senate: {entry.get('senatestatus', '')}",
        'full_text': full_text,
        'html_link': html_link,
        'category': category
    }


async def update_bills_from_rss():
    @cache.cached(timeout=3600, key_prefix='rss_feed')
    def get_rss_feed():
        return feedparser.parse(RSS_FEED_URL)

    feed = get_rss_feed()

    async with aiohttp.ClientSession() as session:
        tasks = [process_bill(session, entry) for entry in feed.entries]
        bills_data = await asyncio.gather(*tasks, return_exceptions=True)

    new_bills = []
    updated_bills = []

    for bill_data in bills_data:
        if isinstance(bill_data, Exception):
            logging.error(f"Error processing bill: {str(bill_data)}")
            continue
        existing_bill = Bill.query.filter_by(
            number=bill_data['number']).first()
        if existing_bill:
            for key, value in bill_data.items():
                setattr(existing_bill, key, value)
            updated_bills.append(existing_bill)
        else:
            new_bills.append(Bill(**bill_data))

    db.session.bulk_save_objects(new_bills)
    db.session.bulk_save_objects(updated_bills)
    db.session.commit()

    return len(new_bills), len(updated_bills)


def update_bills():
    return asyncio.run(update_bills_from_rss())


def update_bill_categories():
    uncategorized_bills = Bill.query.filter(Bill.category.is_(None)).all()
    for bill in uncategorized_bills:
        bill.category = categorize_bill(bill.full_text)
    db.session.commit()
    print(f"Categorized {len(uncategorized_bills)} bills.")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        new, updated = update_bills()
        print(
            f"Added {new} new bills and updated {updated} bills at {datetime.now()}")
