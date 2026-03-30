import React, { useMemo, useState } from 'react';
import axios from 'axios';
import { jobRoles } from '../../jobRolesConfig';

const InterviewForm = ({ onStartInterview, apiBaseUrl }) => {
  const jobRoleOptions = useMemo(() => Object.keys(jobRoles), []);
  const [formData, setFormData] = useState({
    name: '',
    job_role: jobRoleOptions[0] || 'AI Engineer',
    interview_type: 'Conceptual'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      setError('Please enter your name');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${apiBaseUrl}/api/mock-interview/start`, formData);
      onStartInterview(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to start interview. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Welcome to Mock Interview </h1>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="name">Candidate Name *</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="Enter your name"
            required
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="job_role">Job Role *</label>
          <select
            id="job_role"
            name="job_role"
            value={formData.job_role}
            onChange={handleChange}
            required
            disabled={loading}
          >
            {jobRoleOptions.map((role) => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="interview_type">Interview Type *</label>
          <select
            id="interview_type"
            name="interview_type"
            value={formData.interview_type}
            onChange={handleChange}
            required
            disabled={loading}
          >
            <option value="Conceptual">Conceptual</option>
            <option value="Behavioral">Behavioral</option>
            <option value="Technical">Technical</option>
          </select>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="button-group">
          <button 
            type="submit" 
            className="primary-button"
            disabled={loading}
          >
            {loading ? 'Starting Interview...' : 'Start Interview'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default InterviewForm;

