# backend/globals.py

# Python --version: 3.11.6
# 1. to create venv: python -m venv notion
# 2. to install requirements: pip install -r requirements.txt
# 3. activate venv:
#   a. (Linux): source notion/bin/activate
#   b. (Windows CMD): notion\Scripts\activate
#   c. (Windows PowerShell): .\notion\Scripts\Activate.ps1
# 4. run app: python app.py
# 5. to update requirements: pip freeze > requirements.txt
# 6. To print system's structure (Run at project root): python make_tree.py

import os
from dotenv import load_dotenv

load_dotenv()
#################################################################
################# GLOBAL VARIABLES ##############################
#################################################################
REPORT_START_DATE = None  # 'yyyy-mm-dd' or `None` report start date based on period
REPORT_END_DATE = None  # 'yyyy-mm-dd' or `None` for today's date
FETCH_ITEM_LIMIT = 0  # Set to 0 to fetch all items (items are Notion pages)
# Note: it may take a long time to fetch all items for the first time if you have a large database.
# But, subsequent fetches will be faster as only new/updated items will be fetched.
#################################################################
#################### NOTION API #################################
#################################################################
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NAME_TO_BE_PRINTED = os.getenv("NAME_TO_BE_PRINTED")
# Check for critical missing variables to prevent runtime crashes later
if not NOTION_API_TOKEN or not NOTION_DATABASE_ID:
    raise ValueError(
        "CRITICAL ERROR: 'NOTION_API_TOKEN' or 'NOTION_DATABASE_ID' is missing from .env file."
    )
#################################################################
##################### FILE PATHS ################################
#################################################################
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Paths for fetching pages from Notion:
DATA_DIR = os.path.join(BASE_DIR, "data")
# PAGES_CSV_FILE_NAME will store fetched Notion pages in CSV format.
PAGES_CSV_FILE_NAME = os.getenv("PAGES_CSV_FILE_NAME")
# PAGES_JSON_FILE_NAME will store fetched Notion pages in JSON format.
PAGES_JSON_FILE_NAME = os.getenv("PAGES_JSON_FILE_NAME")
PAGES_CSV_FILE_PATH = os.path.join(DATA_DIR, PAGES_CSV_FILE_NAME)
PAGES_JSON_FILE_PATH = os.path.join(DATA_DIR, PAGES_JSON_FILE_NAME)
PAGES_ATTACHMENT_DIR = os.path.join(DATA_DIR, "attachments")
# Paths for the analysis of pages:
ANALYSIS_DIR = os.path.join(DATA_DIR, "analysis")
# ANALYSIS_OUTPUT_FILE_PATH will store the analysis output in text format.
ANALYSIS_OUTPUT_FILE_PATH = os.path.join(ANALYSIS_DIR, "analysis_output.txt")
# Report directory. Reports will be created as pdf files named as "<period>_<REPORT_END_DATE>.pdf".
# E.g., "weekly_2023-10-15.pdf". If REPORT_END_DATE is None, today's date will be used.
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
# Paths for plots:
TASKS_BY_STATUS_PLOT_PATH = os.path.join(ANALYSIS_DIR, "tasks_by_status.png")
TASKS_BY_PRIORITY_PLOT_PATH = os.path.join(ANALYSIS_DIR, "tasks_by_priority.png")
TASKS_OVER_TIME_PLOT_PATH = os.path.join(ANALYSIS_DIR, "tasks_over_time.png")
TASK_COMPLETION_TIMES_PLOT_PATH = os.path.join(
    ANALYSIS_DIR, "task_completion_times.png"
)
TASKS_REPLATIONSHIPS_PLOT_PATH = os.path.join(ANALYSIS_DIR, "task_relationships.png")
# Path for report-specific pie chart
REPORT_STATUS_CHART_PATH = os.path.join(DATA_DIR, "report_status_chart.png")
#################################################################
################## NOTION PAGE PROPERTY NAMES ###################
#################################################################
# These read the specific column names from your .env file
# Defaults are provided so .env entries are optional if using standard Notion names.
NOTION_PROPERTY_NID = os.getenv("NOTION_PROPERTY_NID", "NID")
NOTION_PROPERTY_STATUS = os.getenv("NOTION_PROPERTY_STATUS", "Status")
NOTION_PROPERTY_STARTED = os.getenv("NOTION_PROPERTY_STARTED", "Started")
NOTION_PROPERTY_COMPLETED = os.getenv("NOTION_PROPERTY_COMPLETED", "Completed")
NOTION_PROPERTY_DUE = os.getenv("NOTION_PROPERTY_DUE", "Due")
NOTION_PROPERTY_PRIORITY = os.getenv("NOTION_PROPERTY_PRIORITY", "Priority")
NOTION_PROPERTY_FILES_MEDIA = os.getenv("NOTION_PROPERTY_FILES_MEDIA", "Files & media")
NOTION_PROPERTY_PARENT_ITEM = os.getenv("NOTION_PROPERTY_PARENT_ITEM", "Parent item")
NOTION_PROPERTY_SUB_ITEM = os.getenv("NOTION_PROPERTY_SUB_ITEM", "Sub-item")
NOTION_PROPERTY_ACTIVE_TAGS = os.getenv("NOTION_ACTIVE_TAGS", "Active Tags")

#################################################################
################# PDF REPORT CONFIGURATION ######################
#################################################################
# REPORT CONFIGURATION
# Set to False to exclude the body text (notes) of the tasks from the PDF
INCLUDE_BODY_CONTENT = False
# Truncate body content to a specific number of lines. Set to 0 for no limit.
# REQUIRES INCLUDE_BODY_CONTENT = True
BODY_CONTENT_MAX_LINES = 3
# Set to False to exclude attachment links and content from the PDF
INCLUDE_ATTACHMENTS = False
# Set to False to hide the "Uncategorized / Other Tasks" section in reports
INCLUDE_UNCATEGORIZED = False
# Filter tasks by specific tags. Leave empty [] to include all tasks.
# Example: FILTER_TAGS = ["tag-text-1", "tag-text-2"]
FILTER_TAGS = (
    os.getenv("NOTION_TAGS_LIST").split(",") if os.getenv("NOTION_TAGS_LIST") else []
)
# FILTER_TAGS = []  # No filtering by default to include all tasks.
# Files with these extensions will have their content read and added to the report
# CSV and Excel are excluded to prevent formatting issues in the PDF
READABLE_EXTENSIONS = [".txt", ".md", ".py", ".json", ".log", ".html", ".css", ".js"]
