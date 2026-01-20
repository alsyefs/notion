# backend/analyze_pages.py
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from contextlib import redirect_stdout
import matplotlib
import networkx as nx
import os
import ast  # To parse string representation of lists
from backend.text_style import PrintStyle, TextHelper
from backend.globals import (
    PAGES_CSV_FILE_PATH,
    ANALYSIS_OUTPUT_FILE_PATH,
    TASKS_BY_STATUS_PLOT_PATH,
    TASKS_BY_PRIORITY_PLOT_PATH,
    TASKS_OVER_TIME_PLOT_PATH,
    TASK_COMPLETION_TIMES_PLOT_PATH,
    TASKS_REPLATIONSHIPS_PLOT_PATH,
    INCLUDE_UNCATEGORIZED,
    FILTER_TAGS,
)

# Visualization settings
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["font.family"] = "DejaVu Sans"


def file_header(text):
    return f"\n{'-'*40}\n{text}\n{'-'*40}\n"


def analyze_tasks(csv_file=PAGES_CSV_FILE_PATH, output_file=ANALYSIS_OUTPUT_FILE_PATH):
    tasks_df = pd.read_csv(csv_file)
    if tasks_df.empty:
        PrintStyle.print_warning("The database is empty. No analysis to perform.")
        return

    # Clean column names by stripping whitespace (fixes "Status " vs "Status")
    tasks_df.columns = tasks_df.columns.str.strip()
    # DEBUG: Print columns to verify what Pandas actually sees (Remove this later if you want)
    PrintStyle.print_info(f"Loaded CSV Columns: {list(tasks_df.columns)}")

    # Ensure critical columns exist even if the CSV didn't have them
    expected_columns = [
        "Status",
        "Priority",
        "Due",
        "Created",
        "Completed",
        "Started",
        "Children NIDs",
        "NID",
        "Name",
        "Tags",
        "Parent Tags",
    ]
    for col in expected_columns:
        if col not in tasks_df.columns:
            tasks_df[col] = None  # Create missing column

    # Parse Tags for filtering (convert string representation of list back to list)
    def parse_list_col(x):
        try:
            return (
                ast.literal_eval(x)
                if isinstance(x, str)
                else (x if isinstance(x, list) else [])
            )
        except Exception:
            return []

    if "Tags" not in tasks_df.columns:
        tasks_df["Tags"] = None
    if "Parent Tags" not in tasks_df.columns:
        tasks_df["Parent Tags"] = None

    # Apply Tag Filtering
    if FILTER_TAGS:
        # Check if any of the FILTER_TAGS exist in 'Tags' or 'Parent Tags'
        def match_tags(row):
            row_tags = parse_list_col(row["Tags"])
            parent_tags = parse_list_col(row["Parent Tags"])
            all_tags = set(row_tags + parent_tags)
            # Returns True if intersection is not empty
            return not all_tags.isdisjoint(FILTER_TAGS)

        original_count = len(tasks_df)
        tasks_df = tasks_df[tasks_df.apply(match_tags, axis=1)].copy()
        PrintStyle.print_info(
            f"Filtered tasks by tags {FILTER_TAGS}: {len(tasks_df)}/{original_count} remain."
        )

    # 1. Fill NaN NIDs with 0 (or -1) so we can convert to int (we force it to be integer)
    tasks_df["NID"] = (
        pd.to_numeric(tasks_df["NID"], errors="coerce").fillna(0).astype(int)
    )
    PrintStyle.print_subheader("ANALYZING DATA AVAILABILITY")

    status_ok = tasks_df["Status"].notna().any()
    priority_ok = tasks_df["Priority"].notna().any()
    due_ok = tasks_df["Due"].notna().any()

    if not status_ok:
        PrintStyle.print_warning(
            "'Status' data is missing. Workflow analysis will be generic."
        )
    if not priority_ok:
        PrintStyle.print_warning(
            "'Priority' data is missing. Treating all tasks as normal priority."
        )
    if not due_ok:
        PrintStyle.print_warning(
            "'Due Date' data is missing. Overdue/Timeline analysis skipped."
        )

    if status_ok and priority_ok and due_ok:
        PrintStyle.print_success("All critical analysis data is available.")

    # Fill NaN values for logic safety
    tasks_df["Status"] = tasks_df["Status"].fillna("unknown")
    # Default to lowest priority:
    tasks_df["Priority"] = tasks_df["Priority"].fillna("Note")
    tasks_df["Name"] = tasks_df["Name"].fillna("Untitled")

    PrintStyle.print_divider()
    # --- PRE-PROCESSING ---
    # Convert dates with robust parsing using utc=True to handle mixed timezones
    tasks_df["Due Date"] = pd.to_datetime(
        tasks_df["Due"], errors="coerce", format="mixed", utc=True
    ).dt.tz_localize(None)

    tasks_df["Created Date"] = pd.to_datetime(
        tasks_df["Created"], errors="coerce", format="mixed", utc=True
    ).dt.tz_localize(None)

    # Normalize Status
    status_mapping = {
        "Duplicate": "duplicate",
        "1 Canceled": "canceled",
        "2 Notes": "notes",
        "3 To Do": "to do",
        "4 Doing": "doing",
        "5 Paused": "paused",
        "6 Done 🙌": "done",
    }
    tasks_df["Status"] = tasks_df["Status"].replace(status_mapping)

    # Normalize Priority for sorting
    priority_map = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Note": 4}
    tasks_df["Priority_Score"] = tasks_df["Priority"].map(priority_map).fillna(5)

    # Identify "Container/Project" tasks vs "Actionable" tasks
    def has_children(x):
        try:
            val = ast.literal_eval(x) if isinstance(x, str) else x
            return isinstance(val, list) and len(val) > 0
        except:
            return False

    tasks_df["Is_Project"] = tasks_df["Children NIDs"].apply(has_children)

    # Create output directory
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        with redirect_stdout(f):
            # 1. Weekly Workflow
            print(f"\n{'='*80}\n🚀 THIS WEEK'S WORKFLOW\n{'='*80}\n")
            analyze_weekly_focus(tasks_df)

            # 2. Project Status
            print(f"\n{'='*80}\n📂 Active Projects (Containers)\n{'='*80}\n")
            analyze_active_projects(tasks_df)

            # 3. Standard Analysis
            print(f"\n{'='*80}\n📊 Task Statistics\n{'='*80}\n")
            analyze_task_summary(tasks_df)

            print(f"\n{'='*80}\n📋 Backlog Analysis\n{'='*80}\n")
            analyze_task_dates(tasks_df)  # Overdue
            analyze_task_priorities(tasks_df)  # Priority breakdown
            analyze_upcoming_tasks(tasks_df)  # General upcoming

            # 4. Uncategorized (The "Worst Case" Handler)
            # This ensures that even if columns are missing, you see what was fetched while respecting the toggle
            if INCLUDE_UNCATEGORIZED:
                print(f"\n{'='*80}\n⚠️ Unclassified / Other Tasks\n{'='*80}\n")
                analyze_uncategorized(tasks_df)

    generate_charts(tasks_df)
    PrintStyle.print_saved("Text report", output_file)


