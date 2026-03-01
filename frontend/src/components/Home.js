import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  Brain, 
  BookOpen, 
  BarChart3, 
  Target, 
  MessageSquare,
  ArrowRight,
  CheckCircle
} from 'lucide-react';
import './Home.css';

const Home = () => {
  const { authenticated } = useAuth();
  const navigate = useNavigate();

  const handleClick = (e) => {
    if (!authenticated) {
      e.preventDefault();
      navigate('/signup');
    }
  };

  const features = [
    {
      icon: <BookOpen size={48} strokeWidth={1.5} />,
      title: 'Skill Preparation',
      description: 'Structured learning paths and practice questions tailored to your role.',
      color: '#2E86AB'
    },
    {
      icon: <Target size={48} strokeWidth={1.5} />,
      title: 'Mock Interviews',
      description: 'Simulate real interview flows with role-based questions and instant feedback.',
      color: '#2E86AB'
    },
    {
      icon: <MessageSquare size={48} strokeWidth={1.5} />,
      title: 'Detailed Feedback',
      description: 'Get clear, actionable feedback after every attempt to improve faster.',
      color: '#2E86AB'
    },
    {
      icon: <BarChart3 size={48} strokeWidth={1.5} />,
      title: 'Progress Tracking',
      description: 'Track performance across skills, interview types, and difficulty levels.',
      color: '#2E86AB'
    }
  ];

  const jobRoles = [
    {
      title: 'AI Engineer',
      skills: ['Machine Learning', 'Python', 'TensorFlow', 'PyTorch', 'Deep Learning'],
      color: '#0A2540'
    },
    {
      title: 'Data Scientist',
      skills: ['Python', 'Machine Learning', 'SQL', 'Data Analysis', 'Statistics'],
      color: '#1B4F72'
    },
    {
      title: 'Python Developer',
      skills: ['Python', 'AWS', 'Kubernetes', 'Docker', 'Lambda'],
      color: '#2E86AB'
    }
  ];

  return (
    <div className="home">
      {/* Hero Section */}
      <section className="hero">
        <div className="container">
          <div className="hero-content">
            <div className="hero-text">
              <h1 className="hero-title">
                Master Your Interview Skills with{' '}
                <span className="highlight">Practice2Panel</span>
              </h1>
              <p className="hero-description">
                The ultimate platform for skill practice and interview preparation. 
                Prepare smarter, perform better, and land your dream job.
              </p>
              <div className="hero-actions">
                {authenticated ? (
                  <>
                    <Link to="/skill-prep" className="btn btn-primary btn-large">
                      Start Learning
                      <ArrowRight size={20} />
                    </Link>
                  </>
                ) : (
                  <>
                    <button onClick={handleClick} className="btn btn-primary btn-large">
                      Get Started
                      <ArrowRight size={20} />
                    </button>
                  </>
                )}
              </div>
            </div>
            <div className="hero-visual">
              <div className="hero-visual-elements">
                <div className="hero-circle hero-circle-1"></div>
                <div className="hero-circle hero-circle-2"></div>
                <div className="hero-icon">
                  <Brain size={120} strokeWidth={1.5} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features">
        <div className="container">
          <h2 className="section-title">Why Choose Practice2Panel?</h2>
          <p className="section-subtitle">
            Role-based learning, mock interviews, and a structured question bank—everything in Practice2Panel is built for real interview preparation.
          </p>
          <div className="features-grid">
            {features.map((feature, index) => (
              <div key={index} className="feature-card animate-fade-in-up" style={{ animationDelay: `${index * 0.1}s` }}>
                <div className="feature-icon" style={{ color: feature.color }}>
                  {feature.icon}
                </div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Job Roles Section */}
      <section className="job-roles">
        <div className="container">
          <h2 className="section-title">Choose Your Job Role</h2>
          <p className="section-subtitle">
            Choose your job role and get personalized learning paths and interview questions.
          </p>
          <div className="roles-grid">
            {jobRoles.map((role, index) => (
              <div key={index} className="role-card">
                <div className="role-header" style={{ backgroundColor: role.color }}>
                  <h3>{role.title}</h3>
                </div>
                <div className="role-content">
                  <h4>Key Skills:</h4>
                  <ul className="skills-list">
                    {role.skills.map((skill, skillIndex) => (
                      <li key={skillIndex}>
                        <CheckCircle size={16} strokeWidth={2} />
                        {skill}
                      </li>
                    ))}
                  </ul>
                  {authenticated ? (
                    <Link to="/skill-prep" className="btn btn-primary">
                      Start Learning
                    </Link>
                  ) : (
                    <button onClick={handleClick} className="btn btn-primary">
                      Sign Up to Start
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="container">
          <div className="cta-content">
            <h2>Ready to Ace Your Next Interview?</h2>
            <p>Join thousands of successful candidates who've transformed their interview skills with Practice2Panel.</p>
            <div className="cta-actions">
              {authenticated ? (
                <Link to="/skill-prep" className="btn btn-primary btn-large">
                  Get Started Free
                </Link>
              ) : (
                <button onClick={handleClick} className="btn btn-primary btn-large">
                  Get Started Free
                </button>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
