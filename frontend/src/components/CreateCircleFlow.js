import React, { useState } from 'react';
import client from '../api/client';
import { useCircle } from '../contexts/CircleContext';
import PackSelector from './PackSelector';
import './CreateCircleFlow.css';

const CreateCircleFlow = ({ onComplete, needsDisplayName = false, onNameSaved }) => {
  const { circles, setCircles, switchCircle } = useCircle();
  const [step, setStep] = useState('create'); // 'create' | 'packs' | 'invite'
  const [circleName, setCircleName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [createdCircle, setCreatedCircle] = useState(null);
  const [inviteMessage, setInviteMessage] = useState('');
  const [copied, setCopied] = useState(false);
  const [packsAdded, setPacksAdded] = useState(0);

  const handleCreateCircle = async (e) => {
    e.preventDefault();
    if (!circleName.trim()) return;
    if (needsDisplayName && !displayName.trim()) return;

    setLoading(true);
    setError(null);

    try {
      // Save display name first if needed
      if (needsDisplayName && displayName.trim()) {
        const profileResponse = await client.put('/api/auth/profile', {
          display_name: displayName.trim()
        });
        if (onNameSaved) {
          onNameSaved(profileResponse.data);
        }
      }

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
              {needsDisplayName
                ? "Let's get you set up. Tell us your name and create your first circle."
                : "Create a circle to start matching movies with friends and family."}
            </p>

            {error && <div className="flow-error">{error}</div>}

            <form onSubmit={handleCreateCircle} className="create-circle-form">
              {needsDisplayName && (
                <div className="input-group">
                  <label htmlFor="display-name">Your name</label>
                  <input
                    id="display-name"
                    type="text"
                    placeholder="What should we call you?"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    disabled={loading}
                    autoFocus
                  />
                </div>
              )}
              <div className="input-group">
                <label htmlFor="circle-name">Name your circle</label>
                <input
                  id="circle-name"
                  type="text"
                  placeholder="e.g., Movie Night Crew, Family, Roommates"
                  value={circleName}
                  onChange={(e) => setCircleName(e.target.value)}
                  disabled={loading}
                  autoFocus={!needsDisplayName}
                />
              </div>
              <button
                type="submit"
                className="flow-btn primary"
                disabled={loading || !circleName.trim() || (needsDisplayName && !displayName.trim())}
              >
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
              Choose one or more movie packs to get started. You can change this later.
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
              isAdmin={true}
            />
          </div>

          <div className="flow-footer">
            <button
              onClick={handlePacksDone}
              className="flow-btn primary"
              disabled={loading || packsAdded === 0}
            >
              {loading ? 'Loading...' : packsAdded > 0 ? 'Continue' : 'Add movies to continue'}
            </button>
            {packsAdded === 0 && (
              <p className="flow-helper-text">
                Add at least one movie pack to get started
              </p>
            )}
          </div>
        </div>
      )}

      {step === 'invite' && (
        <div className="flow-step">
          <div className="flow-content">
            <div className="success-icon">🎉</div>
            <h2>You're all set!</h2>
            <p className="flow-subtitle">
              Your circle "{createdCircle?.name}" is ready. Invite others to start matching movies together.
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
                <button onClick={copyToClipboard} className="flow-btn primary">
                  {copied ? 'Copied!' : 'Copy Invitation'}
                </button>
              </div>
            )}

            <button onClick={handleFinish} className="flow-btn secondary">
              Start Swiping
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CreateCircleFlow;
