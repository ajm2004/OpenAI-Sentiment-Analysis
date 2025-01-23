import asyncio
from asyncpraw import Reddit
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

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

# Function to fetch top posts and their comments
async def fetch_top_posts_with_comments(reddit, subreddit_name, json_filename, post_limit):
    subreddit = await reddit.subreddit(subreddit_name)
    submissions = subreddit.top(limit=post_limit, time_filter="all")  # Fetch top posts with user-defined limit
    data = []

    async for submission in submissions:
        await submission.load()  # Ensure submission data is fully loaded
        await submission.comments.replace_more(limit=None)  # Load all comments
        post_data = {
            "Title": submission.title,
            "Body": submission.selftext,
            "ID": submission.id,
            "URL": submission.url,
            "Upvotes": submission.score,
            "Created_UTC": datetime.fromtimestamp(submission.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            # Number of comments:
            "Number_of_Comments": len(submission.comments.list()),
            "Comments": []
            
        }

        # Recursive function to process comments and their replies
        def process_comment(comment):
            comment_data = {
                "ID": comment.id,
                "Body": comment.body,
                "Upvotes": comment.score,
                "Created_UTC": datetime.fromtimestamp(comment.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                "Replies": []
            }
            # Process replies recursively
            if comment.replies:
                for reply in comment.replies:
                    comment_data["Replies"].append(process_comment(reply))
            return comment_data

        # Process top-level comments
        for comment in submission.comments.list():
            post_data["Comments"].append(process_comment(comment))

        data.append(post_data)

    # Save to JSON
    with open(json_filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
    print(f"Saved top {post_limit} posts with comments from r/{subreddit_name} in {json_filename}")

# Main asynchronous function
async def main():
    reddit = await create_reddit_instance()

    # Take user input for subreddit and post limit
    subreddit_name = input("Enter the subreddit name: ")
    try:
        post_limit = int(input("Enter the number of top posts to fetch: "))
    except ValueError:
        print("Invalid input! Please enter a number for the post limit.")
        return

    json_filename = f"top_{post_limit}_posts_with_comments_from_{subreddit_name}.json"

    try:
        # Fetch and save top posts with comments in hierarchical JSON format
        await fetch_top_posts_with_comments(reddit, subreddit_name, json_filename, post_limit)
    finally:
        # Ensure the session is closed
        await reddit.close()

# Run the main function
asyncio.run(main())