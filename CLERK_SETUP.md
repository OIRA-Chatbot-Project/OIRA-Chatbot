# Clerk Authentication Setup Guide

This guide will help you integrate Google login using Clerk in your chatbot application.

## Prerequisites

- Node.js installed
- Python 3.8+ installed
- A Clerk account (sign up at https://clerk.com)

## Step 1: Create a Clerk Application

1. Go to https://dashboard.clerk.com
2. Click "Create Application"
3. Name your application (e.g., "Bucknell Chatbot")
4. Enable "Google" as an authentication provider
5. Enable "Email" as an authentication provider
6. Click "Create Application"

## Step 2: Get Your Clerk Keys

After creating your application, you'll see your API keys on the dashboard:

1. Copy the **Publishable Key** (starts with `pk_test_` or `pk_live_`)
2. Copy the **Secret Key** (starts with `sk_test_` or `sk_live_`)

## Step 3: Configure Frontend Environment Variables

1. Open `frontend/.env.local`
2. Replace the placeholder values with your actual Clerk keys:

```env
# Clerk Configuration
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_actual_key_here
CLERK_SECRET_KEY=sk_test_your_actual_secret_key_here

# Clerk Sign-in/Sign-up URLs (keep these as is)
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Step 4: Configure Backend Environment Variables

1. Create or update `backend/.env` file:

```env
# Clerk Configuration (for JWT verification)
CLERK_SECRET_KEY=sk_test_your_actual_secret_key_here
CLERK_PUBLISHABLE_KEY=pk_test_your_actual_key_here

# Database
DATABASE_URL=sqlite:///./chatbot.db

# OpenAI (existing)
OPENAI_API_KEY=your_openai_api_key_here
```

## Step 5: Install Dependencies

### Frontend:
```bash
cd frontend
npm install
```

### Backend:
```bash
cd backend
pip install -r requirements.txt
```

## Step 6: Run Database Migration

Since we added new User table and relationships, you need to:

1. **IMPORTANT**: Back up your existing database if it has data:
   ```bash
   cp backend/chatbot.db backend/chatbot.db.backup
   ```

2. Delete the old database to recreate with new schema:
   ```bash
   rm backend/chatbot.db
   ```

3. The database will be automatically recreated when you start the backend server.

## Step 7: Start the Application

### Start Backend:
```bash
cd backend
source .venv/Scripts/activate  # On Windows: .venv\Scripts\activate
uvicorn main:app --reload
```

### Start Frontend (in a new terminal):
```bash
cd frontend
npm run dev
```

## Step 8: Configure Email Verification Method

To use email code verification as the primary method:

1. Go to your Clerk Dashboard: https://dashboard.clerk.com
2. Select your application
3. Navigate to **User & Authentication** → **Email, Phone, Username**
4. Under **Email address**:
   - Enable "Email address" if not already enabled
   - Click on **Verification methods**
   - Select **Email verification code** as the verification method
   - Make sure it's set as the primary/first option
5. Navigate to **User & Authentication** → **Social Connections**
6. Ensure **Google** is enabled for OAuth sign-in
7. Save your changes

This configuration will:
- Send a verification code to the user's email when signing up
- Use the email code for email/password authentication
- Still allow Google OAuth as an alternative sign-in method

## Step 9: Test the Application

1. Open your browser to `http://localhost:3000`
2. You should be redirected to the Clerk sign-in page
3. **To sign in with email:**
   - Enter your email address
   - Click "Continue"
   - Enter the verification code sent to your email
4. **To sign in with Google:**
   - Click "Continue with Google"
   - Sign in with your Google account
5. You'll be redirected back to the chatbot
6. Start chatting!

## How It Works

### Authentication Flow:

1. **User signs in** → Clerk handles Google OAuth
2. **Frontend receives JWT token** → Clerk session token
3. **Frontend sends API requests** → Includes token in Authorization header
4. **Backend verifies token** → Validates JWT and extracts user info
5. **Backend creates/retrieves user** → Stores user in SQLite database
6. **Chat sessions are user-scoped** → Each user sees only their own chat history

### Key Features:

- ✅ Google OAuth sign-in
- ✅ User data stored in SQLite
- ✅ Private chat history per user
- ✅ Secure JWT authentication
- ✅ User profile and sign-out in sidebar

## Troubleshooting

### Issue: "Cannot find module '@clerk/nextjs'"
**Solution**: Run `npm install` in the frontend directory

### Issue: "User not found. Please sign up first."
**Solution**: Make sure you've created the user by visiting the /users endpoint. This should happen automatically on first sign-in.

### Issue: "Invalid token"
**Solution**: 
- Check that your CLERK_SECRET_KEY is correct in backend/.env
- Make sure both frontend and backend are using the same Clerk application keys

### Issue: "Session does not belong to user"
**Solution**: Clear your browser's localStorage and cookies, then sign in again

### Issue: Database errors after migration
**Solution**: If you have existing data, you may need to write a migration script. For fresh start, delete chatbot.db and let it recreate.

## Development vs Production

### Development (current setup):
- Uses `pk_test_` and `sk_test_` keys
- Token verification is simplified for faster development
- CORS allows localhost

### Production (when deploying):
- Use `pk_live_` and `sk_live_` keys from Clerk
- Enable full JWT verification with JWKS
- Update CORS settings in `backend/config.py`
- Set proper domain in Clerk dashboard

## Next Steps

1. Customize the Clerk sign-in appearance in the Clerk dashboard
2. Add more OAuth providers (GitHub, Microsoft, etc.)
3. Implement user profile page
4. Add user settings and preferences
5. Deploy to production

## Support

- Clerk Documentation: https://clerk.com/docs
- Clerk Discord: https://clerk.com/discord
- GitHub Issues: Report bugs in the repository
