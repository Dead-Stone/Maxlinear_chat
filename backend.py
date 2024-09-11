from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from weaviate import Client, auth
from cachetools import TTLCache
import os, re
from dotenv import load_dotenv
import json
from datetime import datetime, timezone

load_dotenv()

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = os.getenv('OPENAI_API_KEY')

weaviate_client = Client(
    url=os.getenv('WCS_URL'),
    auth_client_secret=auth.AuthApiKey(api_key=os.getenv('WCS_API_KEY'))
)

class Message(BaseModel):
    content: str


cache = TTLCache(maxsize=100, ttl=300)

def read_prompt_from_file(filename='prompt.txt'):
    try:
        with open(filename, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
        return None
    except IOError:
        print(f"Error: There was an issue reading the file '{filename}'.")
        return None

prompt_template = read_prompt_from_file()
if not prompt_template:
    raise Exception("Failed to load prompt template")

def create_weaviate_schema():
    schema = {
        "classes": [{
            "class": "Article",
            "description": "A news article",
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "The full content of the article"
                },
                {
                    "name": "title",
                    "dataType": ["string"],
                    "description": "The title of the article"
                },
                {
                    "name": "url",
                    "dataType": ["string"],
                    "description": "The URL of the article"
                },
                {
                    "name": "date",
                    "dataType": ["date"],
                    "description": "The publication date of the article"
                }
            ]
        }]
    }
    
    try:
        weaviate_client.schema.create(schema)
        print("Weaviate schema created successfully")
    except Exception as e:
        print(f"Error creating Weaviate schema: {e}")

def read_news_articles():
    with open('./data/maxlinear_news_combined.json', 'r', encoding='utf-8') as file:
        articles = json.load(file)
    return articles

news_articles = read_news_articles()
print(f"Loaded {len(news_articles)} news articles successfully.")

def delete_existing_schema():
    try:
        existing_schema = weaviate_client.schema.get()
        for class_obj in existing_schema['classes']:
            if class_obj['class'] == 'Article':
                weaviate_client.schema.delete_class('Article')
                print("Existing 'Article' class deleted")
                return
    except Exception as e:
        print(f"Error checking/deleting existing schema: {e}")

def extract_metadata(article):
    metadata = {}
    metadata['title'] = article.get('title', '')
    date_str = article.get('date', '')
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        utc_date = date_obj.replace(tzinfo=timezone.utc)
        metadata['date'] = utc_date.isoformat().replace('+00:00', 'Z')
    except ValueError:
        print(f"Warning: Unable to parse date: {date_str}")
        metadata['date'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    metadata['url'] = article.get('url', '')
    return metadata

async def embed_articles():
    for i, article in enumerate(news_articles):
        metadata = extract_metadata(article)
        try:
            embedding = generate_embedding(article.get('content', ''))
            if not embedding:
                print(f"Skipping article {i + 1} due to embedding error")
                continue
            
            weaviate_client.data_object.create(
                data_object={
                    "content": article.get('content', ''),
                    "title": metadata['title'],
                    "url": metadata['url'],
                    "date": metadata['date']
                },
                class_name="Article",
                vector=embedding
            )
            print(f"Successfully added article {i + 1}")
        except Exception as e:
            print(f"Error adding article {i + 1}: {e}")

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

def search_weaviate(query, top_n=10):
    query_vector = generate_embedding(query)
    try:
        print("Searching Weaviate for similar articles...")
        result = (weaviate_client.query
            .get("Article", ["content", "title", "url", "date"])
            .with_hybrid(query=query, vector=query_vector, alpha=0.6)
            .with_limit(top_n)
            .do())
        print("result",result)
        if 'data' in result and 'Get' in result['data']:
            return result['data']['Get']['Article']
        else:
            print("No data found in search results")
            return []

    except Exception as e:
        print(f"Error searching Weaviate: {e}")
        return []

def generate_response(query):
    if query in cache:
        return cache[query]
    
    similar_articles = search_weaviate(query)
    # print("similar_articles",similar_articles)
    if not similar_articles:
        return "No similar articles found."

    combined_content = "\n\n".join(
        [f"Article {i+1}: \"{article['title']}\" (URL: {article['url']}, Date: {article['date']})\n\n{article['content'][:500]}..." 
         for i, article in enumerate(similar_articles)]
    )
    
    prompt = prompt_template.format(combined_content=combined_content, query=query)
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.2,
        ) 
        print("response",response)
        generated_response = response.choices[0].message.content
        print("generated_response",generated_response)
        cache[query] = generated_response
        # print("cache",cache)
        return generated_response
    except Exception as e:
        print(f"Error generating response: {e}")
        return "An error occurred while generating the response."

# url_pattern = re.compile(r'(\d+)\.\s+(.*?)\s+(https?://\S+)')

def extract_sources_from_response(response_text):
    sources = []
    
# Regular expression pattern to extract the number, text, and URL
    pattern = r"(\d+)\.\s(.+?)\s(https?://[^\s]+)"

    # Isolating the section with sources
    if "Sources" in response_text:
        sources_text = response_text.split("Sources")[1]
        print("sources_text",sources_text)
        print("sources_text.split",sources_text.split('\n'))
        
        # Split by lines and match against our regular expression
        # for line in sources_text.split('\n')[1:]:
        #     print("line",line)
        match = re.findall(pattern, response_text)
        for line in match:
          print("line:",line)
          l=list(line)
          sources.append({
                  "number": l[0],
                  "title": l[1],
                  "url": l[2]
              })
        # Format the result as a list of dictionaries
        for entry in sources:
            print(f"Number: {entry['number']}, Text: {entry['title']}, URL: {entry['url']}")
    
    return sources

@app.post("/send_message")
def send_message(message: Message):
    try:
        print("message.content", message.content)
        
        # Generate response text
        response_text = generate_response(message.content)
        print("response_text", response_text)
        
        if response_text:
            # Extract sources from the response
            sources = extract_sources_from_response(response_text)
            print("sources", sources)
            
            # Remove the sources from the response_text
            cleaned_response_text = remove_sources_from_response(response_text)
            print("cleaned_response_text", cleaned_response_text)
            
            return {
                "response": cleaned_response_text,  # Cleaned response without sources
                "sources": sources  # List of sources extracted
            }
        else:
            raise HTTPException(status_code=500, detail="No response generated")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def remove_sources_from_response(response_text: str) -> str:
    """
    Removes the sources section from the response text.
    Assumes the sources section starts with "Sources:" or "Top 5 most relevant sources used to generate the response".
    """
    pattern = r"(Sources:|Top 5 most relevant sources used to generate the response:).*$"
    cleaned_response = re.sub(pattern, '', response_text, flags=re.DOTALL).strip()
    return cleaned_response

@app.on_event("startup")
async def startup():
    delete_existing_schema()
    create_weaviate_schema()
    await embed_articles()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)