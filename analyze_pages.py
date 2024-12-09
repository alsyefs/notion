import pandas as pd
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from contextlib import redirect_stdout
import matplotlib
import networkx as nx
import os
from typing import Dict, List
import textwrap
from globals import (PAGES_CSV_FILE_PATH, ANALYSIS_OUTPUT_FILE_PATH,
                     TASKS_BY_STATUS_PLOT_PATH, TASKS_BY_PRIORITY_PLOT_PATH,
                     TASKS_OVER_TIME_PLOT_PATH,
                     TASK_COMPLETION_TIMES_PLOT_PATH,
                     TASKS_REPLATIONSHIPS_PLOT_PATH)

# Visualization settings
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'DejaVu Sans'

def format_section_header(text: str) -> str:
    """Creates a formatted section header."""
    return f"\n{'='*80}\n{text.upper()}\n{'='*80}\n"

def format_subsection_header(text: str) -> str:
    """Creates a formatted subsection header."""
    return f"\n{'-'*40}\n{text}\n{'-'*40}\n"

def wrap_text(text: str, width: int = 80) -> str:
    """Wraps text to specified width."""
    return '\n'.join(textwrap.wrap(text, width=width))

def analyze_tasks(csv_file=PAGES_CSV_FILE_PATH, output_file=ANALYSIS_OUTPUT_FILE_PATH):
    """Main analysis function with improved formatting."""
    tasks_df = pd.read_csv(csv_file)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        with redirect_stdout(f):
            # Summary Section
            print(format_section_header("Task Summary"))
            analyze_task_summary(tasks_df)
            
            # Overdue Tasks Section
            print(format_section_header("Overdue Tasks Analysis"))
            analyze_task_dates(tasks_df)
            
            # Priority Analysis Section
            print(format_section_header("Priority Analysis"))
            analyze_task_priorities(tasks_df)
            
            # Upcoming Tasks Section
            print(format_section_header("Upcoming Tasks"))
            analyze_upcoming_tasks(tasks_df)
    
    generate_charts(tasks_df)
    generate_task_network(tasks_df)
    print(f"Analysis results saved to {output_file}")

def analyze_task_summary(tasks_df: pd.DataFrame):
    """Analyzes and prints task summary statistics with improved formatting."""
    total_tasks = len(tasks_df)
    completed_tasks = len(tasks_df[tasks_df["Status"].str.contains("Done", case=False, na=False)])
    in_progress_tasks = len(tasks_df[tasks_df["Status"].str.contains("Doing", case=False, na=False)])
    not_started_tasks = len(tasks_df[~tasks_df["Status"].str.contains("Done|Doing", case=False, regex=True, na=False)])
    
    print(f"Total Tasks: {total_tasks}")
    print(f"├─ Completed: {completed_tasks}")
    print(f"├─ In Progress: {in_progress_tasks}")
    print(f"└─ Not Started: {not_started_tasks}")
    
    if total_tasks > 0:
        percent_completed = (completed_tasks / total_tasks) * 100
        print(f"\nCompletion Rate: {percent_completed:.1f}%")
        
        if percent_completed >= 75:
            print("Status: Excellent progress! Most tasks completed.")
        elif percent_completed >= 50:
            print("Status: Good progress. Continue focusing on remaining tasks.")
        else:
            print("Status: Less than half of tasks completed. Consider prioritizing critical tasks.")

def truncate_task_name(name: str, max_length: int = 90) -> str:
    """Truncates task name to specified length and adds ellipsis if needed."""
    return f"{name[:max_length-3]}..." if len(name) > max_length else name

