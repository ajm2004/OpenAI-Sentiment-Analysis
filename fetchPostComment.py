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
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import text2emotion as te
from collections import deque

load_dotenv()

# ======== COMPANY-SPECIFIC CONFIGURATION ========
# TODO: Modify these constants for your target company

# Product-related keywords - modify for your company's products
TECHNICAL_KEYWORDS = {
    # Technical terms and features
    "performance", "technology", "features",
    "specs", "specifications", "benchmark",
    "hardware", "software", "system",
    "configuration", "technical", "details",
    # Core company and brand names
    "amd", "radeon", "ryzen",  # Change these to your company's main brands
    
    # Product lines and technologies
    # Add your company's product lines, technologies, and key features
    "epyc", "threadripper", "vega", "rdna",
    "fsr", "freesync", "adrenalin",
    
    # Technical terms relevant to your industry
    # Modify these based on your industry's technical terminology
    "cores", "threads", "nm", "tdp", "clock speed",
    
    # Product model numbers/names
    # Add your company's product model numbers and names
    "ryzen 3", "ryzen 5", "ryzen 7", "ryzen 9",
    "radeon rx 6000", "radeon rx 7000"
}

# Keywords that indicate positive reputation
# Customize these based on what matters for your company's reputation
REPUTATION_KEYWORDS = {
    # General positive indicators
    "efficient", "reliable", "innovative",
    "recommend", "great", "helpful",
    
    # Support and documentation
    "support", "tutorial", "guide", "fix", "solution",
    
    # Performance and quality
    "improved", "better performance", "stable",
    "quality", "optimized"

    # Negative indicators can be added as well
    "bug", "issue", "problem", "error",
    "slow", "overheat", "crash"
}

# Industry-specific exclusions
# Modify these based on content you want to filter out
EXCLUDE_KEYWORDS = {
    "meme", "shitpost", "joke",
    "stock", "invest",  # Remove if financial content is relevant
    "fan art"  # Remove if community art is relevant
}

# Relevant post categories
# Customize based on your content needs
RELEVANT_FLAIRS = {
    "review", "discussion", "support",
    "rant", "news", "photo"
}

# Engagement thresholds
# Adjust these based on typical engagement in your target subreddits
MIN_POST_UPVOTES = 10
MIN_COMMENT_UPVOTES = 3
SENTIMENT_THRESHOLD = 0.25

# Emotion analysis settings
POSITIVE_EMOTIONS = {"Happy", "Surprise"}  # Customize relevant emotions
POSITIVE_EMOTION_THRESHOLD = 0.3

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

sentiment_analyzer = SentimentIntensityAnalyzer()

# Initialize asyncpraw instance
async def create_reddit_instance():
    return Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent="my user agent",
        username=USERNAME,
        password=PASSWORD,
    )

# ======== FILTER FUNCTIONS ========
def contains_company_keywords(text):
    """Check if text contains relevant technical keywords"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in TECHNICAL_KEYWORDS)

def is_opinion_driven(text, threshold=SENTIMENT_THRESHOLD):
    sentiment = sentiment_analyzer.polarity_scores(text)
    return abs(sentiment["compound"]) > threshold  # Exclude neutral posts

def is_high_engagement(post, min_upvotes=10, min_comments=5):
    return post.score >= min_upvotes and post.num_comments >= min_comments

def has_relevant_flair(post):
    if post.link_flair_text:
        flair_text = post.link_flair_text.lower()
        if any(flair in flair_text for flair in RELEVANT_FLAIRS):
            return True
        if any(keyword in flair_text for keyword in TECHNICAL_KEYWORDS):
            return True
    return False

def is_relevant(post):
    title = post.title.lower()
    body = post.selftext.lower() if post.selftext else ""
    return not any(banned_word in title or banned_word in body 
                   for banned_word in EXCLUDE_KEYWORDS)

def adds_reputation_value(text):
    """Check if text contains elements beneficial to company's reputation"""
    text_lower = text.lower()
    
    # Keyword check
    if any(keyword in text_lower for keyword in REPUTATION_KEYWORDS):
        return True
    
    # Informative content patterns
    informative_patterns = {
        "how to", "tutorial", "guide", "step by step",
        "fix for", "solution to", "problem solved"
    }
    if any(pattern in text_lower for pattern in informative_patterns):
        return True
    
    # Structured problem-solving indicators
    if any(text_lower.count(indicator) >= 2 for indicator in ["•", "- ", "1.", "2.", "3."]):
        return True
    
    return False

