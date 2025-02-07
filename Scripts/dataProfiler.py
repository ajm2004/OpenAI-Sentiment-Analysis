import pandas as pd
import argparse

def count_unique_items(file_path):
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Count unique comment_ids and post_ids
        unique_comments = len(df['comment_id'].unique()) if 'comment_id' in df.columns else 0
        unique_posts = len(df['post_id'].unique()) if 'post_id' in df.columns else 0
        
        # Print results
        print(f"Number of unique comments: {unique_comments}")
        print(f"Number of unique posts: {unique_posts}")
        print(f"Total unique items: {unique_comments + unique_posts}")
        
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Error processing file: {str(e)}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Count unique comments and posts in a CSV file')
    parser.add_argument('-f', '--file', type=str, required=True, help='Path to the CSV file')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Process the file
    count_unique_items(args.file)

if __name__ == "__main__":
    main()