import React from 'react';
import { BarChart3, Target, Clock, BookOpen, Video } from 'lucide-react';
import './Dashboard.css';

const Dashboard = () => {
  return (
    <div className="dashboard-shell">
      <div className="dashboard-page">
        <div className="dashboard-header">
          <div>
            <h1 className="dashboard-title">Dashboard</h1>
            <p className="dashboard-subtitle">Static overview of Skill Prep and Mock Interview.</p>
          </div>
        </div>

        <div className="dashboard-section">
          <div className="section-title">Skill Preparation</div>
          <div className="dashboard-grid">
            <div className="dashboard-card">
              <div className="card-header">
                <BookOpen size={18} />
                <span>Summary</span>
              </div>
              <div className="card-body">
                <div className="stat-row">
                  <span>Total Questions</span>
                  <strong>0</strong>
                </div>
                <div className="stat-row">
                  <span>Total Time</span>
                  <strong>0m</strong>
                </div>
              </div>
            </div>

            <div className="dashboard-card">
              <div className="card-header">
                <Target size={18} />
                <span>Interview Type + Skill</span>
              </div>
              <div className="card-body">
                <div className="badge-list">
                  <span className="chip">Technical • Python: 0</span>
                  <span className="chip">Conceptual • ML: 0</span>
                  <span className="chip">Behavioral • General: 0</span>
                </div>
              </div>
            </div>
          </div>

          <div className="dashboard-card wide">
            <div className="card-header">
              <BarChart3 size={18} />
              <span>Resume Skill Prep</span>
            </div>
            <div className="card-body">
              <p className="card-muted">Last question: Q0 of 0</p>
              <p className="card-muted">Skill: — | Interview Type: —</p>
            </div>
          </div>

          <div className="dashboard-card wide">
            <div className="card-header">
              <Clock size={18} />
              <span>Recent Questions</span>
            </div>
            <div className="card-body">
              <p className="card-muted">No recent questions yet.</p>
            </div>
          </div>
        </div>

        <div className="dashboard-section">
          <div className="section-title">Mock Interviews</div>
          <div className="dashboard-grid">
            <div className="dashboard-card">
              <div className="card-header">
                <Video size={18} />
                <span>Summary</span>
              </div>
              <div className="card-body">
                <div className="stat-row">
                  <span>Total Interviews</span>
                  <strong>0</strong>
                </div>
                <div className="stat-row">
                  <span>Total Time</span>
                  <strong>0m</strong>
                </div>
              </div>
            </div>

            <div className="dashboard-card">
              <div className="card-header">
                <Target size={18} />
                <span>Interview Types</span>
              </div>
              <div className="card-body">
                <div className="badge-list">
                  <span className="chip">Technical: 0</span>
                  <span className="chip">Conceptual: 0</span>
                  <span className="chip">Behavioral: 0</span>
                </div>
              </div>
            </div>
          </div>

          <div className="dashboard-card wide">
            <div className="card-header">
              <BarChart3 size={18} />
              <span>Mock Interview History</span>
            </div>
            <div className="card-body">
              <p className="card-muted">No mock interviews yet.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
