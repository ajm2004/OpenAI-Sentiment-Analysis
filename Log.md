# CW1

## WEEK 1

We formed the group

## WEEK 2

We researched different companies, and decided to choose OpenAI for company reputation analysis, due to the large number of data available related to the company and its products, as well as the diversity of the subreddits.

- **AJAY**: Hands on electronics
- **ANSON**: Cars
- **JONATHAN**: AI Research Companies (OpenAI, Deepseek, Anthropic, etc.)
- **SIDDH**: CPU and GPU

## WEEK 3

Ajay and Siddh built a GUI and wrote code to quickly extract posts and comments from Reddit.

AJAY: r/singularity

ANSON: r/technology

JONATHAN: r/OpenAI

SIDDH: r/ChatGPT

We collectively collected over 600k records from Reddit by providing queries related to OpenAI and its products

## WEEK 4

We realized that there was too much low quality data in our dataset. A lot of the records were replies to previous comments on a post, so a sentiment analysis model would not have the adequate context to make a decision on the company,

Therefore, we decided to repeat our data collection, this time, only collecting posts and their top-level comments. These would be processed, converted to TFIDF vectors and used to calculate cosine similarity to a query, in order to retrieve only relevant records.

AJAY: Repeated the data collection and restricted to top-level comments

ANSON: Conducted the text preprocessing, vectorized the text using TF-IDF and calculated cosine similarity to a query, in order to select the relevant rows.

JONATHAN: Labelled the data using a Sentiment Analysis Transformer model from Hugging Face (Part 1 of the labelling pipeline)

SIDDH: Heuristically filtered the data to remove too short/too long records, etc.

## WEEK 5

Upon manually labelling the data, we realized that ~40% of the 450 labelled claims were irrelevant, indicating that tdidf performed poorly. Therefore, we are going ahead for an updated round of retrieval using embeddings similarity:

JONATHAN: Retrieving the most semantically relevant data with an embedding model, Labelling data with TextBlob/Vader.
