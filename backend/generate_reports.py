# backend/generate_reports.py
import pandas as pd
import os
import datetime
import re
import ast
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
from backend.text_style import TextHelper, PrintStyle
from backend.globals import (
    PAGES_CSV_FILE_PATH,
    PAGES_ATTACHMENT_DIR,
    REPORTS_DIR,
    TASKS_OVER_TIME_PLOT_PATH,
    NAME_TO_BE_PRINTED,
    REPORT_STATUS_CHART_PATH,
    INCLUDE_BODY_CONTENT,
    INCLUDE_ATTACHMENTS,
    READABLE_EXTENSIONS,
    INCLUDE_UNCATEGORIZED,
    BODY_CONTENT_MAX_LINES,
    FILTER_TAGS,
)


class PDFReport(FPDF):
    def __init__(self, title_text, start_date_str, report_end_date_str):
        super().__init__()
        self.title_text = title_text
        self.start_date_str = start_date_str
        self.report_end_date_str = report_end_date_str

    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, self.title_text, 0, 1, "C")

        # Add Period Range
        self.set_font("Arial", "", 10)
        self.cell(
            0,
            6,
            f"Period: {self.start_date_str} to {self.report_end_date_str}",
            0,
            1,
            "C",
        )

        self.set_font("Arial", "I", 10)
        self.cell(
            0,
            6,
            f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d')}",
            0,
            1,
            "C",
        )
        # Print the user name if available
        if NAME_TO_BE_PRINTED:
            self.cell(0, 6, f"Prepared by: {NAME_TO_BE_PRINTED}", 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    def chapter_title(self, num, label):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, f"{num}. {label}", 0, 1, "L", 1)
        self.ln(2)

    def chapter_body(self, body):
        self.set_font("Arial", "", 10)
        self.multi_cell(0, 6, body)
        self.ln()

    def add_task_item(self, index, task_name, task_body=None, parent_name=None):
        # Construct the display name with parent context if available
        # Format: "Parent Name: Task Name"
        if parent_name:
            full_display_name = f"[{parent_name}]: {task_name}"
        else:
            full_display_name = task_name

        clean_name = safe_encode(TextHelper.clean_text(full_display_name))

        self.set_font("Arial", "B", 10)
        self.multi_cell(0, 6, f"{chr(97 + index)}. {clean_name}")

        if task_body and isinstance(task_body, str) and task_body.strip():
            self.set_font("Arial", "", 10)
            # Truncate page body text content
            if BODY_CONTENT_MAX_LINES > 0:
                lines = task_body.split("\n")
                if len(lines) > BODY_CONTENT_MAX_LINES:
                    lines = lines[:BODY_CONTENT_MAX_LINES]
                    lines.append(f"... (Truncated to {BODY_CONTENT_MAX_LINES} lines)")
                    task_body = "\n".join(lines)
            self.render_markdown(task_body)
            self.ln(2)

    def render_markdown(self, text):
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            current_indent = 20
            if re.match(r"^(\d+\.|-|\*)\s", line):
                current_indent = 25
            self.set_x(current_indent)
            parts = line.split("**")
            for i, part in enumerate(parts):
                clean_part = safe_encode(TextHelper.clean_text(part))
                if not clean_part:
                    continue
                if i % 2 == 1:
                    self.set_font("Arial", "B", 10)
                else:
                    self.set_font("Arial", "", 10)
                self.write(5, clean_part)
            self.set_font("Arial", "", 10)
            self.ln(5)

    def add_chart_section(self, title, image_path):
        """Adds a new page/section for a chart."""
        if os.path.exists(image_path):
            self.add_page()
            self.chapter_title("Analysis", title)
            # Image(name, x, y, w, h)
            # Adjust width to fit page (A4 width is ~210mm)
            self.image(image_path, x=10, w=190)
            self.ln()


def safe_encode(text):
    """
    Handles the latin-1 encoding for FPDF.
    Separated from clean_text because TextHelper is generic, but this is PDF-specific.
    """
    return text.encode("latin-1", "replace").decode("latin-1")


