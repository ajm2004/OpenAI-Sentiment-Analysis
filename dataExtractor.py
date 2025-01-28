import os
import csv
import json
import praw
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
from datetime import datetime
from dotenv import load_dotenv
from tkinter.ttk import Progressbar
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

USERNAME = os.getenv('USER')
PASSWORD = os.getenv('PASSWORD')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')

# Reddit Instance
reddit_instance = praw.Reddit(client_id=CLIENT_ID,
                              client_secret=CLIENT_SECRET,
                              user_agent="my user agent",
                              username=USERNAME,
                              password=PASSWORD)

def fetch_reddit_data(subreddit, query, limit, sort, time_filter, safe_search, progress_callback):
    try:
        subreddit_instance = reddit_instance.subreddit(subreddit)
        posts = []

        # Fetch posts
        for i, post in enumerate(subreddit_instance.search(query=query, limit=limit, sort=sort, time_filter=time_filter, params={"include_over_18": safe_search})):
            post_data = {
                "date_time": datetime.utcfromtimestamp(post.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
                "posted_by": post.author.name if post.author else "[Deleted]",
                "subreddit": str(post.subreddit),
                "title": post.title,
                "body": post.selftext,
                "upvotes": post.score,
                "comments": post.num_comments,
                "url": post.url,
                "post_id": post.id
            }
            posts.append(post_data)
            progress_callback(i + 1, limit)

        # Save posts to files
        save_data(subreddit, query, posts)

        # Fetch comments in parallel
        def fetch_comments_for_post(post):
            fetch_comments(subreddit, post["post_id"], progress_callback)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_comments_for_post, post) for post in posts]
            for i, future in enumerate(as_completed(futures)):
                progress_callback(i + 1, len(posts))

        root.after(0, lambda: status_label.config(text="Fetch Completed!"))
        return posts
    except Exception as e:
        root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {str(e)}"))

def fetch_comments(subreddit, post_id, progress_callback):
    try:
        submission = reddit_instance.submission(post_id)
        comments = []
        submission.comments.replace_more(limit=None)

        for comment in submission.comments.list():
            comments.append({
                "comment_id": comment.id,
                "post_id": submission.id,
                "body": comment.body,
                "time": datetime.utcfromtimestamp(comment.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
                "author": comment.author.name if comment.author else "[Deleted]"
            })
        
        if comments:
            save_comments(submission.subreddit.display_name, submission.id, comments)
        return comments
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while fetching comments: {str(e)}")

def save_data(subreddit, query, posts):
    if not posts:
        return

    # Create folder for subreddit
    folder_name = f"data_{subreddit}"
    os.makedirs(folder_name, exist_ok=True)

    # Save CSV
    csv_file = os.path.join(folder_name, f"{query}_posts.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=posts[0].keys())
        writer.writeheader()
        writer.writerows(posts)

    # Save JSON
    json_file = os.path.join(folder_name, f"{query}_posts.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=4)

def save_comments(subreddit, post_id, comments):
    if not comments:
        return

    # Create folder for comments
    folder_name = os.path.join(f"data_{subreddit}", "comments", f"{post_id}")
    os.makedirs(folder_name, exist_ok=True)

    # Save CSV
    csv_file = os.path.join(folder_name, f"{post_id}.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=comments[0].keys())
        writer.writeheader()
        writer.writerows(comments)

    # Save JSON
    json_file = os.path.join(folder_name, f"{post_id}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(comments, f, indent=4)

def start_fetch():
    subreddit = subreddit_choice.get()
    query = query_entry.get()
    limit = int(limit_choice.get())
    sort = sort_choice.get()
    time_filter = time_filter_choice.get()
    safe_search = "1" if safe_search_var.get() else "0"

    if not query:
        messagebox.showerror("Error", "Please enter a search query.")
        return

    progress_var.set(0)
    progress_bar['value'] = 0

    def run_fetch():
        fetch_reddit_data(subreddit, query, limit, sort, time_filter, safe_search, progress_callback)
        status_label.config(text="Fetch Completed!")

    Thread(target=run_fetch).start()

def progress_callback(current, total):
    progress = int((current / total) * 100)

    # Update progress bar and status label
    def update_progress():
        progress_var.set(progress)
        progress_bar['value'] = progress
        status_label.config(text=f"Progress: {current}/{total}")

    root.after(0, update_progress)


def update_status_safe(message):
    root.after(0, lambda: status_label.config(text=message))

# UI Setup
root = tk.Tk()
root.title("Reddit Fetch Tool")
root.geometry("500x600")

# Subreddit Selection
ttk.Label(root, text="Select Subreddit:").pack(pady=5)
subreddit_choice = ttk.Combobox(root, values=["OpenAI", "ChatGPT", "singularity", "technology", "all"], state="readonly")
subreddit_choice.pack(pady=5)
subreddit_choice.current(0)

# Query Input
ttk.Label(root, text="Search Query:").pack(pady=5)
query_entry = ttk.Entry(root, width=40)
query_entry.pack(pady=5)

# Limit Selection
ttk.Label(root, text="Limit:").pack(pady=5)
limit_choice = ttk.Combobox(root, values=["10", "25", "50", "100"], state="readonly")
limit_choice.pack(pady=5)
limit_choice.current(0)

# Sort Selection
ttk.Label(root, text="Sort By:").pack(pady=5)
sort_choice = ttk.Combobox(root, values=["relevance", "hot", "top", "new", "comments"], state="readonly")
sort_choice.pack(pady=5)
sort_choice.current(0)

# Time Filter Selection
ttk.Label(root, text="Time Filter:").pack(pady=5)
time_filter_choice = ttk.Combobox(root, values=["all", "day", "hour", "month", "week", "year"], state="readonly")
time_filter_choice.pack(pady=5)
time_filter_choice.current(0)

# Safe Search
safe_search_var = tk.IntVar()
safe_search_check = ttk.Checkbutton(root, text="Enable Safe Search", variable=safe_search_var)
safe_search_check.pack(pady=5)

# Progress Bar
progress_var = tk.IntVar()
progress_bar = Progressbar(root, orient="horizontal", length=400, mode="determinate", variable=progress_var)
progress_bar.pack(pady=10)

# Status Label
status_label = ttk.Label(root, text="Idle")
status_label.pack(pady=5)

# Fetch Button
fetch_button = ttk.Button(root, text="Fetch Posts", command=start_fetch)
fetch_button.pack(pady=10)

root.mainloop()
