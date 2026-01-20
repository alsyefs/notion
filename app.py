# /app.py
import asyncio
from datetime import datetime
from backend.fetch_pages import fetch_pages
from backend.analyze_pages import analyze_tasks
from backend.generate_reports import generate_pdf_report
from backend.text_style import PrintStyle
from backend.globals import (
    REPORT_START_DATE,
    REPORT_END_DATE,
    FETCH_ITEM_LIMIT,
    INCLUDE_BODY_CONTENT,
    BODY_CONTENT_MAX_LINES,
    FILTER_TAGS,
)

# REPORT_START_DATE = "2022-12-18"  # Testing
# REPORT_END_DATE = "2027-02-18"  # Testing


def main():
    # 1. Define the workflow dynamically
    steps = []

    # -- Step: Fetch --
    steps.append(
        (
            "Fetching pages from Notion",
            lambda: asyncio.run(fetch_pages(limit=FETCH_ITEM_LIMIT)),
        )
    )

    # -- Step: Analyze --
    steps.append(("Analyzing tasks", analyze_tasks))

    # -- Step: Configure --
    # Define complex logic in a local function to keep the list clean
    def print_config():
        if REPORT_END_DATE:
            PrintStyle.print_info(f"End date: {REPORT_END_DATE}")
        if not REPORT_END_DATE:
            PrintStyle.print_info(f"End date: Today ({datetime.today().date()})")
        if REPORT_START_DATE:
            PrintStyle.print_info(f"Start date: {REPORT_START_DATE}")
        else:
            PrintStyle.print_info(f"Start date: Default based on period")
        # Print Filter Info
        if FILTER_TAGS:
            PrintStyle.print_info(f"Filtering by Tags: {FILTER_TAGS}")

        # Check Body Content Logic
        if INCLUDE_BODY_CONTENT:
            if BODY_CONTENT_MAX_LINES > 0:
                PrintStyle.print_warning(
                    f"Body content truncated to {BODY_CONTENT_MAX_LINES} lines.",
                    label="CONFIG",
                )
            else:
                PrintStyle.print_info("Body content: Full")
        else:
            PrintStyle.print_info("Body content: Disabled")
            # User set a limit but disabled the content
            if BODY_CONTENT_MAX_LINES > 0:
                PrintStyle.print_warning(
                    f"BODY_CONTENT_MAX_LINES is set to {BODY_CONTENT_MAX_LINES}, but INCLUDE_BODY_CONTENT is False. No content will be shown.",
                    label="CONFIG MISMATCH",
                )

    steps.append(("Configuring Report Period", print_config))

    # -- Step: Custom Report --
    def run_custom_report():
        if REPORT_START_DATE and REPORT_END_DATE:
            generate_pdf_report(
                period="custom",
                report_start_date=REPORT_START_DATE,
                report_end_date=REPORT_END_DATE,
            )
        else:
            print(
                f"  {PrintStyle.DIM}Skipped (No custom dates defined){PrintStyle.RESET}"
            )

    steps.append(("Generating Custom Report", run_custom_report))

    # -- Steps: Standard Reports --
    periods = ["daily", "weekly", "biweekly", "monthly", "yearly"]
    for period in periods:
        steps.append(
            (
                f"Generating {period.capitalize()} Report",
                # Use default arg p=period to capture the current value of the loop
                lambda p=period: generate_pdf_report(
                    period=p,
                    report_start_date=REPORT_START_DATE,
                    report_end_date=REPORT_END_DATE,
                ),
            )
        )

    # 2. Execute the workflow
    PrintStyle.print_header("NOTION REPORT GENERATOR")

    total_steps = len(steps)

    for i, (task_name, task_func) in enumerate(steps, 1):
        PrintStyle.print_step(i, total_steps, task_name)
        task_func()

    print("\n")
    PrintStyle.print_success("All operations completed successfully!", label="DONE")
    print("\n")


if __name__ == "__main__":
    main()
