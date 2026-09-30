import chromadb
from chromadb.config import Settings

client = chromadb.CloudClient(
    api_key="ck-2B6buDuWpmjRHYvfzYyvdmL6GwK8CEWaVY18Gz3Zrnh8",
    tenant="6bc9849c-6b26-4656-bc35-8ed88f03677e",
    database="sofia_knowledge_base"
)

collection = client.get_or_create_collection(
    name="teste_collection"
)

print("Collection criada com sucesso!")
print(collection.name)
