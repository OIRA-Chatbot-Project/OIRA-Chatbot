#from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
import gradio as gr
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings

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

# Option 3: HuggingFace - FREE and open-access (CURRENTLY USED IN DATABASE)
embeddings_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
# initiate the model
#llm = ChatOpenAI(temperature=0.5, model='gpt-4o-mini')
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# connect to the chromadb
vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings_model,
    persist_directory=CHROMA_PATH, 
)

# Set up the vectorstore to be the retriever
num_results = 5
retriever = vector_store.as_retriever(search_kwargs={'k': num_results})

# call this function for every message added to the chatbot
def stream_response(message, history):
    #print(f"Input: {message}. History: {history}\n")

    # retrieve the relevant chunks based on the question asked
    docs = retriever.invoke(message)

    # add all the chunks to 'knowledge'
    knowledge = ""

    for doc in docs:
        knowledge += doc.page_content+"\n\n"


    # make the call to the LLM (including prompt)
    if message is not None:

        partial_message = ""

        rag_prompt = f"""
        You are an assistant chatbot that helps Bucknell University students find infomation about courses using the school's course catalog.
        While answering, you don't use your internal knowledge, 
        but solely the information in 'data/2025-2026 course catalog.pdf'. 
        If you don't know the answer, just say that you don't know and ask the student to consult faculty and staff.
        You don't mention anything to the user about the provided knowledge.
        Response should be as detailed as possible.

        The question: {message}

        Conversation history: {history}

        The knowledge: {knowledge}

        """

        print(rag_prompt)

        # stream the response to the Gradio App
        for response in llm.stream(rag_prompt):
            partial_message += response.content
            yield partial_message

# initiate the Gradio app
chatbot = gr.ChatInterface(stream_response, textbox=gr.Textbox(placeholder="Send to the LLM...",
    container=False,
    autoscroll=True,
    scale=7),
)

# launch the Gradio app
chatbot.launch(share=True)