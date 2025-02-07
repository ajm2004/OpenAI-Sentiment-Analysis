import os
import sys
import pandas as pd

def main():
    if len(sys.argv) < 2:
        print("Usage: python combine_csv.py <parent_folder>")
        sys.exit(1)

    parent_folder = sys.argv[1]

    # List to collect all dataframes
    all_dfs = []
    print("="*50)

    # Walk through parent_folder and find subfolders containing data_<x>.csv & query.txt
    for root, dirs, files in os.walk(parent_folder):
        

        csv_files = [f for f in files if f.lower().endswith(".csv")]
        txt_files = [f for f in files if f.lower().endswith(".txt")]

        # We expect exactly one CSV (e.g. data_<x>.csv) and one query.txt in each subfolder
        if len(csv_files) == 1 and len(txt_files) == 1:

            print(f"Processing folder: {root}...")

            csv_path = os.path.join(root, csv_files[0])
            txt_path = os.path.join(root, txt_files[0])

            # Read the query from the query.txt file
            with open(txt_path, "r", encoding="utf-8") as txt_file:
                query_text = txt_file.read().strip()

            # Read the CSV into a DataFrame
            df = pd.read_csv(csv_path, on_bad_lines='warn')

            # Append the query text as a new column
            df["query"] = query_text

            # Collect for later concatenation
            all_dfs.append(df)

    if not all_dfs:
        print("No valid CSV/query pairs found. Exiting.")
        sys.exit(0)

    print("="*50)

    # Concatenate all dataframes
    combined_df = pd.concat(all_dfs, ignore_index=True)

    # Drop duplicates based on the composite key (post_id, comment_id)
    combined_df.drop_duplicates(subset=["post_id", "comment_id"], inplace=True)

    # Reorder columns to match the final desired format
    final_columns = [
        "post_id",
        "comment_id",
        "title",
        "body",
        "subreddit",
        "upvotes",
        "comments",
        "date_time",
        "author",
        "query"
    ]
    # Keep only these columns (if they exist) in the correct order
    # (In case some CSV might have extra columns, or missing columns raise error)
    existing_columns = [col for col in final_columns if col in combined_df.columns]
    combined_df = combined_df[existing_columns]

    # Print no.of posts and comments
    num_of_posts = combined_df["post_id"].nunique()
    num_of_comments = combined_df["comment_id"].nunique()
    print(f"Total number of posts: {num_of_posts}")
    print(f"Total number of comments: {num_of_comments}")
    print(f"Total number of Records: {num_of_posts + num_of_comments:,}")
    print("="*50)

    # Write combined data to CSV
    output_csv = "combined_data.csv"
    combined_df.to_csv(output_csv, index=False)
    print(f"Combined CSV successfully saved as {output_csv}")
    print(f"File size: {os.path.getsize(output_csv)/(1024*1024):.2f} MB")
    print("="*50)

if __name__ == "__main__":
    main()
