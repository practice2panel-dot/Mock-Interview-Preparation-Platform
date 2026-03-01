# VAPI Setup Guide for Mock Interview Feature

This guide will help you configure VAPI (Voice AI Platform) for the Mock Interview feature.

## Prerequisites

1. VAPI account with API keys (Public and Private)
2. Backend server running with Flask
3. Frontend React application

## Step 1: Get VAPI API Keys

1. Sign up for a VAPI account at [https://vapi.ai](https://vapi.ai)
2. Navigate to your dashboard
3. Go to API Keys section
4. Copy your **Private API Key** (keep this secure!)

## Step 2: Configure Backend

1. Open the `Backend/.env` file (create it if it doesn't exist)
2. Add your VAPI Private API Key:

```env
VAPI_PRIVATE_KEY=your_vapi_private_key_here
```

**Important:** Never commit your API keys to version control. The `.env` file should be in `.gitignore`.

## Step 2b: Configure Frontend (For Web SDK)

1. Open the `frontend/.env` file (create it if it doesn't exist)
2. Add your VAPI Public API Key:

```env
REACT_APP_VAPI_PUBLIC_KEY=your_vapi_public_key_here
```

**Note:** The application now uses VAPI's Web SDK for browser-based interviews, which **does NOT require a phone number**. This is the recommended approach for web calls.

## Step 3: Install Dependencies

Make sure you have the `requests` library installed:

```bash
cd Backend
pip install -r requirements.txt
```

## Step 4: VAPI API Endpoints

The current implementation uses VAPI's REST API. You may need to adjust the endpoints based on VAPI's actual API structure:

### Current Implementation:
- **Start Call**: `POST https://api.vapi.ai/call`
- **Get Call Status**: `GET https://api.vapi.ai/call/{call_id}`
- **End Call**: `POST https://api.vapi.ai/call/{call_id}/end`

### Note:
VAPI's API structure may vary. Please refer to [VAPI Documentation](https://docs.vapi.ai) for the latest API endpoints and request/response formats.

## Step 5: Adjust Backend Code (if needed)

If VAPI's API structure is different, update the following endpoints in `Backend/app.py`:

1. `/api/mock-interview/start-call` - Adjust the payload structure
2. `/api/mock-interview/call-status/{call_id}` - Adjust response parsing
3. `/api/mock-interview/end-call/{call_id}` - Adjust endpoint URL

## Step 6: Test the Integration

1. Start your backend server:
   ```bash
   cd Backend
   python app.py
   ```

2. Start your frontend:
   ```bash
   cd frontend
   npm start
   ```

3. Navigate to `/mock-interview` in your browser
4. Fill in the form (Name, Job Role, Interview Type)
5. Click "Start Interview"

## Troubleshooting

### Error: "VAPI API key not configured"
- Make sure you've added `VAPI_PRIVATE_KEY` to your `Backend/.env` file
- Restart your backend server after adding the key

### Error: "VAPI Public Key not configured"
- Make sure you've added `REACT_APP_VAPI_PUBLIC_KEY` to your `frontend/.env` file
- Get your Public Key from VAPI dashboard → API Keys
- Restart your frontend after adding the key

### Error: "Failed to start call"
- Check that your VAPI API keys (both Private and Public) are valid
- Verify you're using the correct keys (Private for backend, Public for frontend)
- Check browser console and backend logs for detailed error messages

### Call not connecting
- Verify your VAPI account has sufficient credits
- Check VAPI dashboard for any account restrictions
- Review VAPI API documentation for required parameters

## Alternative: Using VAPI Web SDK

If you prefer to use VAPI's Web SDK directly in the frontend:

1. Install the SDK:
   ```bash
   cd frontend
   npm install @vapi-ai/web
   ```

2. Update `frontend/src/components/MockInterview.js` to use the SDK directly instead of backend API calls

3. Store your VAPI Public Key in `frontend/.env`:
   ```env
   REACT_APP_VAPI_PUBLIC_KEY=your_vapi_public_key_here
   ```

## Features Implemented

✅ Form for job role, interview type, and candidate name
✅ Fetches questions from database for all skills of selected job role
✅ 2-3 questions per skill
✅ VAPI integration for voice conversation
✅ Greeting at interview start
✅ Follow-up questions based on conversation
✅ Interview conclusion
✅ LLM-powered feedback generation
✅ Feedback display after interview

## Next Steps

1. Configure your VAPI account and API keys
2. Test the mock interview flow
3. Adjust VAPI API calls based on actual API structure
4. Customize voice settings (voice provider, voice ID) in `Backend/app.py`
5. Add more job roles and skills as needed

## Support

For VAPI-specific issues, refer to:
- [VAPI Documentation](https://docs.vapi.ai)
- [VAPI Support](https://vapi.ai/support)

For application-specific issues, check the backend logs and browser console.

