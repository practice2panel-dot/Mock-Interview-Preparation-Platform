# 🎯 Practice2Panel - AI Powered Interview Preparation Platform

A comprehensive full-stack application for AI-powered interview preparation featuring skill-based practice questions and mock interviews. Built with React frontend and Flask backend, Practice2Panel provides structured interview prep with optional voice responses.

## 🌟 Key Features

### 🧠 Skill Preparation Module
- **Multi-Role Support**: AI Engineer, Data Scientist, Python Developer
- **Skill-Based Learning**: Python, Machine Learning, Deep Learning, SQL, Data Analysis
- **Interactive MCQs**: Easy, Medium, Hard difficulty levels
- **Real-time Feedback**: Instant explanations for correct/incorrect answers
- **Progress Tracking**: Monitor scores and accuracy per skill

### 🎤 Mock Interviews
- **Role + Type Based**: Choose job role and interview type
- **Interactive Flow**: Follow-up questions and structured feedback
- **Voice-Friendly**: Works with browser speech input where supported

### 📊 Dashboard & Analytics
- **Progress Overview**: Visual representation of learning journey
- **Performance Metrics**: Detailed analytics and insights
- **Achievement System**: Badges and milestones
- **Activity Tracking**: Recent quizzes and interviews
- **Skill Development**: Individual skill progress monitoring

## 🏗️ Architecture

### Frontend (React)
- **Framework**: React 18 with modern hooks
- **Styling**: CSS3 with CSS Variables and Flexbox/Grid
- **Icons**: Lucide React for consistent UI
- **Routing**: React Router DOM for navigation
- **Responsive**: Mobile-first design approach

### Backend (Flask)
- **API**: RESTful Flask API with CORS support
- **Database**: PostgreSQL with dynamic table management
- **Voice Processing**: Whisper for speech-to-text transcription

## 🚀 Quick Start

### Option 1: One-Click Startup (Recommended)

**Windows:**
```bash
start_project.bat
```

**Mac/Linux:**
```bash
./start_project.sh
```

### Option 2: Manual Setup

**1. Backend Setup:**
```bash
cd Backend
pip install -r requirements.txt
python start_server.py  # Start the Flask server
```

**2. Frontend Setup:**
```bash
cd frontend
npm install
npm start
```

### Option 3: Using npm scripts
```bash
cd frontend
npm install
npm run setup-backend
npm run dev  # Starts both backend and frontend
```

## 📁 Project Structure

```
Interview_Project/
├── Backend/                           # Flask API Server
│   ├── app.py                        # Main Flask application
│   ├── db_handler.py                 # Database connection utilities
│   ├── voice_processor.py            # Voice processing utilities
│   ├── start_server.py               # Server startup script
│   ├── requirements.txt              # Python dependencies
│   ├── *.json                        # Question databases (JSON format)
│   ├── pdfs/                         # Source PDF files
│   └── pdfsExtracted/                # Extracted PDF content
├── frontend/                          # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.js             # Navigation component
│   │   │   ├── Home.js               # Landing page
│   │   │   ├── SkillPrep.js          # MCQ skill preparation
│   │   │   ├── Interview.js          # AI interview module
│   │   │   ├── Dashboard.js          # Progress tracking
│   │   │   └── WelcomeScreen.js      # Welcome interface
│   │   ├── App.js                    # Main app component
│   │   ├── index.js                  # Entry point
│   │   └── config.js                 # Configuration
│   ├── package.json                  # Node.js dependencies
│   └── public/                       # Static assets
├── start_project.bat                 # Windows startup script
├── start_project.sh                  # Unix startup script
└── README.md                         # This file
```

## 🛠️ Tech Stack

### Frontend
- **React 18** - Modern UI framework with hooks
- **React Router DOM** - Client-side routing
- **Lucide React** - Beautiful icon library
- **Framer Motion** - Smooth animations and transitions
- **CSS3** - Modern styling with CSS variables and Grid/Flexbox
- **Web Speech API** - Text-to-speech for question narration
- **MediaRecorder API** - Voice recording capabilities

### Backend
- **Flask 2.3.3** - Python web framework
- **Flask-CORS 4.0.0** - Cross-origin resource sharing
- **PostgreSQL** - Primary database with psycopg2-binary
- **Whisper 1.1.10** - OpenAI's speech-to-text model (base model)
- **python-dotenv 1.0.0** - Environment variable management
- **pyttsx3 2.90** - Text-to-speech synthesis
- **pydub 0.25.1** - Audio processing

## 🗄️ Database Schema

The system uses PostgreSQL with dynamic table naming:
- **Table Format**: `{interview_type}_{skill}`
- **Examples**: 
  - `technical_python` - Technical Python questions
  - `behavioral_machine_learning` - Behavioral ML questions
  - `problem_solving_sql` - SQL problem-solving questions