def analyze_task_dates(tasks_df: pd.DataFrame):
    """Analyzes and prints task dates with improved formatting."""
    today = pd.Timestamp.now().tz_localize(None)
    
    # Convert dates and clean status
    tasks_df['Due Date'] = pd.to_datetime(tasks_df['Due'], errors='coerce').dt.tz_localize(None)
    status_mapping = {
        'Duplicate': 'duplicate',
        '1 Canceled': 'canceled',
        '2 Notes': 'notes',
        '3 To Do': 'to do',
        '4 Doing': 'doing',
        '5 Paused': 'paused',
        '6 Done 🙌': 'done'
    }
    tasks_df['Status'] = tasks_df['Status'].replace(status_mapping)
    
    # Identify overdue tasks
    past_due = tasks_df['Due Date'] < today
    incomplete_tasks = tasks_df["Status"].str.lower().isin(["", "to do", "doing"])
    overdue_tasks = tasks_df[(past_due) & (incomplete_tasks)]
    print(f"Number of Overdue Tasks: {len(overdue_tasks)}")
    
    if not overdue_tasks.empty:
        print(format_subsection_header("Overdue Tasks Details"))
        overdue_display = overdue_tasks[["NID", "Name", "Due", "Priority"]].copy()
        overdue_display['Name'] = overdue_display['Name'].apply(truncate_task_name)
        print(overdue_display.to_string(index=False))
        print(format_subsection_header("High Priority Overdue Tasks"))
        high_priority_overdue = overdue_tasks[overdue_tasks['Priority'].isin(['Critical', 'High'])].copy()
        high_priority_overdue['Name'] = high_priority_overdue['Name'].apply(truncate_task_name)
        if not high_priority_overdue.empty:
            print(high_priority_overdue[["NID", "Name", "Due", "Priority"]].to_string(index=False))
            print("\nAction Required: Address these high-priority overdue tasks immediately.")
        else:
            print("No high-priority overdue tasks.")

def analyze_task_priorities(tasks_df: pd.DataFrame):
    """Analyzes and prints task priorities with improved formatting."""
    priority_counts = tasks_df["Priority"].value_counts()
    
    print("Task Distribution by Priority:")
    for priority, count in priority_counts.items():
        print(f"{priority:.<20} {count}")
    
    print(format_subsection_header("Priority Status Breakdown"))
    status_priority = pd.crosstab(tasks_df["Status"], tasks_df["Priority"])
    print(status_priority)
    
    # Add specific priority recommendations
    critical_high = tasks_df[
        (tasks_df["Priority"].isin(["Critical", "High"])) & 
        (tasks_df["Status"].str.lower().isin(["to do", "doing"]))
    ]
    
    if not critical_high.empty:
        print(format_subsection_header("Critical/High Priority Tasks to Focus On"))
        critical_high_display = critical_high.copy()
        critical_high_display['Name'] = critical_high_display['Name'].apply(truncate_task_name)
        print(critical_high_display[["NID", "Name", "Priority", "Status"]].to_string(index=False))

def analyze_upcoming_tasks(tasks_df: pd.DataFrame):
    """Analyzes and prints upcoming tasks with improved formatting."""
    today = pd.Timestamp.now().tz_localize(None)
    next_week = today + datetime.timedelta(days=7)
    
    # Upcoming due tasks
    tasks_df['Due Date'] = pd.to_datetime(tasks_df['Due'], errors='coerce').dt.tz_localize(None)
    upcoming_tasks = tasks_df[
        (tasks_df['Due Date'] >= today) & 
        (tasks_df['Due Date'] <= next_week) &
        (tasks_df["Status"].str.lower().isin(["", "to do", "doing"]))
    ]
    
    print(format_subsection_header("Tasks Due in Next 7 Days"))
    if not upcoming_tasks.empty:
        upcoming_display = upcoming_tasks.copy()
        upcoming_display['Name'] = upcoming_display['Name'].apply(truncate_task_name)
        print(upcoming_display[["NID", "Name", "Due", "Priority"]].to_string(index=False))
    else:
        print("No tasks due in the next 7 days.")
    
    # Longest pending tasks
    tasks_df['Created Date'] = pd.to_datetime(tasks_df['Created'], errors='coerce')  # Changed from 'Created Date' to 'Created'
    pending_tasks = tasks_df[tasks_df["Status"].str.lower().isin(["to do", "doing"])]
    oldest_pending = pending_tasks.nlargest(5, 'Created Date')[["NID", "Name", "Created Date", "Priority"]].copy()  # Use the column we just created
    oldest_pending['Name'] = oldest_pending['Name'].apply(truncate_task_name)
    
    print(format_subsection_header("Oldest Pending Tasks"))
    print(oldest_pending.to_string(index=False))

