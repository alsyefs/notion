from fetch_pages import fetch_pages
from analyze_pages import analyze_tasks
from generate_reports import generate_pdf_report
import asyncio

FETCH_ITEM_LIMIT = 0  # Set to 0 to fetch all items (items are Notion pages)
# Set a custom report date in 'yyyy-mm-dd' format, or None to use today's date
# REPORT_DATE = "2023-12-25"
REPORT_DATE = None

if __name__ == "__main__":
    print("Starting...")
    print("[1/4] ---------- Fetching pages from Notion...")
    asyncio.run(fetch_pages(limit=FETCH_ITEM_LIMIT))
    print("[2/4] ---------- Analyzing tasks...")
    analyze_tasks()
    # Generate Reports
    print("[3/4] ---------- Generating weekly reports...")
    generate_pdf_report(period="weekly", reference_date=REPORT_DATE)
    print("[4/4] ---------- Generating monthly reports...")
    generate_pdf_report(period="monthly", reference_date=REPORT_DATE)
    # generate_pdf_report(period="yearly", reference_date=REPORT_DATE)
    print("Done!")
