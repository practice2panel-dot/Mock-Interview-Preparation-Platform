# Simple Guide: How to Check Which Model is Used

## 🎯 Easiest Method - Check Browser Console

### Step-by-Step Instructions:

1. **Open your browser** (Chrome/Edge/Firefox)
2. **Open Developer Tools:**
   - Press `F12` OR
   - Right-click → "Inspect" OR
   - Press `Ctrl+Shift+I` (Windows) or `Cmd+Option+I` (Mac)

3. **Click on the "Console" tab"** (it's usually at the top of Developer Tools)

4. **Submit an answer** in Skill Prep (either voice or text)

5. **Look for these messages in the Console:**
   ```
   🤖 Evaluation Model Used: gpt-5.2-thinking
   📊 Model Info: {model: "gpt-5.2-thinking", rubric_used: true, ...}
   ```

That's it! The model name will be clearly displayed.

---

## 📋 Alternative Method - Check Network Tab

### Step-by-Step Instructions:

1. **Open Developer Tools** (`F12`)

2. **Click on the "Network" tab**

3. **Submit an answer** in Skill Prep

4. **Find the request:**
   - Look for `process-voice` (if using voice) OR
   - Look for `evaluate` (if using text)

5. **Click on the request** to open details

6. **Click on the "Response" tab** (or "Preview" tab)

7. **Look for `model_used` field:**
   ```json
   {
     "success": true,
     "evaluation": "...",
     "model_used": "gpt-5.2-thinking",  ← HERE!
     "rubric_used": true,
     "rubric_source": "Rubrics.docx (Relaxed Version)"
   }
   ```

---

## 🔍 Quick Test Endpoint

Open this URL in your browser:
```
http://localhost:5000/api/evaluation-model
```

You'll see:
```json
{
  "success": true,
  "skill_prep_model": "gpt-5.2-thinking",
  "default_model": "gpt-4o-mini",
  "message": "Skill Prep evaluation uses: gpt-5.2-thinking (falls back to gpt-4o-mini if unavailable)"
}
```

---

## 📸 Visual Guide

### Console Method (Easiest):
```
1. Press F12
2. Click "Console" tab
3. Submit answer
4. See: 🤖 Evaluation Model Used: gpt-5.2-thinking
```

### Network Method:
```
1. Press F12
2. Click "Network" tab
3. Submit answer
4. Click on "process-voice" or "evaluate"
5. Click "Response" tab
6. Find "model_used" field
```

---

## ✅ What You Should See

**If GPT-5.2 is working:**
- Console: `🤖 Evaluation Model Used: gpt-5.2-thinking`
- Response: `"model_used": "gpt-5.2-thinking"`

**If fallback is used:**
- Console: `🤖 Evaluation Model Used: gpt-4o-mini`
- Response: `"model_used": "gpt-4o-mini"`

---

## 🆘 Still Can't See It?

1. **Make sure backend is running** (check terminal)
2. **Refresh the page** and try again
3. **Check backend terminal** - it also prints the model name:
   ```
   [EVALUATION] Model used: gpt-5.2-thinking (GPT-5.2 Thinking/Pro)
   ```

---

## 💡 Pro Tip

The **Console method is the easiest** - just press F12, submit an answer, and look for the 🤖 emoji message!