def generate_charts(tasks_df: pd.DataFrame):
    """Generates visualization charts with improved styling."""
    sns.set(style="whitegrid")
    
    # Calculate completion time for tasks that have both Started and Completed dates
    tasks_df['Started'] = pd.to_datetime(tasks_df['Started'], errors='coerce')
    tasks_df['Completed'] = pd.to_datetime(tasks_df['Completed'], errors='coerce')
    tasks_df['Time to Complete'] = (tasks_df['Completed'] - tasks_df['Started']).dt.total_seconds() / (24 * 60 * 60)  # Convert to days
    
    # Pie chart for task status
    status_counts = tasks_df["Status"].value_counts()
    sanitized_labels = [remove_emojis(label) for label in status_counts.index]
    plt.figure(figsize=(6, 6))
    plt.pie(status_counts, labels=sanitized_labels, autopct='%1.1f%%', startangle=90)
    plt.title(remove_emojis("Tasks by Status"))
    plt.ylabel('')
    plt.annotate(f"Total tasks: {status_counts.sum()}", xy=(0.5, -0.1), xycoords="axes fraction", ha='center')
    plt.savefig(TASKS_BY_STATUS_PLOT_PATH)
    plt.close()
    
    # Bar chart for tasks by priority
    priority_counts = tasks_df["Priority"].value_counts()
    sanitized_labels = [remove_emojis(label) for label in priority_counts.index]
    plt.figure(figsize=(8, 6))
    sns.barplot(x=sanitized_labels, y=priority_counts.values, hue=sanitized_labels, dodge=False, legend=False)
    plt.title(remove_emojis("Tasks by Priority"))
    plt.xlabel("Priority")
    plt.ylabel("Number of Tasks")
    for index, value in enumerate(priority_counts.values):
        plt.text(index, value + 0.5, str(value), ha='center')
    plt.savefig(TASKS_BY_PRIORITY_PLOT_PATH)
    plt.close()
    
    # Line chart for tasks over time
    tasks_df['Created Date'] = pd.to_datetime(tasks_df['Created'], errors='coerce').dt.date
    tasks_by_date = tasks_df.groupby('Created Date').size().cumsum()
    plt.figure(figsize=(10, 6))
    plt.plot(tasks_by_date.index, tasks_by_date.values, marker='o', linestyle='-', color='b')
    plt.title("Cumulative Tasks Over Time")
    plt.xlabel(remove_emojis("Date"))
    plt.ylabel(remove_emojis("Total Tasks"))
    plt.grid(True)
    plt.savefig(TASKS_OVER_TIME_PLOT_PATH)
    plt.close()
    
    # Histogram of task completion times for completed tasks with valid start/end dates
    completed_tasks = tasks_df[tasks_df['Time to Complete'].notna() & (tasks_df['Time to Complete'] >= 0)]
    if not completed_tasks.empty:
        plt.figure(figsize=(8, 6))
        sns.histplot(completed_tasks['Time to Complete'], bins=20, kde=True, color='green')
        plt.title("Histogram of Task Completion Times")
        plt.xlabel("Days to Complete")
        plt.ylabel("Number of Tasks")
        avg_completion_time = completed_tasks['Time to Complete'].mean()
        plt.axvline(avg_completion_time, color='red', linestyle='--')
        plt.annotate(f"Average: {avg_completion_time:.2f} days", 
                    xy=(avg_completion_time, plt.ylim()[1]/2), 
                    xytext=(10, 30), 
                    textcoords="offset points", 
                    arrowprops=dict(facecolor='red', shrink=0.05))
        plt.savefig(TASK_COMPLETION_TIMES_PLOT_PATH)
        plt.close()

def generate_task_network(tasks_df: pd.DataFrame):
    """Generates task network visualization with improved styling."""
    G = nx.DiGraph()
    
    # Add nodes
    for _, row in tasks_df.iterrows():
        G.add_node(row['NID'], label=row['Name'])
    
    # Add edges
    for _, row in tasks_df.iterrows():
        parent_nid = row.get('Parent NID')
        if parent_nid and pd.notna(parent_nid):
            G.add_edge(parent_nid, row['NID'])
    
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_size=500, node_color='skyblue', 
            font_size=8, arrows=True, edge_color='gray')
    plt.title("Task Parent-Child Relationships")
    plt.savefig(TASKS_REPLATIONSHIPS_PLOT_PATH)
    plt.close()

def remove_emojis(text: str) -> str:
    """Removes emoji characters from text."""
    return text.encode('ascii', 'ignore').decode('ascii')

if __name__ == "__main__":
    analyze_tasks()