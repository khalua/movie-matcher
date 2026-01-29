import React, { useState } from 'react';
import client from '../api/client';
import { useCircle } from '../contexts/CircleContext';
import PackSelector from './PackSelector';
import './CreateCircleFlow.css';

const CreateCircleFlow = ({ onComplete }) => {
  const { circles, setCircles, switchCircle } = useCircle();
  const [step, setStep] = useState('create'); // 'create' | 'packs' | 'invite'
  const [circleName, setCircleName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [createdCircle, setCreatedCircle] = useState(null);
  const [inviteMessage, setInviteMessage] = useState('');
  const [copied, setCopied] = useState(false);
  const [packsAdded, setPacksAdded] = useState(0);

  const handleCreateCircle = async (e) => {
    e.preventDefault();
    if (!circleName.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await client.post('/api/circles', { name: circleName });
      const newCircle = response.data;

      // Update circles list and switch to the new circle
      setCircles([...circles, newCircle]);
      localStorage.setItem('currentCircleId', newCircle.id);
      switchCircle(newCircle);

      setCreatedCircle(newCircle);
      setStep('packs');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create circle');
    } finally {
      setLoading(false);
    }
  };

  const handlePackAdded = (data) => {
    setPacksAdded(prev => prev + (data.added_count || 0));
  };

  const handlePacksDone = async () => {
    // Generate invitation code for the next step
    setLoading(true);
    try {
      const response = await client.post(`/api/circles/${createdCircle.id}/invitations`);
      setInviteMessage(response.data.email_body);
      setStep('invite');
    } catch (err) {
      // If invitation generation fails, still proceed but without the message
      console.error('Error generating invitation:', err);
      setStep('invite');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(inviteMessage);
      } else {
        // Fallback for HTTP or unsupported browsers
        const textArea = document.createElement('textarea');
        textArea.value = inviteMessage;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleFinish = () => {
    if (onComplete) {
      onComplete();
    }
  };

  return (
    <div className="create-circle-flow">
      {step === 'create' && (
        <div className="flow-step">
          <div className="flow-content">
            <h2>Welcome to Movie Matcher!</h2>
            <p className="flow-subtitle">
              Create a circle to start matching movies with friends and family.
            </p>

            {error && <div className="flow-error">{error}</div>}

            <form onSubmit={handleCreateCircle} className="create-circle-form">
              <div className="input-group">
                <label htmlFor="circle-name">Name your circle</label>
                <input
                  id="circle-name"
                  type="text"
                  placeholder="e.g., Movie Night Crew, Family, Roommates"
                  value={circleName}
                  onChange={(e) => setCircleName(e.target.value)}
                  disabled={loading}
                  autoFocus
                />
              </div>
              <button type="submit" className="flow-btn primary" disabled={loading || !circleName.trim()}>
                {loading ? 'Creating...' : 'Create Circle'}
              </button>
            </form>
          </div>
        </div>
      )}

      {step === 'packs' && (
        <div className="flow-step packs-step">
          <div className="flow-header">
            <h2>Add Movies to {createdCircle?.name}</h2>
            <p className="flow-subtitle">
              Choose movie packs to get started. You can always add more later.
            </p>
            {packsAdded > 0 && (
              <div className="packs-added-count">
                {packsAdded} movies added
              </div>
            )}
          </div>

          <div className="inline-pack-selector">
            <PackSelector
              onClose={handlePacksDone}
              onPackAdded={handlePackAdded}
              embedded={true}
            />
          </div>

          <div className="flow-footer">
            <button
              onClick={handlePacksDone}
              className="flow-btn primary"
              disabled={loading}
            >
              {loading ? 'Loading...' : packsAdded > 0 ? 'Continue' : 'Skip for now'}
            </button>
          </div>
        </div>
      )}

      {step === 'invite' && (
        <div className="flow-step">
          <div className="flow-content">
            <div className="success-icon">🎉</div>
            <h2>You're all set!</h2>
            <p className="flow-subtitle">
              {createdCircle?.name} is ready. Invite others to start matching movies together.
            </p>

            {inviteMessage && (
              <div className="invite-section">
                <label>Share this invitation:</label>
                <textarea
                  value={inviteMessage}
                  readOnly
                  rows="5"
                  className="invite-textarea"
                />
                <button onClick={copyToClipboard} className="flow-btn secondary">
                  {copied ? 'Copied!' : 'Copy Invitation'}
                </button>
              </div>
            )}

            <button onClick={handleFinish} className="flow-btn primary">
              Start Swiping
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CreateCircleFlow;
