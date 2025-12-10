import pandas as pd
import os
import datetime
import re
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
from globals import (
    PAGES_CSV_FILE_PATH,
    REPORTS_DIR,
    TASKS_OVER_TIME_PLOT_PATH,
    DATA_DIR,
    NAME_TO_BE_PRINTED,
)

# Temp path for report-specific pie chart
REPORT_STATUS_CHART_PATH = os.path.join(DATA_DIR, "report_status_chart.png")


class PDFReport(FPDF):
    def __init__(self, title_text, start_date_str, end_date_str):
        super().__init__()
        self.title_text = title_text
        self.start_date_str = start_date_str
        self.end_date_str = end_date_str

    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, self.title_text, 0, 1, "C")

        # Add Period Range
        self.set_font("Arial", "", 10)
        self.cell(
            0, 6, f"Period: {self.start_date_str} to {self.end_date_str}", 0, 1, "C"
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

        clean_name = clean_text(full_display_name)

        self.set_font("Arial", "B", 10)
        self.multi_cell(0, 6, f"{chr(97 + index)}. {clean_name}")

        if task_body and isinstance(task_body, str) and task_body.strip():
            self.set_font("Arial", "", 10)
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
                clean_part = clean_text(part)
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


def clean_text(text):
    if not isinstance(text, str):
        return str(text)
    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
        "🙌": "",
        "🚀": "",
        "📂": "",
        "🚨": "",
        "👴": "",
        "⚖️": "Licensing: ",
        "⚠️": "Warning: ",
    }
    for char, rep in replacements.items():
        text = text.replace(char, rep)
    return text.encode("latin-1", "replace").decode("latin-1")


def get_tasks_df():
    if not os.path.exists(PAGES_CSV_FILE_PATH):
        return pd.DataFrame()
    df = pd.read_csv(PAGES_CSV_FILE_PATH)
    # Date conversion
    cols = ["Completed", "Created", "Due"]
    for col in cols:
        df[col] = pd.to_datetime(
            df[col], errors="coerce", format="mixed", utc=True
        ).dt.tz_localize(None)

    # Clean Parent NID (convert float to int/str for matching)
    df["NID"] = df["NID"].fillna(0).astype(int)
    df["Parent NID"] = df["Parent NID"].fillna(0).astype(int)

    status_map = {
        "Duplicate": "duplicate",
        "1 Canceled": "canceled",
        "2 Notes": "notes",
        "3 To Do": "to do",
        "4 Doing": "doing",
        "5 Paused": "paused",
        "6 Done 🙌": "done",
    }
    df["Status"] = df["Status"].replace(status_map).str.lower()
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
        print(f"Error generating report chart: {e}")
        return False


def generate_pdf_report(period="weekly", reference_date=None):
    df = get_tasks_df()
    if df.empty:
        return

    # --- 1. Build Parent Lookup Map ---
    # Create a dictionary {NID: Name} to look up parent names instantly
    nid_to_name = df.set_index("NID")["Name"].to_dict()

    # Determine reference date
    today = None
    if reference_date:
        try:
            # Attempt to parse the provided date string
            today = pd.to_datetime(reference_date).tz_localize(None)
        except Exception as e:
            print(f"Error parsing date '{reference_date}': {e}. Defaulting to today.")
            today = None

    if today is None:
        today = pd.Timestamp.now().tz_localize(None)

    if period == "weekly":
        start_date = today - datetime.timedelta(days=7)
        title = f"Weekly Status Report - Week {today.isocalendar()[1]}"
        filename = f"weekly_{today.strftime('%Y-%m-%d')}.pdf"
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
    candidates = df[
        (df["Status"] == "to do") & (df["Priority"].isin(["Critical", "High"]))
    ]
    dated_goals = candidates[candidates["Due"].notna()].sort_values("Due")
    undated_goals = candidates[candidates["Due"].isna()]
    goals = dated_goals if not dated_goals.empty else undated_goals

    completed = df[
        (df["Status"] == "done")
        & (df["Completed"] >= start_date)
        & (df["Completed"] <= today)
    ]
    in_progress = df[df["Status"] == "doing"]

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
            # Resolve Parent Name
            parent_nid = row["Parent NID"]
            p_name = nid_to_name.get(parent_nid) if parent_nid else None
            pdf.add_task_item(i, row["Name"], parent_name=p_name)
    else:
        pdf.chapter_body("No immediate high priority goals with due dates.")

    # Section 2: Completed
    pdf.chapter_title(2, "Completed Tasks")
    if not completed.empty:
        for i, (_, row) in enumerate(completed.iterrows()):
            parent_nid = row["Parent NID"]
            p_name = nid_to_name.get(parent_nid) if parent_nid else None
            pdf.add_task_item(
                i, row["Name"], row.get("Body Content", ""), parent_name=p_name
            )
    else:
        pdf.chapter_body("No tasks completed in this period.")

    # Section 3: In Progress
    pdf.chapter_title(3, "In Progress")
    if not in_progress.empty:
        for i, (_, row) in enumerate(in_progress.iterrows()):
            parent_nid = row["Parent NID"]
            p_name = nid_to_name.get(parent_nid) if parent_nid else None
            pdf.add_task_item(i, row["Name"], parent_name=p_name)
    else:
        pdf.chapter_body("No tasks currently in progress.")

    # --- Add Charts ---
    # 1. Report Specific Status Chart (Generated on the fly)
    if generate_report_charts(goals, completed, in_progress):
        pdf.add_chart_section(
            "Work Distribution (This Period)", REPORT_STATUS_CHART_PATH
        )

    # # 2. Velocity Chart (Global Trend)
    # pdf.add_chart_section("Weekly Velocity (Trend)", TASKS_OVER_TIME_PLOT_PATH)

    pdf.output(output_path, "F")
    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    generate_pdf_report("weekly")