def analyze_uncategorized(df: pd.DataFrame):
    """
    Lists tasks that do not match any standard Status.
    Useful for debugging when a user connects a database with different property names.
    """
    # Filter for items that are NOT in the standard known statuses
    known_statuses = [
        "to do",
        "doing",
        "done",
        "canceled",
        "duplicate",
        "notes",
        "paused",
    ]

    # Check if 'Status' column even has meaningful data or if it's all "unknown"
    uncategorized = df[~df["Status"].str.lower().isin(known_statuses)].copy()

    if not uncategorized.empty:
        print("These items have a Status that is not recognized (or missing):")
        # Print a simple table of these items
        cols = ["NID", "Name", "Status", "Created"]

        # Format for display
        display = uncategorized[cols].copy()
        # This prevents "0" from showing as "0.0" if pandas reverts type during slicing
        display["NID"] = display["NID"].astype(int).astype(str)
        display["Name"] = display["Name"].apply(TextHelper.truncate_text)
        display["Created"] = display["Created"].apply(
            lambda x: str(x).split(" ")[0]
        )  # Show only date

        print(display.to_string(index=False))
        print(f"\nTotal Unclassified Items: {len(uncategorized)}")
    else:
        print("All items are properly classified into standard statuses.")


def print_task_table(df):
    """Helper to print a clean table with Due Dates."""
    if df.empty:
        print("No tasks found.")
        return

    display_df = df.copy()
    # Explicitly format NID for the print view
    display_df["NID"] = display_df["NID"].astype(int).astype(str)
    display_df["Name"] = display_df["Name"].apply(TextHelper.truncate_text)
    display_df["Due"] = display_df["Due"].fillna("None")

    cols = ["NID", "Name", "Status", "Priority", "Due"]
    print(display_df[cols].to_string(index=False))


