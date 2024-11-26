import pandas as pd
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from contextlib import redirect_stdout
import matplotlib
import networkx as nx
import os
from globals import (PAGES_CSV_FILE_PATH, ANALYSIS_OUTPUT_FILE_PATH,
                     TASKS_BY_STATUS_PLOT_PATH, TASKS_BY_PRIORITY_PLOT_PATH,
                     TASKS_OVER_TIME_PLOT_PATH,
                     TASK_COMPLETION_TIMES_PLOT_PATH,
                     TASKS_REPLATIONSHIPS_PLOT_PATH)

matplotlib.rcParams['axes.unicode_minus'] = False  # Handle minus signs
matplotlib.rcParams['font.family'] = 'DejaVu Sans'  # A font that supports more Unicode glyphs

def analyze_tasks(csv_file=PAGES_CSV_FILE_PATH, output_file=ANALYSIS_OUTPUT_FILE_PATH):
    tasks_df = pd.read_csv(csv_file)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        with redirect_stdout(f):  # Redirect all print statements to the file
            analyze_task_summary(tasks_df)
            analyze_task_dates(tasks_df)
            analyze_task_priorities(tasks_df)
            analyze_upcoming_tasks(tasks_df)
    generate_charts(tasks_df)
    generate_task_network(tasks_df)
    print(f"Analysis results saved to {output_file}")

def analyze_task_summary(tasks_df):
    total_tasks = len(tasks_df)
    completed_tasks = tasks_df[tasks_df["Status"].str.lower().isin(["completed", "done"])]
    num_completed_tasks = len(completed_tasks)
    in_progress_tasks = tasks_df[tasks_df["Status"].str.lower() == "in progress"]
    num_in_progress_tasks = len(in_progress_tasks)
    not_started_tasks = tasks_df[~tasks_df["Status"].str.lower().isin(["completed", "done", "in progress"])]
    num_not_started_tasks = len(not_started_tasks)
    print(f"Total tasks: {total_tasks}")
    print(f"Completed tasks: {num_completed_tasks}")
    print(f"In Progress tasks: {num_in_progress_tasks}")
    print(f"Not started tasks: {num_not_started_tasks}")
    if total_tasks > 0:
        percent_completed = (num_completed_tasks / total_tasks) * 100
        print(f"Percentage of tasks completed: {percent_completed:.2f}%")
    if percent_completed >= 75:
        print("Great progress! Most of the tasks are completed.")
    elif percent_completed >= 50:
        print("Good job, you're halfway there. Keep pushing forward!")
    else:
        print("Less than half of the tasks are completed. Consider prioritizing the most important tasks to boost progress.")

def analyze_task_dates(tasks_df):
    today = pd.Timestamp.now().tz_localize(None)  # Ensure today is timezone-naive
    tasks_df['Due Date'] = pd.to_datetime(tasks_df['Due'], errors='coerce').dt.tz_localize(None)
    tasks_df['Status'] = tasks_df['Status'].str.replace('Duplicate', 'duplicate')
    tasks_df['Status'] = tasks_df['Status'].str.replace('1 Canceled', 'canceled')
    tasks_df['Status'] = tasks_df['Status'].str.replace('2 Notes', 'notes')
    tasks_df['Status'] = tasks_df['Status'].str.replace('3 To Do', 'to do')
    tasks_df['Status'] = tasks_df['Status'].str.replace('4 Doing', 'doing')
    tasks_df['Status'] = tasks_df['Status'].str.replace('5 Paused', 'paused')
    tasks_df['Status'] = tasks_df['Status'].str.replace('6 Done 🙌', 'done')
    past_due = tasks_df['Due Date'] < today # Due date is in the past
    incomplete_tasks = tasks_df["Status"].str.lower().isin(["", "to do", "doing"])
    overdue_tasks = tasks_df[(past_due) &  (incomplete_tasks)]
    num_overdue_tasks = len(overdue_tasks)
    print(f"Overdue tasks: {num_overdue_tasks}")
    if num_overdue_tasks > 0:
        print("Overdue tasks:")
        print(overdue_tasks[["NID", "Name", "Due", "Priority"]])
    priority_overdue_tasks = overdue_tasks.sort_values(by=["Priority", "Due Date"], ascending=[True, False]).head(30)
    print("Top 30 overdue tasks by priority:")
    print(priority_overdue_tasks[["NID", "Name", "Due", "Priority"]])
    if num_overdue_tasks > 0:  # Insightful comment on overdue tasks
        print("You have overdue tasks. It's crucial to address these as soon as possible to avoid delays.")
    else:
        print("No overdue tasks. Great time management!")
    tasks_df['Created Date'] = pd.to_datetime(tasks_df['Created'], errors='coerce').dt.tz_localize(None)
    tasks_df['Completed Date'] = pd.to_datetime(tasks_df['Completed'], errors='coerce').dt.tz_localize(None)
    tasks_df['Time to Complete'] = (tasks_df['Completed Date'] - tasks_df['Created Date']).dt.days
    avg_time_to_complete = tasks_df['Time to Complete'].mean()
    print(f"Average time to complete tasks: {avg_time_to_complete:.2f} days")
    if not pd.isna(avg_time_to_complete):  # Insightful comment on time to complete tasks
        if avg_time_to_complete <= 7:
            print("Tasks are being completed in a timely manner. Keep up the efficiency!")
        else:
            print("Tasks are taking longer to complete. Consider breaking down larger tasks into smaller, more manageable parts.")