def analyze_emotions(text):
    """Analyze text for emotional content using multiple techniques"""
    try:
        # Emotion detection using text2emotion
        emotions = te.get_emotion(text)
        
        # VADER sentiment for additional context
        vader_sentiment = sentiment_analyzer.polarity_scores(text)
        
        return {
            "emotions": emotions,
            "vader_sentiment": vader_sentiment
        }
    except:
        return None

def has_positive_emotional_value(emotion_data):
    """Determine if text has significant positive emotional value"""
    if not emotion_data:
        return False
    
    # Check for dominant positive emotions
    emotions = emotion_data["emotions"]
    if any(emotions[emotion] > POSITIVE_EMOTION_THRESHOLD 
           for emotion in POSITIVE_EMOTIONS):
        return True
    
    # Check VADER compound score as fallback
    if emotion_data["vader_sentiment"]["compound"] > SENTIMENT_THRESHOLD:
        return True
    
    return False

class StatusCallback:
    def __init__(self, app):
        self.app = app
        self.total_steps = 0
        self.current_step = 0

    def __call__(self, message, progress=None, post_info=None):
        """Update status with message and optional progress percentage"""
        if post_info:
            self.app.root.after(0, self.app.update_post_display, *post_info)
        if progress is not None:
            self.app.root.after(0, self._update_gui, message, progress)
        else:
            self.app.root.after(0, self._update_gui, message, -1)

    def _update_gui(self, message, progress):
        """Update GUI elements with status and progress"""
        self.app.status_var.set(message)
        
        if progress >= 0:
            if self.app.progress["mode"] != "determinate":
                self.app.progress["mode"] = "determinate"

            if progress == 100:
                self.app.progress.stop()
            self.app.progress["value"] = progress
        else:
            if self.app.progress["mode"] != "indeterminate":
                self.app.progress["mode"] = "indeterminate"
                self.app.progress.start(10)
                

async def analyse_comments_sentiment(submission, status_callback):
    """Analyze comments to determine if there's significant discussion or positive emotion"""
    await submission.comments.replace_more(limit=0)
    opinionated_comments = 0
    total_sentiment = 0
    positive_emotion_comments = 0
    
    # Analyze top 15 comments
    for comment in submission.comments[:15]:
        try:
            # Analyze both sentiment and emotions
            sentiment = sentiment_analyzer.polarity_scores(comment.body)
            emotions = analyze_emotions(comment.body)
            
            # Check for strong opinions
            if abs(sentiment["compound"]) > SENTIMENT_THRESHOLD:
                opinionated_comments += 1
                total_sentiment += abs(sentiment["compound"])
            
            # Check for positive emotions
            if emotions and has_positive_emotional_value(emotions):
                positive_emotion_comments += 1
                
        except Exception as e:
            status_callback(f"⚠️ Error analyzing comment: {str(e)}")
            continue
    
    # Acceptance criteria
    acceptance_reasons = []
    if opinionated_comments >= 3:
        acceptance_reasons.append(f"{opinionated_comments} opinionated comments")
    if positive_emotion_comments >= 2:
        acceptance_reasons.append(f"{positive_emotion_comments} positive emotion comments")
    
    if acceptance_reasons:
        status_callback(
            f"🟢 Post accepted based on: {', '.join(acceptance_reasons)}"
        )
        return True
    return False