def analyze_weekly_focus(df: pd.DataFrame):
    """
    Generates a strict, prioritized list of what to work on.
    Filters out 'Project' containers to avoid clutter.
    """
    today = pd.Timestamp.now().tz_localize(None)
    next_week = today + datetime.timedelta(days=7)

    # Base filter: Active items (To Do or Doing) AND NOT Projects
    active_items = df[
        (df["Status"].str.lower().isin(["to do", "doing"]))
        & (df["Is_Project"] == False)
    ].copy()

    # --- 1. IMMEDIATE ACTION ---
    immediate = active_items[
        (active_items["Due Date"].notna())
        & (
            (active_items["Due Date"] < today)
            | (active_items["Status"].str.lower() == "doing")
        )
    ].sort_values(by=["Priority_Score", "Due Date"])

    print(file_header("1. IMMEDIATE ACTION (Overdue & Dated Active)"))
    if not immediate.empty:
        print_task_table(immediate)
    else:
        print("No immediate overdue or dated active tasks.")

    # --- 2. DUE THIS WEEK ---
    due_week = active_items[
        (active_items["Due Date"] >= today)
        & (active_items["Due Date"] <= next_week)
        & (~active_items["NID"].isin(immediate["NID"]))
    ].sort_values(by=["Due Date", "Priority_Score"])

    print(file_header(f"2. DUE BY NEXT WEEK (By {next_week.strftime('%Y-%m-%d')})"))
    if not due_week.empty:
        print_task_table(due_week)
    else:
        print("No additional tasks due by next week.")

    # --- 3. BACKLOG (Undated or Far Future) ---
    candidates_backlog = active_items[
        (~active_items["NID"].isin(immediate["NID"]))
        & (~active_items["NID"].isin(due_week["NID"]))
    ]

    dated_backlog = candidates_backlog[candidates_backlog["Due Date"].notna()]
    undated_backlog = candidates_backlog[candidates_backlog["Due Date"].isna()]

    if not dated_backlog.empty:
        backlog = dated_backlog.sort_values(by=["Due Date", "Priority_Score"])
    else:
        backlog = undated_backlog.sort_values(by=["Priority_Score", "Created Date"])

    print(file_header("3. HIGH PRIORITY BACKLOG (Undated Active & Future)"))
    if not backlog.empty:
        print_task_table(backlog.head(15))
    else:
        print("No backlog items.")


def analyze_active_projects(df: pd.DataFrame):
    """Shows status of 'Container' tasks (like PhD Thesis)."""
    projects = df[
        (df["Is_Project"] == True) & (df["Status"].str.lower().isin(["to do", "doing"]))
    ].sort_values(by="Priority_Score")

    if not projects.empty:
        print("These are large containers/projects currently active:")
        print_task_table(projects)
    else:
        print("No active major projects found.")


def analyze_task_summary(tasks_df: pd.DataFrame):
    total_tasks = len(tasks_df)
    completed = len(
        tasks_df[tasks_df["Status"].str.contains("done", case=False, na=False)]
    )
    doing = len(
        tasks_df[tasks_df["Status"].str.contains("doing", case=False, na=False)]
    )
    todo = len(tasks_df[tasks_df["Status"].str.contains("to do", case=False, na=False)])

    print(f"Total Database Items: {total_tasks}")
    print(f"├─ Completed: {completed}")
    print(f"├─ In Progress: {doing}")
    print(f"└─ To Do: {todo}")


def analyze_task_dates(tasks_df: pd.DataFrame):
    today = pd.Timestamp.now().tz_localize(None)
    incomplete = tasks_df[
        (tasks_df["Status"].str.lower().isin(["to do", "doing"]))
        & (tasks_df["Is_Project"] == False)
    ]
    overdue = incomplete[incomplete["Due Date"] < today]

    if not overdue.empty:
        print(file_header(f"🚨 Overdue Tasks ({len(overdue)})"))
        print_task_table(overdue)


