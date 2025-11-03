from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_chroma import Chroma
from uuid import uuid4

# import the .env file
from dotenv import load_dotenv
load_dotenv()

# configuration
DATA_PATH = r"data"
CHROMA_PATH = r"chroma_db"

# OpenAI 
#embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")

# Google Gemini 
# embeddings_model = GoogleGenerativeAIEmbeddings(
#     model="models/gemini-embedding-001"
# )

# Option 3: HuggingFace - FREE and open-access (no authentication needed)
embeddings_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
# initiate the vector store
vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings_model,
    persist_directory=CHROMA_PATH,
)

# loading the PDF document
loader = PyPDFDirectoryLoader(DATA_PATH)

raw_documents = loader.load()

# splitting the document
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=100,
    length_function=len,
    is_separator_regex=False,
)

# creating the chunks
chunks = text_splitter.split_documents(raw_documents)

# creating unique ID's
uuids = [str(uuid4()) for _ in range(len(chunks))]

# adding chunks to vector store in batches to avoid exceeding ChromaDB batch size limit
BATCH_SIZE = 5000  # Safe batch size for ChromaDB
total_chunks = len(chunks)

print(f"Total chunks to process: {total_chunks}")

for i in range(0, total_chunks, BATCH_SIZE):
    batch_end = min(i + BATCH_SIZE, total_chunks)
    batch_chunks = chunks[i:batch_end]
    batch_uuids = uuids[i:batch_end]
    
    print(f"Processing batch {i//BATCH_SIZE + 1}: chunks {i+1} to {batch_end}")
    vector_store.add_documents(documents=batch_chunks, ids=batch_uuids)

print(f"Successfully added {total_chunks} chunks to the vector store!")