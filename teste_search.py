import os
import chromadb

from dotenv import load_dotenv

load_dotenv("/mnt/hd1tb/projetos/.env")

client = chromadb.CloudClient(
    api_key=os.getenv("CHROMA_API_KEY"),
    tenant=os.getenv("CHROMA_TENANT"),
    database=os.getenv("CHROMA_DATABASE")
)

collection = client.get_collection(
    name="teste_collection"
)

results = collection.query(
    query_texts=[
        "quem descobriu o brasil?"
    ],
    n_results=3
)

print(results)