def analyze_task_priorities(tasks_df: pd.DataFrame):
    critical_high = tasks_df[
        (tasks_df["Priority"].isin(["Critical", "High"]))
        & (tasks_df["Status"].str.lower().isin(["to do", "doing"]))
        & (tasks_df["Is_Project"] == False)
    ]

    if not critical_high.empty:
        print(file_header("Critical/High Priority Actions (All)"))
        print_task_table(critical_high)


def analyze_upcoming_tasks(tasks_df: pd.DataFrame):
    pending_tasks = tasks_df[
        (tasks_df["Status"].str.lower().isin(["to do", "doing"]))
        & (tasks_df["Is_Project"] == False)
    ]
    oldest_pending = pending_tasks.nsmallest(5, "Created Date")

    print(file_header("👴 Oldest Stagnant Tasks"))
    cols = ["NID", "Name", "Created", "Priority", "Due"]
    display = oldest_pending.copy()
    display["Name"] = display["Name"].apply(TextHelper.truncate_text)
    display["Due"] = display["Due"].fillna("None")
    print(display[cols].to_string(index=False))


def generate_charts(tasks_df: pd.DataFrame):
    """Generates helpful visualization charts for reports."""
    try:
        sns.set(style="whitegrid")

        # --- Chart 1: Weekly Velocity (Tasks Completed per Week) ---
        completed_tasks = tasks_df[
            (tasks_df["Status"].str.lower() == "done") & (tasks_df["Completed"].notna())
        ].copy()

        if not completed_tasks.empty:
            completed_tasks["Completed"] = pd.to_datetime(
                completed_tasks["Completed"], format="mixed", errors="coerce", utc=True
            ).dt.tz_localize(None)

            weekly_counts = completed_tasks.resample("W-MON", on="Completed").size()
            last_12_weeks = weekly_counts.tail(12)

            plt.figure(figsize=(10, 5))
            ax = sns.barplot(
                x=last_12_weeks.index, y=last_12_weeks.values, color="#4c72b0"
            )

            x_dates = last_12_weeks.index.strftime("%Y-%m-%d")

            # Explicitly set ticks to match the number of labels to fix UserWarning
            ax.set_xticks(range(len(x_dates)))
            ax.set_xticklabels(labels=x_dates, rotation=45, ha="right")

            plt.title("Weekly Task Completion Velocity (Last 12 Weeks)")
            plt.xlabel("Week Ending")
            plt.ylabel("Tasks Completed")
            plt.tight_layout()
            plt.savefig(TASKS_OVER_TIME_PLOT_PATH)
            plt.close()
            PrintStyle.print_saved("Chart", TASKS_OVER_TIME_PLOT_PATH)
        else:
            # Use dim text for non-critical info
            print(
                f"{PrintStyle.DIM}  ℹ️  No completed tasks data found for Velocity chart.{PrintStyle.RESET}"
            )

        # --- Chart 2: Status Distribution (Global) ---
        status_counts = tasks_df["Status"].value_counts()
        if not status_counts.empty:
            plt.figure(figsize=(6, 6))
            plt.pie(
                status_counts,
                labels=status_counts.index,
                autopct="%1.1f%%",
                startangle=140,
                colors=sns.color_palette("pastel"),
            )
            plt.title("All-Time Task Status")
            plt.savefig(TASKS_BY_STATUS_PLOT_PATH)
            plt.close()
            PrintStyle.print_saved("Chart", TASKS_BY_STATUS_PLOT_PATH)

        # --- Chart 3: Priority Distribution (Global) ---
        priority_counts = tasks_df["Priority"].value_counts()
        if not priority_counts.empty:
            plt.figure(figsize=(8, 6))
            sns.barplot(x=priority_counts.index, y=priority_counts.values)
            plt.title("All-Time Task Priority")
            plt.savefig(TASKS_BY_PRIORITY_PLOT_PATH)
            plt.close()
            PrintStyle.print_saved("Chart", TASKS_BY_PRIORITY_PLOT_PATH)

    except Exception as e:
        print(f"Could not generate charts: {e}")


if __name__ == "__main__":
    analyze_tasks()