def get_tasks_df():
    if not os.path.exists(PAGES_CSV_FILE_PATH):
        return pd.DataFrame()
    df = pd.read_csv(PAGES_CSV_FILE_PATH)
    # Ensure columns exist to prevent KeyErrors later
    required_cols = [
        "Status",
        "Priority",
        "Due",
        "Completed",
        "Created",
        "NID",
        "Parent NID",
        "Name",
        "Body Content",
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    # Date conversion
    cols = ["Completed", "Created", "Due", "Updated Time"]
    for col in cols:
        df[col] = pd.to_datetime(
            df[col], errors="coerce", format="mixed", utc=True
        ).dt.tz_localize(None)

    # Clean Parent NID (convert float to int/str for matching)
    df["NID"] = pd.to_numeric(df["NID"], errors="coerce").fillna(0).astype(int)
    # Logic to fill missing Completed dates with Updated Time if the status is Done
    # This fixes the issue where pages without explicit dates were behaving unpredictably
    mask_done_no_date = (df["Status"].astype(str).str.lower().str.contains("done")) & (
        df["Completed"].isna()
    )
    df.loc[mask_done_no_date, "Completed"] = df.loc[mask_done_no_date, "Updated Time"]

    df["Parent NID"] = (
        pd.to_numeric(df["Parent NID"], errors="coerce").fillna(0).astype(int)
    )

    # Ensure Tag columns exist
    if "Tags" not in df.columns:
        df["Tags"] = "[]"
    if "Parent Tags" not in df.columns:
        df["Parent Tags"] = "[]"

    # Apply Tag Filtering
    if FILTER_TAGS:

        def parse_tags(x):
            try:
                return ast.literal_eval(x) if isinstance(x, str) else []
            except Exception:
                return []

        def match_tags(row):
            t = parse_tags(row["Tags"])
            pt = parse_tags(row["Parent Tags"])
            return not set(t + pt).isdisjoint(FILTER_TAGS)

        df = df[df.apply(match_tags, axis=1)]

    status_map = {
        "Duplicate": "duplicate",
        "1 Canceled": "canceled",
        "2 Notes": "notes",
        "3 To Do": "to do",
        "4 Doing": "doing",
        "5 Paused": "paused",
        "6 Done 🙌": "done",
    }
    # Safely replace status, handling non-strings and missing values
    df["Status"] = df["Status"].fillna("unknown").astype(str)
    df["Status"] = df["Status"].replace(status_map).str.lower()
    # Normalize Priority just in case
    df["Priority"] = df["Priority"].fillna("Note")
    return df


def generate_report_charts(goals, completed, in_progress):
    """
    Generates a Pie Chart specifically for the tasks included in this report.
    Returns True if chart created, False otherwise.
    """
    try:
        # Combine relevant tasks
        # We want to see the distribution of "To Do" vs "Done" vs "Doing" *in this period*
        combined_df = pd.concat([goals, completed, in_progress])

        if combined_df.empty:
            return False

        status_counts = combined_df["Status"].value_counts()
        if status_counts.empty:
            return False

        plt.figure(figsize=(6, 6))
        colors = sns.color_palette("pastel")
        plt.pie(
            status_counts,
            labels=status_counts.index.str.title(),
            autopct="%1.1f%%",
            startangle=140,
            colors=colors,
        )
        plt.title("Task Status (This Report Period)")
        plt.tight_layout()
        plt.savefig(REPORT_STATUS_CHART_PATH)
        plt.close()
        return True
    except Exception as e:
        print(f"{PrintStyle.RED}Error generating report chart: {e}{PrintStyle.RESET}")
        return False


def get_smart_attachment_content(nid, files_str):
    """
    Parses the file list, checks extensions, and returns formatted content.
    Skips Excel/CSV and binary files.
    """
    if not INCLUDE_ATTACHMENTS or not files_str:
        return ""

    try:
        files = ast.literal_eval(files_str) if isinstance(files_str, str) else files_str
        if not isinstance(files, list) or not files:
            return ""
    except (ValueError, SyntaxError):
        return ""

    attachment_text = ""
    folder_path = os.path.join(PAGES_ATTACHMENT_DIR, str(nid))

    if not os.path.exists(folder_path):
        return ""

    for filename in files:
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        file_path = os.path.join(folder_path, filename)

        # Case 1: Human readable text (fetch content)
        if ext in READABLE_EXTENSIONS:
            try:
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(
                            1000
                        )  # Limit to 1000 chars to prevent massive overflow
                        if len(content) == 1000:
                            content += "... [Truncated]"
                        attachment_text += (
                            f"\n\n--- Attachment: {filename} ---\n{content}\n"
                        )
            except Exception:
                continue  # Skip if read error

        # Case 2: Skip Excel/CSV (they ruin formatting)
        elif ext in [".csv", ".xlsx", ".xls"]:
            continue

        # Case 3: Other files (just show name if desired, or skip binaries if strictly text)
        # We skip adding just a link/name to keep the report "clean" for non-text items.

    return attachment_text


def generate_pdf_report(period="weekly", report_start_date=None, report_end_date=None):
    df = get_tasks_df()
    if df.empty:
        return

    # 1. Build Parent Lookup Map
    # Create a dictionary {NID: Name} to look up parent names instantly
    nid_to_name = df.set_index("NID")["Name"].to_dict()

    # Build a "Is Parent" lookup to identify container tasks
    # We parse "Children NIDs" to see if a task has children
    def has_children(x):
        try:
            val = ast.literal_eval(x) if isinstance(x, str) else x
            return isinstance(val, list) and len(val) > 0
        except Exception:
            return False

    # Create a set of NIDs that are parents
    parent_nids_set = set(
        df[df["Children NIDs"].apply(has_children)]["NID"].astype(int)
    )

    # Determine reference date
    today = None
    if report_start_date:
        try:
            # Attempt to parse the provided date string
            start_date = pd.to_datetime(report_start_date).tz_localize(None)
        except Exception as e:
            print(
                f"{PrintStyle.RED}Error parsing date '{report_start_date}': {e}. Defaulting to period-based start date.{PrintStyle.RESET}"
            )
            start_date = None
    if report_end_date:
        try:
            # Attempt to parse the provided date string
            today = pd.to_datetime(report_end_date).tz_localize(None)
        except Exception as e:
            print(
                f"{PrintStyle.RED}Error parsing date '{report_end_date}': {e}. Defaulting to today.{PrintStyle.RESET}"
            )
            today = None

    if report_start_date and report_end_date:
        print(
            f"{PrintStyle.CYAN}Using custom report start and end dates.{PrintStyle.RESET}"
        )
        start_date = pd.to_datetime(report_start_date).tz_localize(None)
        today = pd.to_datetime(report_end_date).tz_localize(None)
        title = f"Status Report - {start_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}"
        filename = f"report_{start_date.strftime('%Y-%m-%d')}_to_{today.strftime('%Y-%m-%d')}.pdf"

    if today is None:
        today = pd.Timestamp.now().tz_localize(None)

    if period == "daily":
        start_date = today - datetime.timedelta(days=1)
        title = f"Daily Status Report - {today.strftime('%Y-%m-%d')}"
        filename = f"daily_{today.strftime('%Y-%m-%d')}.pdf"
    elif period == "weekly":
        start_date = today - datetime.timedelta(days=7)
        title = f"Weekly Status Report - Week {today.isocalendar()[1]}"
        filename = f"weekly_{today.strftime('%Y-%m-%d')}.pdf"
    elif period == "biweekly":
        start_date = today - datetime.timedelta(days=14)
        title = f"Biweekly Status Report - Weeks {today.isocalendar()[1]-1} & {today.isocalendar()[1]}"
        filename = f"biweekly_{today.strftime('%Y-%m-%d')}.pdf"
    elif period == "monthly":
        start_date = today - datetime.timedelta(days=30)
        title = f"Monthly Status Report - {today.strftime('%B %Y')}"
        filename = f"monthly_{today.strftime('%Y-%m-%d')}.pdf"
    elif period == "yearly":
        start_date = today - datetime.timedelta(days=365)
        title = f"Yearly Status Report - {today.year}"
        filename = f"yearly_{today.strftime('%Y-%m-%d')}.pdf"

    # Format dates for header
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")

    # --- Filter Logic ---
    # Goals (Date > Priority)
    # We strictly respect the Start/End date even for To Do items if they have a Due Date
    candidates = df[
        (df["Status"] == "to do") & (df["Priority"].isin(["Critical", "High"]))
    ]

    # Split into dated and undated
    dated_candidates = candidates[candidates["Due"].notna()]
    undated_goals = candidates[candidates["Due"].isna()]

    # Only include dated goals if they fall within or before the report period
    # This prevents tasks due next year from cluttering this week's report
    dated_goals = dated_candidates[dated_candidates["Due"] <= today]

    goals = pd.concat([dated_goals, undated_goals]).sort_values("Due")

    # Completed Logic: Now relies on the improved 'Completed' column (which falls back to Updated)
    completed = df[
        (df["Status"] == "done")
        & (df["Completed"] >= start_date)
        & (df["Completed"] <= today)
    ]

    # In Progress Logic
    in_progress = df[df["Status"] == "doing"]
    # Catch-all for tasks that don't fit the specific template statuses (e.g. if Status column is missing)
    uncategorized = df[
        ~df["Status"].isin(
            ["to do", "doing", "done", "canceled", "duplicate", "notes", "paused"]
        )
    ]

    # Helper to clean up lists
    def clean_task_list(task_df):
        """
        Removes tasks that are 'Parents' (containers) IF:
        1. They have no body content (or body is disabled).
        2. They are likely just headers for other tasks in the list.
        """
        if task_df.empty:
            return task_df

        # Helper to check if body is effectively empty
        def is_body_empty(row):
            if not INCLUDE_BODY_CONTENT:
                return True
            content = str(row.get("Body Content", "")).strip()
            return not content or content == "nan"

        # Filter out rows where NID is a Parent AND Body is Empty
        # This stops the "b. Writing paper: ..." standalone header from appearing
        # when its children are also listed.
        mask = ~(
            (task_df["NID"].isin(parent_nids_set))
            & (task_df.apply(is_body_empty, axis=1))
        )
        return task_df[mask]

    # Apply the cleanup
    goals = clean_task_list(goals)
    completed = clean_task_list(completed)
    in_progress = clean_task_list(in_progress)

    # --- Generate PDF ---
    os.makedirs(REPORTS_DIR, exist_ok=True)
    output_path = os.path.join(REPORTS_DIR, filename)

    # Pass dates to the constructor
    pdf = PDFReport(title, start_str, end_str)
    pdf.alias_nb_pages()
    pdf.add_page()

    # Section 1: Goals
    pdf.chapter_title(1, "To Do")
    if not goals.empty:
        for i, (_, row) in enumerate(goals.iterrows()):
            parent_nid = row["Parent NID"]
            p_name = nid_to_name.get(parent_nid) if parent_nid else None

            # Prepare Body
            body = row.get("Body Content", "") if INCLUDE_BODY_CONTENT else ""
            # Append Attachment Content
            att_content = get_smart_attachment_content(
                row["NID"], row.get("Files & Media")
            )
            full_body = (str(body) + str(att_content)).strip()

            pdf.add_task_item(i, row["Name"], full_body, parent_name=p_name)
    else:
        pdf.chapter_body("No immediate high priority goals with due dates.")

    # Section 2: Completed
    pdf.chapter_title(2, "Completed Tasks")
    if not completed.empty:
        for i, (_, row) in enumerate(completed.iterrows()):
            parent_nid = row["Parent NID"]
            p_name = nid_to_name.get(parent_nid) if parent_nid else None

            body = row.get("Body Content", "") if INCLUDE_BODY_CONTENT else ""
            att_content = get_smart_attachment_content(
                row["NID"], row.get("Files & Media")
            )
            full_body = (str(body) + str(att_content)).strip()

            pdf.add_task_item(i, row["Name"], full_body, parent_name=p_name)
    else:
        pdf.chapter_body("No tasks completed in this period.")

    # Section 3: In Progress
    pdf.chapter_title(3, "In Progress")
    if not in_progress.empty:
        for i, (_, row) in enumerate(in_progress.iterrows()):
            parent_nid = row["Parent NID"]
            p_name = nid_to_name.get(parent_nid) if parent_nid else None

            body = row.get("Body Content", "") if INCLUDE_BODY_CONTENT else ""
            att_content = get_smart_attachment_content(
                row["NID"], row.get("Files & Media")
            )
            full_body = (str(body) + str(att_content)).strip()

            pdf.add_task_item(i, row["Name"], full_body, parent_name=p_name)
    else:
        pdf.chapter_body("No tasks currently in progress.")

    # Section 4: Uncategorized / Backlog (The "Worst Case" Handler)
    # If the user's database doesn't have a "Status" property, everything ends up here.
    if INCLUDE_UNCATEGORIZED and not uncategorized.empty:
        pdf.chapter_title(4, "Uncategorized / Other Tasks")
        pdf.chapter_body(
            "These tasks do not match standard status filters (To Do, Doing, Done)."
        )
        for i, (_, row) in enumerate(uncategorized.iterrows()):
            pdf.add_task_item(i, row["Name"])

    # --- Add Charts ---
    # 1. Report Specific Status Chart (Generated on the fly)
    if generate_report_charts(goals, completed, in_progress):
        pdf.add_chart_section(
            "Work Distribution (This Period)", REPORT_STATUS_CHART_PATH
        )

    # 2. Velocity Chart (Global Trend)
    if os.path.exists(TASKS_OVER_TIME_PLOT_PATH):
        pdf.add_chart_section("Tasks Over time", TASKS_OVER_TIME_PLOT_PATH)

    pdf.output(output_path, "F")
    PrintStyle.print_saved("Report", output_path)


if __name__ == "__main__":
    generate_pdf_report("weekly")
