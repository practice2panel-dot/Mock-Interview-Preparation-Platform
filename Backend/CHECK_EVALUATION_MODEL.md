# How to Check Which Model is Used for Evaluation

This guide explains multiple ways to verify which AI model is being used for Skill Prep evaluation.

## Method 1: Check API Response (Recommended)

The evaluation API response now includes the `model_used` field. After submitting an answer for evaluation, check the response:

**API Endpoint:** `POST /api/evaluate`

**Response includes:**
```json
{
  "success": true,
  "evaluation": "{...feedback JSON...}",
  "rubric_used": true,
  "rubric_source": "Rubrics.docx (Relaxed Version)",
  "model_used": "gpt-5.2-thinking"  // ← Model name here
}
```

### How to Check:
1. Open browser Developer Tools (F12)
2. Go to Network tab
3. Submit an answer in Skill Prep
4. Find the `/api/evaluate` request
5. Check the Response - look for `model_used` field

## Method 2: Check Backend Console/Logs

The backend server prints the model name to the console when evaluation runs:

**Look for these messages in the backend terminal:**
```
[EVALUATION] Model used: gpt-5.2-thinking (GPT-5.2 Thinking/Pro)
```

Or if fallback is used:
```
[EVALUATION] ⚠️ GPT-5.2 not available, using fallback: gpt-4o-mini
[EVALUATION] Model used: gpt-4o-mini (Fallback)
```

## Method 3: Check Model Configuration Endpoint

A new endpoint shows the configured models:

**API Endpoint:** `GET http://localhost:5000/api/evaluation-model`

**Response:**
```json
{
  "success": true,
  "skill_prep_model": "gpt-5.2-thinking",
  "default_model": "gpt-4o-mini",
  "message": "Skill Prep evaluation uses: gpt-5.2-thinking (falls back to gpt-4o-mini if unavailable)"
}
```

### How to Check:
1. Open browser and go to: `http://localhost:5000/api/evaluation-model`
2. Or use curl: `curl http://localhost:5000/api/evaluation-model`
3. Or use Postman/Insomnia to make a GET request

## Method 4: Check Environment Variables

Check the `.env` file in the Backend directory:

```env
# Skill Prep Evaluation Model
SKILL_PREP_MODEL=gpt-5.2-thinking

# Default model (fallback)
OPENAI_MODEL=gpt-4o-mini
```

If `SKILL_PREP_MODEL` is not set, it defaults to `gpt-5.2-thinking`.

## Method 5: Check Backend Logs File

If logging is configured to write to a file, check the log file for entries like:

```
INFO: ✅ Using GPT-5.2 model (gpt-5.2-thinking) for Skill Prep evaluation
```

or

```
WARNING: ⚠️ GPT-5.2 model (gpt-5.2-thinking) not available, falling back to gpt-4o-mini
```

## Quick Test

To quickly test which model is being used:

1. **Start the backend server**
2. **Open browser console** (F12)
3. **Submit an answer** in Skill Prep
4. **Check Network tab** → Find `/api/evaluate` → View Response
5. **Look for `model_used`** field in the JSON response

## Expected Models

- **Primary:** `gpt-5.2-thinking` (GPT-5.2 Thinking/Pro)
- **Fallback:** `gpt-4o-mini` (if GPT-5.2 is unavailable)

## Troubleshooting

If you see the fallback model being used:
1. Check if `SKILL_PREP_MODEL` is set correctly in `.env`
2. Verify your OpenAI API key has access to GPT-5.2
3. Check backend console for error messages
4. The system will automatically fallback if GPT-5.2 is not available

## Notes

- The model name is now included in every evaluation response
- Console output shows model usage in real-time
- The `/api/evaluation-model` endpoint shows configuration without running an evaluation