def analyze_task_priorities(tasks_df):
    priority_counts = tasks_df["Priority"].value_counts()
    print("Tasks by priority:")
    print(priority_counts)
    critical_high_priorities = [priority for priority in ["Critical", "High"] if priority in priority_counts.index]
    if critical_high_priorities and priority_counts.loc[critical_high_priorities].sum() > 0:
        print("There are critical or high-priority tasks that need attention. Make sure these are addressed first.")
    else:
        print("No critical or high-priority tasks pending. Focus on other tasks.")
    not_completed_statuses = ["to do", "doing", ""]  # Suggest tasks to work on next based on highest priority not started tasks
    incomplete_tasks = tasks_df[(tasks_df["Priority"].isin(priority_counts.index)) & 
                                 (tasks_df["Status"].str.lower().isin(not_completed_statuses))]
    if not incomplete_tasks.empty:
        print("Tasks to work on next based on priority:")
        for priority in priority_counts.index:
            priority_tasks = incomplete_tasks[incomplete_tasks["Priority"] == priority]
            if not priority_tasks.empty:
                print(f"\nPriority: {priority}")
                print(priority_tasks[["NID", "Name", "Due"]])
    else:
        print("No tasks to work on.")
    status_priority = pd.crosstab(tasks_df["Status"], tasks_df["Priority"])
    print("\nBreakdown of tasks by Status and Priority:")
    print(status_priority)

def analyze_upcoming_tasks(tasks_df):
    today = pd.Timestamp.now().tz_localize(None)
    next_week = today + datetime.timedelta(days=7)
    valid_statuses = ["", "to do", "doing"]
    relevant_tasks = tasks_df[tasks_df["Status"].str.lower().isin(valid_statuses)]
    upcoming_due_tasks = relevant_tasks[(relevant_tasks['Due Date'] >= today) & (relevant_tasks['Due Date'] <= next_week)]
    print("Tasks due in the next 7 days:")
    if not upcoming_due_tasks.empty:
        print(upcoming_due_tasks[["NID", "Name", "Due"]])
    else:
        print("No tasks due in the next 7 days.")
    if len(upcoming_due_tasks) > 0:
        print("You have tasks due in the next week. Prioritize these to stay on track.")
    else:
        print("No tasks are due in the next 7 days. This might be a good time to get ahead or revisit pending tasks.")
    pending_tasks = relevant_tasks.copy()  # Filter pending tasks with valid statuses
    longest_pending_tasks = pending_tasks.sort_values(by="Created Date").head(5)
    print("Longest pending tasks:")
    print(longest_pending_tasks[["NID", "Name", "Created Date", "Status"]])
    tasks_df['Week Created'] = tasks_df['Created Date'].dt.to_period('W')  # Group tasks by week created
    tasks_by_week = tasks_df.groupby('Week Created').size()
    print("Tasks created per week:")
    print(tasks_by_week)

def generate_charts(tasks_df):
    sns.set(style="whitegrid")
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
    sns.barplot(
        x=sanitized_labels,
        y=priority_counts.values,
        hue=sanitized_labels,  # Set the hue to match x for consistent coloring
        dodge=False,           # Prevent grouping since hue is the same as x
        legend=False,          # Disable legend as it's unnecessary in this case
        palette="viridis"
    )
    plt.title(remove_emojis("Tasks by Priority"))
    plt.xlabel("Priority")
    plt.ylabel("Number of Tasks")
    for index, value in enumerate(priority_counts.values):
        plt.text(index, value + 0.5, str(value), ha='center')
    plt.savefig(TASKS_BY_PRIORITY_PLOT_PATH)
    plt.close()
    # Line chart for cumulative tasks over time
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
    # Histogram of task completion times
    completed_tasks = tasks_df.dropna(subset=['Time to Complete'])
    if not completed_tasks.empty:
        plt.figure(figsize=(8, 6))
        sns.histplot(completed_tasks['Time to Complete'], bins=20, kde=True, color='green')
        plt.title("Histogram of Task Completion Times")
        plt.xlabel("Days to Complete")
        plt.ylabel("Number of Tasks")
        avg_completion_time = completed_tasks['Time to Complete'].mean()
        plt.axvline(avg_completion_time, color='red', linestyle='--')
        plt.annotate(f"Average: {avg_completion_time:.2f} days", xy=(avg_completion_time, 5), xycoords="data", 
                     xytext=(10, 30), textcoords="offset points", arrowprops=dict(facecolor='red', shrink=0.05))
        plt.savefig(TASK_COMPLETION_TIMES_PLOT_PATH)
        plt.close()

def generate_task_network(tasks_df):
    G = nx.DiGraph()
    for _, row in tasks_df.iterrows():  # Add nodes
        G.add_node(row['NID'], label=row['Name'])
    for _, row in tasks_df.iterrows():  # Add edges
        parent_nid = row.get('Parent NID')
        if parent_nid and pd.notna(parent_nid):
            G.add_edge(parent_nid, row['NID'])
    plt.figure(figsize=(12, 8))  # Draw the graph
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_size=500, node_color='skyblue', font_size=8, arrows=True, edge_color='gray')
    plt.title("Task Parent-Child Relationships")
    plt.savefig(TASKS_REPLATIONSHIPS_PLOT_PATH)
    plt.close()

def remove_emojis(text):
    return text.encode('ascii', 'ignore').decode('ascii') 

if __name__ == "__main__":
    analyze_tasks()
