import chromadb
from langchain.embeddings.sentence_transformer import \
    SentenceTransformerEmbeddings
from langchain.vectorstores import Chroma

import ingest
from markdown_loader import load_markdown_data, query_with_doug

GH_USER = "defenseunicorns"
GH_REPO = "zarf"
PATH = 'docs'


class DocumentStore:
    def __init__(self):
        self.index_name = "default"
        self.client = chromadb.PersistentClient(path="db")
        self.collection = self.client.get_or_create_collection(name="default")
        self.ingestor = ingest.Ingest(
            self.index_name, self.client, self.collection)
        # For the sliding window
        self.chunk_size = 200
        self.overlap_size = 50

        self.username = "devopsdojoconsortium"
        self.repository = "dojoconsortium.org"
        self.path = "content/en/docs"

        # self.username = GH_USER
        # self.repository = GH_REPO
        # self.path = PATH

        self.url = f"https://api.github.com/repos/{self.username}/{self.repository}/contents/"

        self.embedding_function = SentenceTransformerEmbeddings(
            model_name="all-MiniLM-L6-v2")
        self.chroma_db = Chroma(embedding_function=self.embedding_function, collection_name="default",
                                client=self.client)

    # Try catch fails if collection cannot be found
    def does_collection_exist(self, collection_name):
        try:
            collection = self.client.get_collection(name=collection_name)
            if collection.count() > 0:
                return True
        except ValueError:
            return False

        return False

    def query_langchain(self, query_text):
        docs = self.chroma_db.similarity_search(query_text)
        return docs

    def query_with_doug(self, query_text):
        result = query_with_doug(self.client, query_text)
        return result['documents'][0][0]

    def load_pdf(self, path):
        self.ingestor.load_data(path)

    def load_doug_data(self):
        load_markdown_data(self.client, self.url, self.path)
