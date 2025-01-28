import os
import csv
import json
import praw
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
from datetime import datetime, timezone
from dotenv import load_dotenv
from tkinter.ttk import Progressbar
from concurrent.futures import ThreadPoolExecutor, as_completed

class RedditFetcher:
    def __init__(self, gui_update_callback=None):
        load_dotenv()
        self._validate_env()
        self.reddit_instance = self._initialize_reddit()

        assert gui_update_callback is None or callable(gui_update_callback), "GUI update callback must be a callable function."
        self.gui_update_callback = gui_update_callback

    def _validate_env(self):
        self.username = os.getenv('USER')
        self.password = os.getenv('PASSWORD')
        self.client_id = os.getenv('CLIENT_ID')
        self.client_secret = os.getenv('CLIENT_SECRET')

        if not all([self.username, self.password, self.client_id, self.client_secret]):
            raise ValueError("Please set the environment variables USER, PASSWORD, CLIENT_ID, and CLIENT_SECRET.")

    def _initialize_reddit(self):
        return praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent="my user agent",
            username=self.username,
            password=self.password
        )

    def fetch_reddit_data(self, subreddit, query, limit, sort, time_filter, safe_search, JSON_DUMP):
        # Validate input
        assert 1 <= limit <= 10000, "Limit must be between 1 and 10000."
        assert sort in ["relevance", "hot", "top", "new", "comments"], "Invalid sort option."
        assert time_filter in ["all", "day", "hour", "month", "week", "year"], "Invalid time filter option."
        assert safe_search in ["0", "1"], "Invalid safe search option."

        # Use "all" subreddit if none is provided
        if not subreddit:
            subreddit = "all"
            
        try:
            subreddit_instance = self.reddit_instance.subreddit(subreddit)
            posts = []

            self.gui_update_callback(0, "Fetching posts...")

            # Fetch posts based on query or sort option
            data_fetcher = None
            if query:
                data_fetcher = subreddit_instance.search(query=query, limit=limit, sort=sort, time_filter=time_filter, params={"include_over_18": safe_search})
            else:
                match sort:
                    case "hot":
                        data_fetcher = subreddit_instance.hot(limit=limit)
                    case "top":
                        data_fetcher = subreddit_instance.top(limit=limit)
                    case "relevance":
                        data_fetcher = subreddit_instance.hot(limit=limit)
                    case _:
                        data_fetcher = subreddit_instance.new(limit=limit)
                    

            for i, post in enumerate(data_fetcher):
                post_data = {
                    "post_id": post.id,
                    "title": post.title,
                    "body": post.selftext,
                    "subreddit": str(post.subreddit),
                    "upvotes": post.score,
                    "comments": post.num_comments,
                    "date_time":  datetime.fromtimestamp(post.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                    "author": post.author.name if post.author else "[Deleted]",
                }
                posts.append(post_data)
                self.gui_update_callback(int((i/limit) * 100), f"Fetching posts {i}/{limit}...")

            self.remove_previous_data(subreddit)
        
            self.save_data(subreddit, query, posts, JSON_DUMP)

            completed_requests = 0
            total_requests = len(posts)
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(self.fetch_comments, post["subreddit"],query ,post["post_id"], post["title"], JSON_DUMP) for post in posts]
                for future in as_completed(futures):
                    future.result()
                    completed_requests += 1
                    self.gui_update_callback(int((completed_requests/total_requests) * 100), f"Fetching comments {completed_requests}/{total_requests}...")

            self.gui_update_callback(100, "Fetch Completed!")
            return posts
        except Exception as e:
            self.gui_update_callback(0, f"Error: {str(e)}")
            raise Exception(f"Error fetching Reddit data: {str(e)}")

    def fetch_comments(self, subreddit, query, post_id, post_title=None, JSON_DUMP=False):
        try:
            submission = self.reddit_instance.submission(post_id)
            comments = []
            submission.comments.replace_more(limit=5)

            self.gui_update_callback(0, f"Fetching comments for post {post_id}...")
            for comment in submission.comments.list():
                if comment.body in ("[deleted]","[removed]"):
                    continue
                comments.append({
                    "post_id": submission.id,
                    "comment_id": comment.id,
                    "title": post_title,
                    "body": comment.body,
                    "subreddit": subreddit,
                    "upvotes": comment.score,
                    "comments": 0, 
                    "date_time": datetime.fromtimestamp(comment.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                    "author": comment.author.name if comment.author else "[Deleted]",
                })

            if comments:
                self.save_data(subreddit, query, comments, JSON_DUMP)
            return comments
        except Exception as e:
            raise Exception(f"Error fetching comments: {str(e)}")
        
    @staticmethod
    def remove_previous_data(subreddit):
        folder_name = f"data_{subreddit}"
        if os.path.exists(folder_name):
            for file in os.listdir(folder_name):
                file_path = os.path.join(folder_name, file)
                os.remove(file_path)

    @staticmethod
    def save_data(subreddit, query, posts, JSON_DUMP=False):
        if not posts:
            return

        folder_name = f"data_{subreddit}"
        if query:
            folder_name = f"data_{subreddit}_{query.replace(' ', '_').encode('ascii', 'ignore').decode()}"
        os.makedirs(folder_name, exist_ok=True)

        RedditFetcher.save_query(folder_name, query)

        csv_file = os.path.join(folder_name, f"{query if not subreddit else subreddit}_posts.csv")
        file_exists = os.path.isfile(csv_file)
        with open(csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=['post_id','comment_id','title', 'body', 'subreddit', 'upvotes', 'comments', 'date_time', 'author'])
            if not file_exists:
                writer.writeheader()
            writer.writerows(posts)

        if JSON_DUMP:
            json_file = os.path.join(folder_name, f"{query}_posts.json")
            with open(json_file, "a", encoding="utf-8") as f:
                json.dump(posts, f, indent=4)

    @staticmethod
    def save_query(folder, query):
        os.makedirs(folder, exist_ok=True)

        if not query:
            query = "None"

        with open(os.path.join(folder, "query.txt"), "w") as f:
            f.write(query)
        
class RedditFetcherGUI:
    def __init__(self):
        self.fetcher = RedditFetcher(self.progress_callback)
        self.root = tk.Tk()
        self.setup_gui()

    def setup_gui(self):
        self.root.title("Reddit Fetch Tool")
        self.root.geometry("425x350")

        # Initialize variables
        self.progress_var = tk.IntVar()
        self.safe_search_var = tk.IntVar()

        # Create GUI elements
        self.create_subreddit_selection()
        self.create_query_input()
        self.create_limit_selection()
        self.create_sort_selection()
        self.create_time_filter()
        self.create_safe_search()
        self.create_json_dump_checkbox()
        self.create_progress_elements()
        self.create_fetch_button()

    def create_subreddit_selection(self):
        ttk.Label(self.root, text="Enter Subreddit:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.subreddit_choice = ttk.Entry(self.root, width=40)
        self.subreddit_choice.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.subreddit_choice.insert(0, "")

    def create_query_input(self):
        ttk.Label(self.root, text="Search Query:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.query_entry = ttk.Entry(self.root, width=40)
        self.query_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

    def create_limit_selection(self):
        ttk.Label(self.root, text="Limit:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.limit_choice = ttk.Spinbox(self.root, from_=1, to=10000, width=38)
        self.limit_choice.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        self.limit_choice.set(10)

    def create_sort_selection(self):
        ttk.Label(self.root, text="Sort By:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.sort_choice = ttk.Combobox(self.root, values=["relevance", "hot", "top", "new", "comments"], state="readonly", width=37)
        self.sort_choice.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        self.sort_choice.current(0)

    def create_time_filter(self):
        ttk.Label(self.root, text="Time Filter:").grid(row=4, column=0, padx=5, pady=5, sticky='w')
        self.time_filter_choice = ttk.Combobox(self.root, values=["all", "day", "hour", "month", "week", "year"], state="readonly", width=37)
        self.time_filter_choice.grid(row=4, column=1, padx=5, pady=5, sticky='w')
        self.time_filter_choice.current(0)

    def create_safe_search(self):
        self.safe_search_check = ttk.Checkbutton(self.root, text="Enable Safe Search", variable=self.safe_search_var)
        self.safe_search_check.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky='w')

    def create_json_dump_checkbox(self):
        self.json_dump_var = tk.BooleanVar(value=False)
        self.json_dump_check = ttk.Checkbutton(self.root, text="Enable JSON Dump", variable=self.json_dump_var)
        self.json_dump_check.grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky='w')

    def create_progress_elements(self):
        self.progress_bar = Progressbar(self.root, orient="horizontal", length=400, mode="determinate", variable=self.progress_var)
        self.progress_bar.grid(row=7, column=0, columnspan=2, padx=5, pady=5)
        self.status_label = ttk.Label(self.root, text="Idle")
        self.status_label.grid(row=8, column=0, columnspan=2, padx=5, pady=5)

    def create_fetch_button(self):
        self.fetch_button = ttk.Button(self.root, text="Fetch Posts", command=self.start_fetch)
        self.fetch_button.grid(row=9, column=0, columnspan=2, padx=5, pady=5)


    def progress_callback(self, progress, status):
        assert 0 <= progress <= 100, "Progress must be between 0 and 100."
        assert isinstance(status, str), "Status must be a string."

        self.progress_var.set(progress)
        self.progress_bar['value'] = progress
        self.status_label.config(text=status)

    def start_fetch(self):
        subreddit = self.subreddit_choice.get()
        query = self.query_entry.get()
        limit = int(self.limit_choice.get())
        sort = self.sort_choice.get()
        time_filter = self.time_filter_choice.get()
        safe_search = "1" if self.safe_search_var.get() else "0"
        JSON_DUMP = self.json_dump_var.get()

        if not query and not subreddit:
            messagebox.showerror("Error", "Please enter either a search query or a subreddit.")
            return

        self.progress_var.set(0)
        self.progress_bar['value'] = 0

        def run_fetch():
            try:
                self.fetcher.fetch_reddit_data(subreddit, query, limit, sort, time_filter, safe_search, JSON_DUMP)
                self.root.after(0, lambda: self.status_label.config(text="Fetch Completed!"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

        Thread(target=run_fetch).start()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = RedditFetcherGUI()
    app.run()
