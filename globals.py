import os
from secret import (
    NOTION_API_TOKEN,
    NOTION_DATABASE_ID,
    PAGES_CSV_FILE_NAME,
    PAGES_JSON_FILE_NAME,
    NAME_TO_BE_PRINTED,
)

# Notion API
NOTION_API_TOKEN = NOTION_API_TOKEN
NOTION_DATABASE_ID = NOTION_DATABASE_ID
NAME_TO_BE_PRINTED = NAME_TO_BE_PRINTED
# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Paths for fetching pages from Notion:
DATA_DIR = os.path.join(BASE_DIR, "data")
PAGES_CSV_FILE_NAME = PAGES_CSV_FILE_NAME
PAGES_JSON_FILE_NAME = PAGES_JSON_FILE_NAME
PAGES_CSV_FILE_PATH = os.path.join(DATA_DIR, PAGES_CSV_FILE_NAME)
PAGES_JSON_FILE_PATH = os.path.join(DATA_DIR, PAGES_JSON_FILE_NAME)
PAGES_ATTACHMENT_DIR = os.path.join(DATA_DIR, "attachments")
# Paths for analyzing pages:
ANALYSIS_DIR = os.path.join(DATA_DIR, "analysis")
ANALYSIS_OUTPUT_FILE_PATH = os.path.join(ANALYSIS_DIR, "analysis_output.txt")
# Report directory
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
# Paths for plots:
TASKS_BY_STATUS_PLOT_PATH = os.path.join(ANALYSIS_DIR, "tasks_by_status.png")
TASKS_BY_PRIORITY_PLOT_PATH = os.path.join(ANALYSIS_DIR, "tasks_by_priority.png")
TASKS_OVER_TIME_PLOT_PATH = os.path.join(ANALYSIS_DIR, "tasks_over_time.png")
TASK_COMPLETION_TIMES_PLOT_PATH = os.path.join(
    ANALYSIS_DIR, "task_completion_times.png"
)
TASKS_REPLATIONSHIPS_PLOT_PATH = os.path.join(ANALYSIS_DIR, "task_relationships.png")
