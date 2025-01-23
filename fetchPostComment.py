import asyncio
from asyncpraw import Reddit
import json
import csv
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from tkinter import Tk, Label, Entry, Button, StringVar, IntVar, OptionMenu

load_dotenv()

USERNAME = os.getenv('USER')
PASSWORD = os.getenv('PASSWORD') 
CLIENT_ID = os.getenv('CLIENT_ID') 
CLIENT_SECRET = os.getenv('CLIENT_SECRET') 

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
async def fetch_posts_and_comments(reddit, subreddit_name, post_limit, post_sort):
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

    output_dir = f"reddit_data_{subreddit_name}"
    os.makedirs(output_dir, exist_ok=True)

    post_csv = os.path.join(output_dir, f"{subreddit_name}_posts.csv")
    posts_json = []

    with open(post_csv, "w", encoding="utf-8") as post_file:
        post_writer = csv.writer(post_file)
        post_writer.writerow(["Post ID", "Title", "Body", "Upvotes", "URL", "Created UTC", "Number of Comments"])

        async for submission in submissions:
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

            # Save comments for each post in CSV
            comments_csv = os.path.join(post_folder, f"comments.csv")
            comments_json = []
            with open(comments_csv, "w", encoding="utf-8") as comments_file:
                comments_writer = csv.writer(comments_file)
                comments_writer.writerow(["Comment ID", "Body", "Upvotes", "Created UTC"])

                await submission.comments.replace_more(limit=0)
                for comment in submission.comments:
                    comment_data = {
                        "Comment ID": comment.id,
                        "Body": comment.body,
                        "Upvotes": comment.score,
                        "Created UTC": datetime.fromtimestamp(comment.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    comments_writer.writerow([
                        comment.id,
                        comment.body,
                        comment.score,
                        datetime.fromtimestamp(comment.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    ])
                    comments_json.append(comment_data)

            # Save hierarchical JSON for the post
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

    # Save all posts as JSON
    all_posts_json_path = os.path.join(output_dir, f"{subreddit_name}_posts.json")
    with open(all_posts_json_path, "w", encoding="utf-8") as all_posts_json_file:
        json.dump(posts_json, all_posts_json_file, indent=4)

    print(f"Saved posts and comments from r/{subreddit_name} in {output_dir}")

# Create a GUI for input
class RedditFetcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reddit Fetcher")

        # Subreddit name
        Label(root, text="Subreddit Name:").grid(row=0, column=0, padx=10, pady=5)
        self.subreddit_name = StringVar()
        Entry(root, textvariable=self.subreddit_name).grid(row=0, column=1, padx=10, pady=5)

        # Number of posts
        Label(root, text="Number of Posts:").grid(row=1, column=0, padx=10, pady=5)
        self.post_limit = IntVar(value=10)
        Entry(root, textvariable=self.post_limit).grid(row=1, column=1, padx=10, pady=5)

        # Sort type
        Label(root, text="Sort by:").grid(row=2, column=0, padx=10, pady=5)
        self.post_sort = StringVar(value="Top (All Time)")
        OptionMenu(root, self.post_sort, "Top (All Time)", "Top (Year)", "Top (Month)", "Hot", "New").grid(row=2, column=1, padx=10, pady=5)

        # Start button
        Button(root, text="Fetch Posts", command=self.fetch_posts).grid(row=4, column=0, columnspan=2, pady=20)

    def fetch_posts(self):
        subreddit_name = self.subreddit_name.get()
        post_limit = self.post_limit.get()
        post_sort = self.post_sort.get()

        if not subreddit_name:
            print("Please fill in all fields.")
            return

        # Get or create an event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the async functions
        reddit = loop.run_until_complete(create_reddit_instance())
        try:
            loop.run_until_complete(fetch_posts_and_comments(reddit, subreddit_name, post_limit, post_sort))
        finally:
            # Ensure the Reddit instance is properly closed
            loop.run_until_complete(reddit.close())

# Run the application
if __name__ == "__main__":
    root = Tk()
    app = RedditFetcherApp(root)
    root.mainloop()