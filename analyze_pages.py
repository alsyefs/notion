import pandas as pd
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from contextlib import redirect_stdout
import matplotlib
import networkx as nx
import os
import ast  # To parse string representation of lists
from globals import (
    PAGES_CSV_FILE_PATH,
    ANALYSIS_OUTPUT_FILE_PATH,
    TASKS_BY_STATUS_PLOT_PATH,
    TASKS_BY_PRIORITY_PLOT_PATH,
    TASKS_OVER_TIME_PLOT_PATH,
    TASK_COMPLETION_TIMES_PLOT_PATH,
    TASKS_REPLATIONSHIPS_PLOT_PATH,
)

# Visualization settings
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["font.family"] = "DejaVu Sans"


def format_section_header(text: str) -> str:
    return f"\n{'='*80}\n{text.upper()}\n{'='*80}\n"


def format_subsection_header(text: str) -> str:
    return f"\n{'-'*40}\n{text}\n{'-'*40}\n"


def analyze_tasks(csv_file=PAGES_CSV_FILE_PATH, output_file=ANALYSIS_OUTPUT_FILE_PATH):
    tasks_df = pd.read_csv(csv_file)

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
            print(format_section_header("🚀 THIS WEEK'S WORKFLOW"))
            analyze_weekly_focus(tasks_df)

            # 2. Project Status
            print(format_section_header("📂 Active Projects (Containers)"))
            analyze_active_projects(tasks_df)

            # 3. Standard Analysis
            print(format_section_header("Task Statistics"))
            analyze_task_summary(tasks_df)

            print(format_section_header("Backlog Analysis"))
            analyze_task_dates(tasks_df)  # Overdue
            analyze_task_priorities(tasks_df)  # Priority breakdown
            analyze_upcoming_tasks(tasks_df)  # General upcoming

    generate_charts(tasks_df)
    print(f"Analysis results saved to {output_file}")


def truncate_task_name(name: str, max_length: int = 60) -> str:
    if not isinstance(name, str):
        return str(name)
    return f"{name[:max_length-3]}..." if len(name) > max_length else name


def print_task_table(df):
    """Helper to print a clean table with Due Dates."""
    if df.empty:
        print("No tasks found.")
        return

    display_df = df.copy()
    display_df["Name"] = display_df["Name"].apply(truncate_task_name)
    display_df["Due"] = display_df["Due"].fillna("No Date")

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

    print(format_subsection_header("1. IMMEDIATE ACTION (Overdue & Dated Active)"))
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

    print(
        format_subsection_header(
            f"2. DUE THIS WEEK (By {next_week.strftime('%Y-%m-%d')})"
        )
    )
    if not due_week.empty:
        print_task_table(due_week)
    else:
        print("No additional tasks due this week.")

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

    print(
        format_subsection_header("3. HIGH PRIORITY BACKLOG (Undated Active & Future)")
    )
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
        print(format_subsection_header(f"🚨 Overdue Tasks ({len(overdue)})"))
        print_task_table(overdue)


def analyze_task_priorities(tasks_df: pd.DataFrame):
    critical_high = tasks_df[
        (tasks_df["Priority"].isin(["Critical", "High"]))
        & (tasks_df["Status"].str.lower().isin(["to do", "doing"]))
        & (tasks_df["Is_Project"] == False)
    ]

    if not critical_high.empty:
        print(format_subsection_header("Critical/High Priority Actions (All)"))
        print_task_table(critical_high)


def analyze_upcoming_tasks(tasks_df: pd.DataFrame):
    pending_tasks = tasks_df[
        (tasks_df["Status"].str.lower().isin(["to do", "doing"]))
        & (tasks_df["Is_Project"] == False)
    ]
    oldest_pending = pending_tasks.nsmallest(5, "Created Date")

    print(format_subsection_header("👴 Oldest Stagnant Tasks"))
    cols = ["NID", "Name", "Created", "Priority", "Due"]
    display = oldest_pending.copy()
    display["Name"] = display["Name"].apply(truncate_task_name)
    display["Due"] = display["Due"].fillna("No Date")
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
            # FIX: Added utc=True and .dt.tz_localize(None) to handle mixed timezones and offsets
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

            # FIX: Explicitly set ticks to match the number of labels to fix UserWarning
            ax.set_xticks(range(len(x_dates)))
            ax.set_xticklabels(labels=x_dates, rotation=45, ha="right")

            plt.title("Weekly Task Completion Velocity (Last 12 Weeks)")
            plt.xlabel("Week Ending")
            plt.ylabel("Tasks Completed")
            plt.tight_layout()
            plt.savefig(TASKS_OVER_TIME_PLOT_PATH)
            plt.close()
            print(f"Chart generated: {TASKS_OVER_TIME_PLOT_PATH}")
        else:
            print("No completed tasks data found for Velocity chart.")

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
            print(f"Chart generated: {TASKS_BY_STATUS_PLOT_PATH}")

        # --- Chart 3: Priority Distribution (Global) ---
        priority_counts = tasks_df["Priority"].value_counts()
        if not priority_counts.empty:
            plt.figure(figsize=(8, 6))
            sns.barplot(x=priority_counts.index, y=priority_counts.values)
            plt.title("All-Time Task Priority")
            plt.savefig(TASKS_BY_PRIORITY_PLOT_PATH)
            plt.close()
            print(f"Chart generated: {TASKS_BY_PRIORITY_PLOT_PATH}")

    except Exception as e:
        print(f"Could not generate charts: {e}")


if __name__ == "__main__":
    analyze_tasks()
