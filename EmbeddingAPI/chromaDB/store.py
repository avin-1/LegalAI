from chromadb import PersistentClient
import os
# TO avoid different script reading from different db's we set the db path to root folder
BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(BASE), "chromadb_store")

# persistent chroma instance
chroma = PersistentClient(path="chromadb_store")

class ChromaStore:
    def __init__(self, user_id: int):
        self.user_id = user_id

    def collection(self):
        return chroma.get_or_create_collection(
            name=f"vectors_{self.user_id}"
        )

    def create_embeddings(self):
        # I generated this doc string with AI
        """Create and store text embeddings for the user's uploaded document.

                This method loads the processed text file for the current user, splits it
                into fixed-size chunks, and inserts those chunks into the underlying vector
                collection for later search and retrieval. Chunking keeps each document
                segment small enough to embed efficiently and improves recall during search.

                Processing steps (first-principles reasoning):
                1. Resolve the path to the user's `output.txt` file.
                2. Read the entire text into memory.
                3. Slice the text into contiguous chunks of equal size (`chunk_size`).
                4. Insert each chunk into the collection with:
                - a stable, unique ID (`doc_<user_id>_<index>`)
                - metadata describing the chunk index.

                The method assumes the collection backend is already configured by
                `self.collection()` and that the user’s file exists at the expected location.

                Args:
                    self: Instance containing `user_id` and access to the collection backend.

                Side Effects:
                    Persists chunked documents into the collection for future embedding-based
                    search operations.

                Raises:
                    FileNotFoundError: If the user's `output.txt` does not exist.
                    OSError: If the file cannot be read.
                    Exception: If insertion into the collection fails.

                Returns:
                    None: Results are stored in the collection as a side effect.
            """

        
        base = os.path.dirname(os.path.dirname(__file__))  # project root directory

        path = os.path.join(
            base,
            "uploads",
            str(self.user_id),
            "output.txt"
        )
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        chunk_size = 500
        chunks = []
        for start in range(0, len(text), chunk_size):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)

        col = self.collection()

        if not chunks:
            print("Warning: No chunks created from text! Output.txt may be empty.")
            raise ValueError("No text content found in uploaded file. Please check the file is a valid PDF, DOCX, or TXT.")
        else:
             print(f"Created {len(chunks)} chunks for user {self.user_id}")

        col.add(
            documents=chunks,
            ids=[f"doc_{self.user_id}_{i}" for i in range(len(chunks))],
            metadatas=[{"chunk": i} for i in range(len(chunks))]
        )

    # Retrieved the embeddings for developer use
    @staticmethod
    def getEmbeddings(user_id: int):
        col = chroma.get_or_create_collection(name=f"vectors_{user_id}")
        result = col.get(include=["embeddings"])          # returns ids, embeddings, metadata
        return result.get("embeddings")
    
    # Search the Emddings
    # we are giving dynamic no of chunks retrieval for the retrying system for out rag app
    @staticmethod
    def search(user_id: int, query: str, k: int = 3):
        # I generated this doc string with AI 
        """Retrieve search results for a user.
            Args:
                user_id (int): Unique identifier of the user.
                query (str): Search query used to retrieve matching documents.
                k (int, optional): Number of results to return. Defaults to 3.

            Returns:
                dict: A dictionary with:
                    - "chunks": the documents matching the query (up to k results)
                    - "user_id": the ID passed into the function.
        """
        col = chroma.get_or_create_collection(name=f"vectors_{user_id}")

        res = col.query(
        query_texts=[query],
        n_results=k
        )

        return {"chunks":res["documents"][0],"user_id":user_id}


# Testing Purpost:->
# c = ChromaStore(1)
# c.create_embeddings()

# retrieved = ChromaStore.search(1, "python developer machine learning", 7)
# print(retrieved)