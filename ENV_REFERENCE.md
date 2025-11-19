# Environment Variables Quick Reference

## Frontend (.env.local)

```env
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
CLERK_SECRET_KEY=sk_test_xxxxx

# Clerk Routes (usually keep as default)
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Backend (.env)

```env
# OpenAI
OPENAI_API_KEY=sk-xxxxx
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.5
EMBEDDING_MODEL=text-embedding-3-large

# Clerk Authentication
CLERK_SECRET_KEY=sk_test_xxxxx
CLERK_PUBLISHABLE_KEY=pk_test_xxxxx

# Database
DATABASE_URL=sqlite:///./chatbot.db

# Vector Store
CHROMA_PATH=chroma_db
CHROMA_COLLECTION_NAME=example_collection
DATA_PATH=data

# RAG Configuration
NUM_RETRIEVAL_RESULTS=5
CHUNK_SIZE=300
CHUNK_OVERLAP=100

# API Configuration (optional, see config.py)
API_TITLE=Bucknell Course Catalog Chatbot API
API_DESCRIPTION=RAG-based chatbot for course information
API_VERSION=1.0.0
```

## Where to Get Keys

### Clerk Keys
1. Go to https://dashboard.clerk.com
2. Select your application
3. Go to "API Keys" in the sidebar
4. Copy both Publishable Key and Secret Key

### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy and save it (you can't see it again)

## Security Notes

- ⚠️ **Never commit .env or .env.local files to git**
- ⚠️ **Keep your Secret Keys private**
- ⚠️ **Publishable Keys are safe to expose in frontend code**
- ⚠️ **Use different keys for development and production**
- ⚠️ **Rotate keys if compromised**
