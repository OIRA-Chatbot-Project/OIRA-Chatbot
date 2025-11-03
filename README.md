# OIRA-Chatbot
Course Catalog Chatbot for Bucknell University

how to run this:

## 1. move to the ```/backend``` folder

```cd backend```

## 2. create a ```.env``` file to store your API key

```OPENAI_API_KEY=your actual api key here```

## 3. create a virtual environment: 

```python -m venv .venv ```

## 4. activate the virtual environment: (look up the command for your specific OS) 

## 5. run these: 

```pip install -r requirements.txt ```

```python ingest_database.py ```

```python chatbot.py```
