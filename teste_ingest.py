import os
import chromadb

from dotenv import load_dotenv

load_dotenv("/mnt/hd1tb/projetos/.env")

client = chromadb.CloudClient(
    api_key=os.getenv("CHROMA_API_KEY"),
    tenant=os.getenv("CHROMA_TENANT"),
    database=os.getenv("CHROMA_DATABASE")
)

collection = client.get_or_create_collection(
    name="teste_collection"
)

collection.add(
    documents=[
        "Pedro Álvares Cabral chegou ao Brasil em 1500."
    ],
    metadatas=[
        {
            "type": "historical_fact",
            "source": "contexto.txt"
        }
    ],
    ids=[
        "block_001"
    ]
)

print("Documento inserido!")
