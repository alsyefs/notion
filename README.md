# Notion Database Integration and Automation
![MIT License](https://img.shields.io/badge/license-MIT-blue)
![Python 3.11.6](https://img.shields.io/badge/python-3.11.6-brightgreen)

The main goal of this project is to analyze your work on Notion to provide useful insights for better productivity. It fetches data from your Notion database, including pages, content, comments, and attachments. It generates detailed text analysis and **PDF reports** with charts to help you visualize your tasks and workflow.

At the first run, it might take a while to fetch all the data depending on the amount of pages you have, but later runs will only fetch the newly updated pages using a local caching mechanism. This code is currently designed to **not** affect your existing Notion database by avoiding operations like 'insert' or 'update'.

**Disclaimer:** Use this code at your own risk. The author is not responsible for any unintended consequences resulting from its use.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Configuration Setup](#configuration-setup)
- [Installation](#installation)
- [Running](#running)
- [Output Structure](#output-structure)
- [Notion Database Assumptions](#notion-database-assumptions)
- [Notes](#notes)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Data Fetching:**
  - Fetches Notion database pages, including nested blocks (tables, code, equations, toggles).
  - Fetches page comments.
  - recurses through child pages and sub-items.
  - Downloads attached files and media to a local directory.
- **Smart Caching:**
  - Only fetches pages that have been modified since the last run to save time and API calls.
- **Analysis & Reporting:**
  - Exports data to CSV and JSON for external usage.
  - Analyzes tasks to determine "Immediate Actions," "Weekly Focus," and "Backlog."
  - **Generates PDF Reports:** Creates Weekly and Monthly status reports containing:
    - Task lists (Goals, Completed, In Progress).
    - Visual charts (Velocity/Burndown, Status distribution).
    - Rendered Markdown of task descriptions.
- **Read-Only:** Designed to avoid altering your Notion database.

---

## Requirements
- Python 3.6 or higher
- Notion API token with read permissions.
- A Notion database ID.

---

## Configuration Setup

For security, create a `.env` file in the root directory using the provided sample in [`.env.example`](samples/.env.example). This file is excluded from version control. Add the following variables:

1. `NOTION_API_TOKEN`: Your Notion integration token.
2. `NOTION_DATABASE_ID`: The ID of the database you want to track.
3. `PAGES_CSV_FILE_NAME`: Desired name for the raw CSV data.
4. `PAGES_JSON_FILE_NAME`: Desired name for the raw JSON data.
5. `NAME_TO_BE_PRINTED`: The name displayed in the "Prepared by" section of the PDF reports.

### Example of `.env`:
```python
NOTION_API_TOKEN = "secret_your_notion_integration_token"
NOTION_DATABASE_ID = "your_database_id_here"
PAGES_CSV_FILE_NAME = "notion_pages.csv"
PAGES_JSON_FILE_NAME = "notion_pages.json"
NAME_TO_BE_PRINTED = "Your Name"
```

---

## Installation
It is recommended to use a virtual environment. You can set this up manually or use the provided automation scripts (see [Running](#running) section).

### Manual Installation:
1. Create a virtual environment:
   ```bash
   python -m venv notion
   ```
2. Activate it:
   - Windows: `.\notion\Scripts\activate`
   - Linux/Mac: `source notion/bin/activate`
3. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```

---

## Running

### Option 1: Automated Scripts (Recommended)

This repository includes scripts that automatically set up the virtual environment, install dependencies, and run the app.
1. Update the `PROJECT_DIR` path inside the script file to match your folder location.
2. Run the script for your OS:
   - **Windows**: Double-click `run_notion_script_windows.bat`
   - **Linux**: Run bash `run_notion_script_linux.sh`

### Option 2: Manual Execution

After activating your virtual environment and ensuring `.env` is configured, simply run as:
```python
python app.py
```
The application runs in 4 stages:
1. **Fetching**: Retreives new/updated pages from Notion.
2. **Analyzing**: detailed task analysis.
3. **Weekly Report**: Generates a PDF summary for the last 7 days.
4. **Monthly Report**: Generates a PDF summary for the last 30 days.

---

## Output Structure
After running, a `backend/data/` folder will be created with the following structure:
```plaintext
backend/data/
         ├── analysis/
         │   ├── analysis_output.txt       # Text summary of workflow and backlog
         │   ├── tasks_by_priority.png     # Generated chart
         │   ├── tasks_over_time.png       # Generated chart
         │   └── ...
         ├── attachments/                  # Downloaded files from Notion pages
         ├── reports/                      # Generated PDF Reports (Weekly/Monthly)
         ├── notion_pages.csv              # Raw data cache
         └── notion_pages.json             # Raw data JSON
```

---

## Notion Database Assumptions

The code assumes your Notion database contains the following properties (columns). You may need to edit `fetch_pages.py` or `analyze_pages.py` if your schema differs:
1. **NID**: Type `Number` (Unique numeric ID, often used for tickets).
2. **Name**: Type `Title`.
3. **Status**: Type `Select`.
   - **Mapped Options**: 'Done', 'Doing', 'To Do', 'Paused', 'Notes', 'Duplicate', 'Canceled'.
4. **Priority**: Type `Select`.
   - Options: 'Critical (48hrs)', 'High (1wk)', 'Medium (2wks)', 'Low (>month)', 'Note'.
5. **Started**: Type `Date`.
6. **Completed**: Type `Date`.
7. **Due**: Type `Date`.
8. **Files & media**: Type `Files & media`.
9. **Parent item**: Type `Relation` (For sub-tasks/dependencies).
10. **Sub-item**: Type `Relation` (Used to identify "Project" containers vs. actionable tasks).
11. **Update Time**: Type `Last edited time`.
12. **Created**: Type `Created time`.
13. **Active Tags**: Type `Formula` with this formula inside it `prop("Tags").concat(prop("Parent Tags")).unique()`

**Body Content**: This is not part of the database, but it represents the content of a page in the database.

---

## Notes
- **Permissions**: Ensure your Notion Integration has access to the specific Database (`NOTION_API_TOKEN` has access permissions to your database.).
- **PDF Generation**: The tool uses `fpdf` and `matplotlib`. Ensure these are installed via requirements.txt.
- **Timezones**: The tool attempts to handle mixed timezones using UTC normalization.
- **Large Databases**: The first run will fetch everything. Subsequent runs only fetch pages where `Last edited time` has changed.
- **Database Structure:** Verify that your Notion database matches the column structure outlined above, or edit the code to math your structure.
- **Data Usage:** Use the generated CSV and JSON files for further processing or reporting.
- **Troubleshooting:** If you encounter issues with data fetching, check your internet connection and API token validity.


---

## Usage
You can use a script to automate the whole process of running.
First, change the file path to the root of the project in either [`sample_run_script_windows.bat`](samples/sample_run_script_windows.bat) (for Windows) or [`sample_run_script_linux.sh`](samples/sample_run_script_linux.sh) (for Linux) depending on system. Then, double-click on the script file and wait for the fetching process to complete.


After running the script, you will receive reports, inside the directory `backend/data/`, like the following (only 2 charts are shown here, but you will get more):
![Sample Report](samples/sample_task_completion_times.png)
![Sample Report](samples/sample_tasks_by_priority.png)

And here is a sample report file generated after fetching Notion Pages: 
[`sample_analysis_output.txt`](samples/sample_analysis_output.txt)

Additionally, you will get pdf reports (if you want, you can edit the periods in `app.py`).
* **Weekly**: [`sample_weekly_2020-01-01.pdf`](samples/sample_weekly_2020-01-01.pdf).
* **Biweekly**: [`sample_biweekly_2020-01-01.pdf`](samples/sample_biweekly_2020-01-01.pdf).
* **Monthly**: [`sample_monthly_2020-01-01.pdf`](samples/sample_monthly_2020-01-01.pdf).
* **Yearly**: [`sample_yearly_2020-01-01.pdf`](samples/sample_yearly_2020-01-01.pdf).

---

## Contributing
Contributions are welcome! Please open an issue or submit a pull request.

---

## License
This project is licensed under the MIT License - see the [`LICENSE`](LICENSE) file for details.