async def fetch_posts_and_comments(reddit, subreddit_name, post_limit, post_sort, status_callback):
    try:
        status_callback(f"🟠 Connecting to r/{subreddit_name}...", 0)
        subreddit = await reddit.subreddit(subreddit_name)
        
        # Create output directory with generic name
        output_dir = f"data_reddit_{subreddit_name}"
        os.makedirs(output_dir, exist_ok=True)
        status_callback(f"🟣 Created output directory: {output_dir}")

        # Configure sorting
        sort_mapping = {
            "Top (All Time)": ("top", "all"),
            "Top (Year)": ("top", "year"),
            "Top (Month)": ("top", "month"),
            "Hot": ("hot", None),
            "New": ("new", None)
        }
        sort_type, time_filter = sort_mapping.get(post_sort, ("new", None))

        status_callback(f"🔵 Fetching {post_limit} {post_sort} posts...", 10)
        if sort_type == "top":
            submissions = subreddit.top(limit=post_limit, time_filter=time_filter)
        elif sort_type == "hot":
            submissions = subreddit.hot(limit=post_limit)
        else:
            submissions = subreddit.new(limit=post_limit)

        filtered_posts = []
        total_processed = 0
        filtered_out = 0

        with open(f"{output_dir}/{subreddit_name}_posts.csv", "w", encoding="utf-8") as post_file:
            post_writer = csv.writer(post_file)
            post_writer.writerow([
                "Post ID", "Title", "Body", "Upvotes", "URL", 
                "Created UTC", "Num Comments", "Sentiment", "Flair"
            ])

            async for submission in submissions:
                try:
                    total_processed += 1
                    current_progress = (total_processed / post_limit) * 90 + 10  # 10-100% range
                    status_callback(
                        f"⚪ Processing post {total_processed}/{post_limit} "
                        f"(Kept: {len(filtered_posts)}, Filtered: {filtered_out})",
                        current_progress
                    )
                    
                    await submission.load()
                    
                    # --- Filter Checks with Logging ---
                    filter_reasons = []
                    
                    # Keyword check
                    if not contains_company_keywords(submission.title + submission.selftext):
                        filter_reasons.append("no relevant keywords")
                    
                    # Content relevance
                    if not is_relevant(submission):
                        filter_reasons.append("irrelevant content")
                    
                    # Flair check
                    if not has_relevant_flair(submission):
                        filter_reasons.append(f"wrong flair: {submission.link_flair_text}")
                    
                    # Upvote threshold
                    if submission.score < MIN_POST_UPVOTES:
                        filter_reasons.append(f"low upvotes ({submission.score})")
                    
                    # Sentiment check
                    is_neutral = not is_opinion_driven(submission.selftext)
                    
                    # If only rejected due to neutral sentiment, analyze comments
                    if len(filter_reasons) == 0 and is_neutral:
                        status_callback(
                            f"🔍 Post is neutral, analyzing comments for '{submission.title[:30]}...'"
                        )
                        if await analyse_comments_sentiment(submission, status_callback):
                            is_neutral = False  # Override neutral status if comments are opinionated
                        else:
                            filter_reasons.append("neutral sentiment (including comments)")
                    elif is_neutral:
                        filter_reasons.append("neutral sentiment")

                    # Reject if any filter failed
                    if filter_reasons:
                        filtered_out += 1
                        status_callback(
                            f"🔴 Filtered post '{submission.title[:50]}...' "
                            f"Reasons: {', '.join(filter_reasons)}",
                            current_progress,
                            (submission.title[:100], "filtered", ', '.join(filter_reasons))
                        )

                        # Log filtered post to CSV into a new file for rejected posts
                        with open(f"{output_dir}/filtered_posts.csv", "a", encoding="utf-8") as filtered_file:
                            filtered_writer = csv.writer(filtered_file)
                            filtered_writer.writerow([
                                submission.id,
                                submission.title,
                                submission.selftext,
                                submission.score,
                                submission.url,
                                datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                                submission.num_comments,
                                sentiment_analyzer.polarity_scores(submission.selftext)["compound"],
                                submission.link_flair_text,
                                ', '.join(filter_reasons)
                            ])
                        continue

                    

                    # --- Process Comments ---
                    status_callback(f"🟡 Processing comments for post '{submission.title[:30]}...'")
                    filtered_comments = []
                    await submission.comments.replace_more(limit=0)
                    
                    for comment in submission.comments:
                        comment_reasons = []
                        if comment.score < MIN_COMMENT_UPVOTES:
                            comment_reasons.append(f"low votes ({comment.score})")
                        # if not is_opinion_driven(comment.body):
                        #     comment_reasons.append("neutral sentiment")
                            
                        if not comment_reasons:
                            filtered_comments.append({
                                "comment_id": comment.id,
                                "body": comment.body,
                                "upvotes": comment.score,
                                "created_utc": comment.created_utc,
                                "sentiment": sentiment_analyzer.polarity_scores(comment.body)
                            })
                        else:
                            status_callback(
                                f"⚫ Filtered comment: {comment.body[:30]}... "
                                f"Reasons: {', '.join(comment_reasons)}"
                            )

                    # Comment quantity check
                    if len(filtered_comments) < 2:
                        status_callback(
                            f"🟤 Skipped post due to low comments ({len(filtered_comments)})"
                        )
                        filtered_out += 1
                        continue

                    # --- Store Valid Post ---
                    status_callback(f"🟢 Keeping post '{submission.title[:30]}...'")
                    
                    # Write to CSV
                    post_writer.writerow([
                        submission.id,
                        submission.title,
                        submission.selftext,
                        submission.score,
                        submission.url,
                        datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                        submission.num_comments,
                        sentiment_analyzer.polarity_scores(submission.selftext)["compound"],
                        submission.link_flair_text
                    ])

                    # Build JSON structure
                    post_data = {
                        "post_id": submission.id,
                        "title": submission.title,
                        "body": submission.selftext,
                        "upvotes": submission.score,
                        "url": submission.url,
                        "created_utc": submission.created_utc,
                        "sentiment": sentiment_analyzer.polarity_scores(submission.selftext),
                        "flair": submission.link_flair_text,
                        "comments": filtered_comments
                    }
                    filtered_posts.append(post_data)

                    # Save individual post JSON
                    post_dir = os.path.join(output_dir, submission.id)
                    os.makedirs(post_dir, exist_ok=True)
                    with open(f"{post_dir}/post.json", "w") as f:
                        json.dump(post_data, f, indent=4)
                        status_callback(f"🔵 Saved JSON for post {submission.id}")

                    # Save comments as CSV
                    with open(f"{post_dir}/comments.csv", "w", encoding="utf-8") as comment_file:
                        comment_writer = csv.writer(comment_file)
                        comment_writer.writerow([
                            "Post  Id","Comment ID", "Body", "Upvotes", "Created UTC", "Sentiment"
                        ])
                        for comment in filtered_comments:
                            comment_writer.writerow([
                                submission.id,
                                comment["comment_id"],
                                comment["body"],
                                comment["upvotes"],
                                datetime.fromtimestamp(comment["created_utc"], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                                comment["sentiment"]["compound"]
                            ])

                    # For accepted posts, add this before storing:
                    status_callback(
                        f"Processing post {total_processed}/{post_limit}",
                        current_progress,
                        (
                            submission.title[:100],
                            "accepted",
                            f"Score: {submission.score}, Comments: {submission.num_comments}, "
                            f"Sentiment: {sentiment_analyzer.polarity_scores(submission.selftext)['compound']:.2f}"
                        )
                    )

                except Exception as post_error:
                    status_callback(f"⚠️ Error processing post {submission.id}: {str(post_error)}")

        # Final summary
        status_callback(
            f"Completed r/{subreddit_name}\n"
            f"- Total processed: {total_processed}\n"
            f"- Posts kept: {len(filtered_posts)}\n"
            f"- Posts filtered: {filtered_out}\n"
            f"- Comments collected: {sum(len(p['comments']) for p in filtered_posts)}",
            100
        )
        

        return True

    except Exception as e:
        status_callback(f"⛔ Critical error: {str(e)}", -1)
        return False

# Create a GUI for input
class RedditFetcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reddit Content Analyzer")  # Generic title
        
        # Increase window size to accommodate filtered posts display
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Configure grid weights
        self.root.grid_columnconfigure(1, weight=1)
        for i in range(6):  # Increased range for new widget
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

        # Simplified status frame
        status_frame = ttk.LabelFrame(root, text="Status")
        status_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')
        status_frame.grid_columnconfigure(0, weight=1)

        self.status_var = StringVar(value="Ready")
        self.status_label = Label(status_frame, textvariable=self.status_var, 
                                wraplength=750, justify='left', 
                                font=('TkDefaultFont', 10))
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky='w')

        # Rename and update Posts Display
        posts_frame = ttk.LabelFrame(root, text="Post Processing Info")
        posts_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')
        posts_frame.grid_columnconfigure(0, weight=1)
        posts_frame.grid_rowconfigure(0, weight=1)

        self.posts_display = Text(posts_frame, height=10, wrap='word')
        self.posts_display.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        
        # Add scrollbar to posts display
        scrollbar = ttk.Scrollbar(posts_frame, orient='vertical', command=self.posts_display.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.posts_display.configure(yscrollcommand=scrollbar.set)
        
        # Progress bar
        self.progress = ttk.Progressbar(root, mode='determinate', maximum=100)
        self.progress.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky='ew')

        # Button frame (moved to row 4)
        button_frame = ttk.Frame(root)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky='ew')
        button_frame.grid_columnconfigure(0, weight=1)

        self.fetch_button = ttk.Button(button_frame, text="Fetch Posts", command=self.start_fetch)
        self.fetch_button.grid(row=0, column=0)

    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

    def update_post_display(self, title, status, details):
        """Update the posts display with new post information"""
        self.posts_display.config(state='normal')
        
        # Add timestamp to post entries
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if status == "accepted":
            prefix = "🟢 Accepted"
            self.posts_display.insert(END, f"[{timestamp}] {prefix}: {title}\n", "accepted")
        else:
            prefix = "🔴 Filtered"
            self.posts_display.insert(END, f"[{timestamp}] {prefix}: {title}\n", "filtered")
        
        self.posts_display.insert(END, f"Details: {details}\n\n")
        self.posts_display.see(END)
        self.posts_display.config(state='disabled')

    def start_fetch(self):
        self.fetch_button.config(state='disabled')
        self.progress.start(10)
        self.posts_display.config(state='normal')
        self.posts_display.delete(1.0, END)
        self.posts_display.config(state='disabled')
        
        # Configure text tags for colors
        self.posts_display.tag_configure("accepted", foreground="green")
        self.posts_display.tag_configure("filtered", foreground="red")
        
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
            
            status_callback = StatusCallback(self)
            
            success = loop.run_until_complete(
                fetch_posts_and_comments(
                    reddit, 
                    subreddit_name, 
                    post_limit, 
                    post_sort,
                    status_callback
                )
            )
            
            loop.run_until_complete(reddit.close())
            loop.close()

            if success:
                # self.finish_fetch(f"Successfully fetched data for r/{subreddit_name}")
                # Set progress to 100% after completion
                pass
            else:
                self.finish_fetch("Failed to fetch data. Check the status messages above.")
                
        except Exception as e:
            self.finish_fetch(f"Error: {str(e)}")

    def finish_fetch(self, message):
        self.root.after(0, self._finish_fetch_gui, message)

    def _finish_fetch_gui(self, message):
        self.status_var.set(message)
        if self.progress["mode"] == "indeterminate":
            self.progress.stop()
        self.progress["mode"] = "determinate"
        self.progress["value"] = 100
        self.fetch_button.config(state='normal')

# Run the application
if __name__ == "__main__":
    root = Tk()
    app = RedditFetcherApp(root)
    root.mainloop()


