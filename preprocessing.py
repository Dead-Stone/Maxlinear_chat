import openai
from weaviate import Client, auth
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize Weaviate client
weaviate_client = Client(
    url=os.getenv('WCS_URL'),
    auth_client_secret=auth.AuthApiKey(api_key=os.getenv('WCS_API_KEY'))
)

# Function to read news articles
def read_news_articles():
    with open('./data/maxlinear_news_combined.json', 'r', encoding='utf-8') as file:
        articles = json.load(file)
    return articles

news_articles = read_news_articles()

def extract_metadata(article):
    metadata = {}
    metadata['title'] = article.get('title', '')
    date_str = article.get('date', '')
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        utc_date = date_obj.replace(tzinfo=timezone.utc)
        metadata['date'] = utc_date.isoformat().replace('+00:00', 'Z')  # RFC3339 format
    except ValueError:
        print(f"Warning: Unable to parse date: {date_str}")
        metadata['date'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    metadata['url'] = article.get('url', '')
    return metadata

def generate_embedding(text):
    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=[text]
        )
        if isinstance(response, dict) and 'data' in response:
            return response['data'][0]['embedding']
        elif hasattr(response, 'data'):
            return response.data[0].embedding
        else:
            print(f"Unexpected response format: {response}")
            return []
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []

def embed_articles():
    embeddings_data = []
    
    for i, article in enumerate(news_articles):
        metadata = extract_metadata(article)
        try:
            embedding = generate_embedding(article.get('content', ''))
            if not embedding:
                print(f"Skipping article {i + 1} due to embedding error")
                continue

            # Prepare the embedding and metadata for saving
            embeddings_data.append({
                "content": article.get('content', ''),
                "title": metadata['title'],
                "url": metadata['url'],
                "date": metadata['date'],
                "embedding": embedding
            })

            print(f"Successfully processed article {i + 1}")
        except Exception as e:
            print(f"Error processing article {i + 1}: {e}")

    # Save embeddings to file
    with open('./data/embeddings.json', 'w', encoding='utf-8') as f:
        json.dump(embeddings_data, f, ensure_ascii=False, indent=4)

    print(f"Successfully saved embeddings for {len(embeddings_data)} articles.")

if __name__ == "__main__":
    embed_articles()
