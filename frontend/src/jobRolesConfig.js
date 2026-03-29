/**
 * Job roles and skills — keep in sync with Backend PLATFORM_SKILLS (app.py).
 * Table names: {interviewType}_{skill lowercased with spaces removed}, e.g. technical_python.
 */
const JOB_ROLES_BASE = {
  'AI Engineer': {
    skills: ['Machine Learning', 'Python', 'TensorFlow', 'PyTorch', 'Deep Learning'],
    color: 'var(--primary-color)',
    homeColor: '#0A2540'
  },
  'Data Scientist': {
    skills: ['Python', 'Machine Learning', 'SQL', 'Data Analysis', 'Statistics'],
    color: 'var(--accent-color)',
    homeColor: '#1B4F72'
  },
  'Python Developer': {
    skills: ['Python', 'AWS', 'Kubernetes', 'Docker', 'Lambda'],
    color: 'var(--secondary-color)',
    homeColor: '#2E86AB'
  },
  'Machine Learning Engineer': {
    skills: ['Python', 'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch'],
    color: '#0d9488',
    homeColor: '#0f766e'
  },
  'MLOps Engineer': {
    skills: ['AWS', 'Docker', 'Kubernetes', 'Machine Learning', 'Python'],
    color: '#7c3aed',
    homeColor: '#6d28d9'
  },
  'Data Engineer': {
    skills: ['Python', 'SQL', 'AWS', 'Lambda', 'Docker'],
    color: '#ea580c',
    homeColor: '#c2410c'
  },
  'Deep Learning Engineer': {
    skills: ['Python', 'Deep Learning', 'TensorFlow', 'PyTorch', 'AWS'],
    color: '#db2777',
    homeColor: '#be185d'
  },
  'Cloud AI Engineer': {
    skills: ['AWS', 'Lambda', 'Machine Learning', 'Docker', 'Python'],
    color: '#2563eb',
    homeColor: '#1d4ed8'
  },
  'Backend Engineer (AI/ML Focused)': {
    skills: ['Python', 'SQL', 'AWS', 'Docker', 'Machine Learning'],
    color: '#4f46e5',
    homeColor: '#4338ca'
  }
};

/** For MockInterview, SkillPrep, InterviewPrep: { role: { skills, color } } */
export const jobRoles = Object.fromEntries(
  Object.entries(JOB_ROLES_BASE).map(([key, v]) => [key, { skills: v.skills, color: v.color }])
);

/** For Home.js hero cards */
export const jobRolesForHome = Object.entries(JOB_ROLES_BASE).map(([title, v]) => ({
  title,
  skills: v.skills,
  color: v.homeColor
}));