- **Special Table**: `behavioralquestions` - General behavioral questions

### Table Structure
```sql
CREATE TABLE {interview_type}_{skill} (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    explanation TEXT
);
```

## 📚 Question Databases

The platform includes comprehensive question databases in JSON format:

### Technical Skills Coverage
- **Python**: 200+ questions covering syntax, frameworks, and best practices
- **Machine Learning**: Algorithms, preprocessing, model evaluation
- **Deep Learning**: Neural networks, TensorFlow, PyTorch
- **Data Analysis**: Statistics, visualization, data manipulation
- **SQL**: Database design, query optimization, performance
- **Behavioral Questions**: Leadership, teamwork, problem-solving

### Question Types
- **Multiple Choice**: Interactive quizzes with instant feedback
- **Open-ended**: Detailed responses for practice
- **Scenario-based**: Real-world problem-solving situations
- **Code Review**: Technical code analysis and improvement

### Difficulty Levels
- **Easy**: Basic concepts and definitions
- **Medium**: Practical applications and intermediate concepts
- **Hard**: Advanced topics and complex problem-solving

## 🌐 API Endpoints

### Core Endpoints
- `GET /api/health` - Health check
- `GET /api/questions/{interview_type}/{skill}` - Fetch questions
- `POST /api/process-voice` - Process voice recordings

### Response Format
```json
{
  "success": true,
  "message": "Found 5 questions",
  "questions": ["Question 1", "Question 2", ...]
}
```

## ⚙️ Environment Configuration

Create a `.env` file in the `Backend` directory:

```env
# Database Configuration
PGDATABASE=your_database_name
PGUSER=your_username
PGPASSWORD=your_password
PGHOST=localhost
PGPORT=5432

# Flask Configuration
PORT=5000
FLASK_DEBUG=True

# Voice Processing Configuration
WHISPER_MODEL=base  # OpenAI Whisper model (tiny, base, small, medium, large)
```

## 🎯 Usage Guide

### Skill Preparation
1. Navigate to "Skill Prep" from the main menu
2. Select your job role (AI Engineer, Data Scientist, or Python Developer)
3. Choose a specific skill to practice
4. Select difficulty level (Easy, Medium, or Hard)
5. Answer MCQs and receive instant feedback
6. Track your progress and scores

### Mock Interview Practice
1. Navigate to "Mock Interview" from the main menu
2. Enter your name, choose job role, and select interview type
3. Answer questions (voice or text) and receive instant feedback
4. Complete the session to get a summary report

### Dashboard
1. Access "Dashboard" to view your progress
2. Monitor overall statistics and trends
3. Track skill development over time
4. View achievements and badges
5. Analyze performance metrics

## 🔧 Prerequisites

- **Python 3.7+** with pip
- **Node.js 14+** with npm
- **PostgreSQL** database
- **Git** (for cloning)

## 🚀 Development

### Adding New Questions
1. Add questions to the appropriate database table
2. Table name should follow: `{interview_type}_{skill}`
3. Questions will automatically appear in the frontend

### Adding New Skills
1. Update the `jobRoles` object in `SkillPrep.js`
2. Create corresponding database tables
3. Add questions to the new tables

### Customization
The app uses CSS variables for easy theming. Modify the `:root` section in `src/index.css`:

```css
:root {
  --primary-color: #6366f1;
  --accent-color: #10b981;
  --secondary-color: #f59e0b;
  /* Add more custom colors */
}
```

## 🔍 Troubleshooting

### Backend Issues
- Ensure PostgreSQL is running
- Check database credentials in `.env` file
- Verify Python dependencies are installed

### Frontend Issues
- Ensure Node.js and npm are installed
- Check if backend is running on port 5000
- Clear browser cache if needed
- Verify all dependencies are installed

### Database Issues
- Check table naming convention: `{interview_type}_{skill}`
- Verify database connection settings

## 📈 Performance Features

- **Responsive Design**: Works seamlessly on all devices
- **Smooth Animations**: Subtle transitions and hover effects
- **Color-coded System**: Visual hierarchy with consistent theming
- **Accessibility**: High contrast and readable typography
- **Interactive Elements**: Engaging user experience

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Verify all prerequisites are installed
3. Check the console for error messages
4. Ensure both backend and frontend are running
5. Verify database configurations

## 🙏 Acknowledgments

- **React Team** for the amazing framework
- **PostgreSQL** for robust database management
- **Flask** for lightweight Python web framework
- **Lucide** for beautiful, consistent icons

---

**Built with ❤️ for the future of interview preparation**

*Transform your interview skills with Practice2Panel - the ultimate AI-powered practice platform!*