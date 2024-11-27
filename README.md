# Notion Database Integration and Automation

## Configuration Setup

For added security, create a `secret.py` file and add the following variables, which will be imported into `globals.py`:
1. `NOTION_API_TOKEN`: Add your Notion API token.
2. `NOTION_DATABASE_ID`: Add your Notion database ID.
3. `PAGES_CSV_FILE_NAME`: Add the name of the generated CSV file for your Notion pages.
4. `PAGES_JSON_FILE_NAME`: Add the name of the generated JSON file for your Notion pages.

### Example of `secret.py`:
```python
NOTION_API_TOKEN = "your-notion-api-token"
NOTION_DATABASE_ID = "your-notion-database-id"
PAGES_CSV_FILE_NAME = "notion_pages.csv"
PAGES_JSON_FILE_NAME = "notion_pages.json"
```

## Add the necessary Python libraries by running the following command (it is always best to create a Python virtual environment):
(Optional) Create a virtual environment:
    ```python
    python -m venv notion
    ```
(Optional) Activate it in Windows:
    ```python
    .\notion\Scripts\activate
    ```
(Optional) Activate it in Linux:
    ```python
    source notion/bin/activate
    ```
(Required) Install the requirements:
    ```python
    pip install -r requirements.txt
    ```

## After adding your configuration values and installing the requirements, run as:
```python
python app.py
```

## The assumption of a Notion database is to have the following columns:
1. ID: Named UID in the code
2. NID: As type 'ID' with the prefix 'PDM' which shows the numeric ID e.g. '454'.
3. Name: As type 'title'.
4. Status: As type 'select' with the options: '6 Done 🙌', '5 Paused', '4 Doing', '3 To Do', '2 Notes', and '1 Canceled'.
5. Started: As type 'date'.
6. Completed: As type 'date'.
7. Due: As type 'date'.
8. Update Time: As type 'Last edited time'.
9. Priority: As type 'select' with the options: 'Critical', 'High', 'Medium', 'Low', and 'Note'.
10. Files & media: As type 'Files & media'.
11. Created: As type 'Created time'.
12. Parent item: As type 'Relation'.
13. Sub-item: As type 'Relation'.

Body Content: This is not part of the database, but it represents the content of a page in the database.

## Notes
1. Ensure the NOTION_API_TOKEN has appropriate permissions for accessing the database.
2. Verify that your Notion database matches the column structure outlined above.
3. Use the generated CSV and JSON files for further processing or reporting.
