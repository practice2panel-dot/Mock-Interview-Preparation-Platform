import React from 'react';

const SummaryScreen = ({ summaryData, onRestart }) => {
  const renderImprovementList = (text) => {
    if (!text) return null;
    const lines = text
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);

    if (lines.length === 0) {
      return null;
    }

    return (
      <ul style={{ paddingLeft: '20px', margin: '10px 0', lineHeight: 1.6 }}>
        {lines.map((line, index) => {
          const cleanedLine = line.replace(/^[-\u2022\d\.\s]*/, '');
          const html = cleanedLine
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/:\s*/g, ': ');

          return (
            <li
              key={`${cleanedLine}-${index}`}
              style={{ marginBottom: '6px' }}
              dangerouslySetInnerHTML={{ __html: html }}
            />
          );
        })}
      </ul>
    );
  };

  return (
    <div>
      <h1>Interview Summary</h1>
      
      <div className="summary-section">
        <h3>Interview Details</h3>
        <p><strong>Candidate Name:</strong> {summaryData.name}</p>
        <p><strong>Job Role:</strong> {summaryData.job_role}</p>
        <p><strong>Interview Type:</strong> {summaryData.interview_type}</p>
      </div>

      {summaryData.closing_message && (
        <div className="summary-section">
          <div className="feedback-card" style={{ padding: '20px', marginBottom: '20px' }}>
            <p className="feedback-text" style={{ fontSize: '1.1em', lineHeight: '1.6' }}>
              {summaryData.closing_message}
            </p>
          </div>
        </div>
      )}

      {summaryData.overall_scores && (
        <div className="summary-section">
          <h3>Overall Performance Scores</h3>
          <div className="score-grid">
            {Object.entries(summaryData.overall_scores).map(([metric, score]) => (
              <div key={metric} className="score-card">
                <h4>{metric}</h4>
                <div className="score-value" style={{ fontSize: '1.2em', fontWeight: 'bold', marginTop: '10px' }}>
                  {score}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {summaryData.areas_of_improvement && (
        <div className="summary-section">
          <h3>Areas of Improvement</h3>
          
          {summaryData.areas_of_improvement.Communication && (
            <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '4px' }}>
              <h4 style={{ marginTop: '0', color: '#333' }}>Communication</h4>
              {renderImprovementList(summaryData.areas_of_improvement.Communication)}
            </div>
          )}

          {summaryData.areas_of_improvement['Knowledge Accuracy'] && (
            <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '4px' }}>
              <h4 style={{ marginTop: '0', color: '#333' }}>Knowledge Accuracy</h4>
              {renderImprovementList(summaryData.areas_of_improvement['Knowledge Accuracy'])}
            </div>
          )}

          {summaryData.areas_of_improvement.Clarity && (
            <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '4px' }}>
              <h4 style={{ marginTop: '0', color: '#333' }}>Clarity</h4>
              {renderImprovementList(summaryData.areas_of_improvement.Clarity)}
            </div>
          )}
        </div>
      )}

      <div className="button-group" style={{ marginTop: '30px' }}>
        <button 
          type="button" 
          className="primary-button"
          onClick={onRestart}
        >
          Start New Interview
        </button>
      </div>
    </div>
  );
};

export default SummaryScreen;

