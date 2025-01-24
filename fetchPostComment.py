import asyncio
import threading
from asyncpraw import Reddit
import json
import csv
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from tkinter import Tk, Label, Entry, Button, StringVar, IntVar, OptionMenu, Text, DISABLED, NORMAL, END
from tkinter import ttk

load_dotenv()

# Load Reddit API credentials from environment variables
USERNAME = os.getenv('USER')
if not USERNAME:
    raise ValueError("USER environment variable not set")

PASSWORD = os.getenv('PASSWORD')
if not PASSWORD:
    raise ValueError("PASSWORD environment variable not set")

CLIENT_ID = os.getenv('CLIENT_ID')
if not CLIENT_ID:
    raise ValueError("CLIENT_ID environment variable not set")

CLIENT_SECRET = os.getenv('CLIENT_SECRET')
if not CLIENT_SECRET:
    raise ValueError("CLIENT_SECRET environment variable not set")

# Initialize asyncpraw instance
async def create_reddit_instance():
    return Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent="my user agent",
        username=USERNAME,
        password=PASSWORD,
    )

# Function to fetch posts and comments without replies
async def fetch_posts_and_comments(reddit, subreddit_name, post_limit, post_sort, status_callback):
    try:
        status_callback("Connecting to subreddit...")
        subreddit = await reddit.subreddit(subreddit_name)

        if post_sort == "Top (All Time)":
            submissions = subreddit.top(limit=post_limit, time_filter="all")
        elif post_sort == "Top (Year)":
            submissions = subreddit.top(limit=post_limit, time_filter="year")
        elif post_sort == "Top (Month)":
            submissions = subreddit.top(limit=post_limit, time_filter="month")
        elif post_sort == "Hot":
            submissions = subreddit.hot(limit=post_limit)
        else:
            submissions = subreddit.new(limit=post_limit)

        status_callback(f"Creating output directory for r/{subreddit_name}...")
        output_dir = f"reddit_data_{subreddit_name}"
        os.makedirs(output_dir, exist_ok=True)

        posts_json = []
        post_count = 0

        post_csv = os.path.join(output_dir, f"{subreddit_name}_posts.csv")
        with open(post_csv, "w", encoding="utf-8") as post_file:
            post_writer = csv.writer(post_file)
            post_writer.writerow(["Post ID", "Title", "Body", "Upvotes", "URL", "Created UTC", "Number of Comments"])

            async for submission in submissions:
                post_count += 1
                status_callback(f"Fetching post {post_count}/{post_limit}...")
                await submission.load()
                post_folder = os.path.join(output_dir, submission.id)
                os.makedirs(post_folder, exist_ok=True)

                post_writer.writerow([
                    submission.id,
                    submission.title,
                    submission.selftext,
                    submission.score,
                    submission.url,
                    datetime.fromtimestamp(submission.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                    submission.num_comments
                ])

                status_callback(f"Fetching comments for post {post_count}/{post_limit}...")
                comments_csv = os.path.join(post_folder, f"comments.csv")
                comments_json = []
                with open(comments_csv, "w", encoding="utf-8") as comments_file:
                    comments_writer = csv.writer(comments_file)
                    comments_writer.writerow(["Post Id","Comment ID", "Body", "Upvotes", "Created UTC"])

                    await submission.comments.replace_more(limit=0)
                    for comment in submission.comments:
                        comment_data = {
                            'Post ID': submission.id,
                            "Comment ID": comment.id,
                            "Body": comment.body,
                            "Upvotes": comment.score,
                            "Created UTC": datetime.fromtimestamp(comment.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                        }
                        comments_writer.writerow([
                            submission.id,
                            comment.id,
                            comment.body,
                            comment.score,
                            datetime.fromtimestamp(comment.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                        ])
                        comments_json.append(comment_data)

                post_data = {
                    "Post ID": submission.id,
                    "Title": submission.title,
                    "Body": submission.selftext,
                    "Upvotes": submission.score,
                    "URL": submission.url,
                    "Created UTC": datetime.fromtimestamp(submission.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                    "Comments": comments_json
                }
                posts_json.append(post_data)

                post_json_path = os.path.join(post_folder, "post.json")
                with open(post_json_path, "w", encoding="utf-8") as post_json_file:
                    json.dump(post_data, post_json_file, indent=4)

        status_callback("Saving final JSON file...")
        all_posts_json_path = os.path.join(output_dir, f"{subreddit_name}_posts.json")
        with open(all_posts_json_path, "w", encoding="utf-8") as all_posts_json_file:
            json.dump(posts_json, all_posts_json_file, indent=4)

        status_callback(f"Completed! Saved all data for r/{subreddit_name}")
        return True
    except Exception as e:
        status_callback(f"Error: {str(e)}")
        return False

# Create a GUI for input
class RedditFetcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reddit Fetcher")
        
        # Set initial window size and minimum size
        self.root.geometry("600x350")
        self.root.minsize(500, 250)
        
        # Configure grid weights
        self.root.grid_columnconfigure(1, weight=1)
        for i in range(5):  # Reduced range due to removed error log
            self.root.grid_rowconfigure(i, weight=1)

        # Input frame
        input_frame = ttk.LabelFrame(root, text="Input Parameters")
        input_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')
        input_frame.grid_columnconfigure(1, weight=1)

        # Subreddit name
        Label(input_frame, text="Subreddit Name:").grid(row=0, column=0, padx=10, pady=5, sticky='e')
        self.subreddit_name = StringVar()
        Entry(input_frame, textvariable=self.subreddit_name).grid(row=0, column=1, padx=10, pady=5, sticky='ew')

        # Number of posts
        Label(input_frame, text="Number of Posts:").grid(row=1, column=0, padx=10, pady=5, sticky='e')
        self.post_limit = IntVar(value=10)
        Entry(input_frame, textvariable=self.post_limit).grid(row=1, column=1, padx=10, pady=5, sticky='ew')

        # Sort type
        Label(input_frame, text="Sort by:").grid(row=2, column=0, padx=10, pady=5, sticky='e')
        self.post_sort = StringVar(value="Top (All Time)")
        sort_menu = OptionMenu(input_frame, self.post_sort, "Top (All Time)", "Top (Year)", "Top (Month)", "Hot", "New")
        sort_menu.grid(row=2, column=1, padx=10, pady=5, sticky='ew')

        # Status frame with prominent display
        status_frame = ttk.LabelFrame(root, text="Status")
        status_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_rowconfigure(0, weight=1)

        self.status_var = StringVar(value="Ready")
        self.status_label = Label(status_frame, textvariable=self.status_var, 
                                wraplength=550, justify='left', 
                                font=('TkDefaultFont', 10))
        self.status_label.grid(row=0, column=0, padx=10, pady=10, sticky='w')

        # Progress bar
        self.progress = ttk.Progressbar(root, mode='indeterminate')
        self.progress.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky='ew')

        # Button frame
        button_frame = ttk.Frame(root)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)

        self.fetch_button = ttk.Button(button_frame, text="Fetch Posts", command=self.start_fetch)
        self.fetch_button.grid(row=0, column=0)

    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

    def start_fetch(self):
        self.fetch_button.config(state='disabled')
        self.progress.start(10)
        
        # Start fetching in a separate thread
        thread = threading.Thread(target=self.threaded_fetch)
        thread.daemon = True
        thread.start()

    def threaded_fetch(self):
        subreddit_name = self.subreddit_name.get()
        post_limit = self.post_limit.get()
        post_sort = self.post_sort.get()

        if not subreddit_name:
            self.finish_fetch("Please fill in all fields.")
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            reddit = loop.run_until_complete(create_reddit_instance())
            
            success = loop.run_until_complete(
                fetch_posts_and_comments(
                    reddit, 
                    subreddit_name, 
                    post_limit, 
                    post_sort,
                    lambda msg: self.root.after(0, self.update_status, msg)
                )
            )
            
            loop.run_until_complete(reddit.close())
            loop.close()

            if success:
                self.finish_fetch(f"Successfully fetched data for r/{subreddit_name}")
            else:
                self.finish_fetch("Failed to fetch data. Check the status messages above.")
                
        except Exception as e:
            self.finish_fetch(f"Error: {str(e)}")

    def finish_fetch(self, message):
        self.root.after(0, self._finish_fetch_gui, message)

    def _finish_fetch_gui(self, message):
        self.status_var.set(message)
        self.progress.stop()
        self.fetch_button.config(state='normal')

# Run the application
if __name__ == "__main__":
    root = Tk()
    app = RedditFetcherApp(root)
    root.mainloop()
