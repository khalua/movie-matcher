import React, { useState, useEffect } from 'react';
import client from '../api/client';
import { useCircle } from '../contexts/CircleContext';
import './CircleManagement.css';

const CircleManagement = ({ user }) => {
  const { currentCircle, circles, setCircles } = useCircle();
  const [newCircleName, setNewCircleName] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [inviteUrl, setInviteUrl] = useState('');
  const [emailBody, setEmailBody] = useState('');
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [editingName, setEditingName] = useState(false);
  const [newDisplayName, setNewDisplayName] = useState('');
  const [profile, setProfile] = useState(null);
  const [changingPassword, setChangingPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const isAdmin = currentCircle?.role === 'admin';

  useEffect(() => {
    fetchProfile();
    if (currentCircle && isAdmin) {
      fetchMembers();
    }
  }, [currentCircle, isAdmin]);

  const fetchProfile = async () => {
    try {
      const response = await client.get('/api/auth/profile');
      setProfile(response.data);
      setNewDisplayName(response.data.display_name || '');
    } catch (error) {
      console.error('Error fetching profile:', error);
    }
  };

  const updateDisplayName = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await client.put('/api/auth/profile', {
        display_name: newDisplayName
      });
      setProfile(response.data);
      setEditingName(false);
      setSuccess('Name updated successfully!');
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to update name');
    } finally {
      setLoading(false);
    }
  };

  const changePassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      setLoading(false);
      return;
    }

    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters');
      setLoading(false);
      return;
    }

    try {
      await client.post('/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      setChangingPassword(false);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setSuccess('Password changed successfully!');
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  const fetchMembers = async () => {
    try {
      const response = await client.get(`/api/circles/${currentCircle.id}/members`);
      setMembers(response.data);
    } catch (error) {
      console.error('Error fetching members:', error);
      setError('Failed to load members');
    }
  };

  const createCircle = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await client.post('/api/circles', { name: newCircleName });
      setCircles([...circles, response.data]);
      setNewCircleName('');
      setSuccess('Circle created! Go to "Add Movies" to add movie packs to get started.');
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to create circle');
    } finally {
      setLoading(false);
    }
  };

  const generateInviteCode = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await client.post(`/api/circles/${currentCircle.id}/invitations`);
      setInviteCode(response.data.code);
      setInviteUrl(response.data.invite_url);
      setEmailBody(response.data.email_body);
      setSuccess('Invitation code generated!');
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to generate invite code');
    } finally {
      setLoading(false);
    }
  };

  const removeMember = async (userId) => {
    if (!window.confirm('Are you sure you want to remove this member?')) return;

    try {
      await client.delete(`/api/circles/${currentCircle.id}/members/${userId}`);
      fetchMembers();
      setSuccess('Member removed successfully');
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to remove member');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setSuccess('Copied to clipboard!');
  };

  return (
    <div className="circle-management">
      <h2>Settings</h2>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}

      <section className="profile-section">
        <h3>Your Profile</h3>
        {editingName ? (
          <form onSubmit={updateDisplayName} className="edit-name-form">
            <div className="input-group">
              <label htmlFor="display-name">Display Name</label>
              <input
                id="display-name"
                type="text"
                placeholder="Your name"
                value={newDisplayName}
                onChange={(e) => setNewDisplayName(e.target.value)}
                disabled={loading}
              />
            </div>
            <div className="edit-buttons">
              <button type="submit" disabled={loading}>Save</button>
              <button type="button" onClick={() => setEditingName(false)} disabled={loading}>Cancel</button>
            </div>
          </form>
        ) : (
          <div className="profile-display">
            <span className="profile-name">{profile?.display_name || 'No name set'}</span>
            <div className="profile-actions">
              <button onClick={() => setEditingName(true)} className="edit-btn">Edit Name</button>
              <button onClick={() => setChangingPassword(true)} className="edit-btn">Change Password</button>
            </div>
          </div>
        )}

        {changingPassword && (
          <form onSubmit={changePassword} className="change-password-form">
            <div className="input-group">
              <label htmlFor="current-password">Current Password</label>
              <input
                id="current-password"
                type="password"
                placeholder="Enter current password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                disabled={loading}
                required
              />
            </div>
            <div className="input-group">
              <label htmlFor="new-password">New Password</label>
              <input
                id="new-password"
                type="password"
                placeholder="Enter new password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={loading}
                required
              />
            </div>
            <div className="input-group">
              <label htmlFor="confirm-password">Confirm New Password</label>
              <input
                id="confirm-password"
                type="password"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={loading}
                required
              />
            </div>
            <div className="edit-buttons">
              <button type="submit" disabled={loading}>Save</button>
              <button type="button" onClick={() => {
                setChangingPassword(false);
                setCurrentPassword('');
                setNewPassword('');
                setConfirmPassword('');
              }} disabled={loading}>Cancel</button>
            </div>
          </form>
        )}
      </section>

      <section className="create-circle">
        <h3>Create New Circle</h3>
        <form onSubmit={createCircle}>
          <div className="input-group">
            <label htmlFor="circle-name">Circle Name</label>
            <input
              id="circle-name"
              type="text"
              placeholder="Enter circle name"
              value={newCircleName}
              onChange={(e) => setNewCircleName(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <button type="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Create Circle'}
          </button>
        </form>
      </section>

      {currentCircle && isAdmin && (
        <>
          <section className="invite-section">
            <h3>Invite Members to {currentCircle.name}</h3>
            <button onClick={generateInviteCode} disabled={loading}>
              Generate Invite Code
            </button>

            {inviteCode && (
              <div className="invite-details">
                <div className="invite-item">
                  <label>Invitation Code:</label>
                  <div className="invite-code-box">
                    <code>{inviteCode}</code>
                    <button onClick={() => copyToClipboard(inviteCode)}>Copy</button>
                  </div>
                </div>

                <div className="invite-item">
                  <label>Invitation URL:</label>
                  <div className="invite-code-box">
                    <code>{inviteUrl}</code>
                    <button onClick={() => copyToClipboard(inviteUrl)}>Copy</button>
                  </div>
                </div>

                <div className="invite-item">
                  <label>Email Body (copy and send):</label>
                  <textarea
                    value={emailBody}
                    readOnly
                    rows="6"
                  />
                  <button onClick={() => copyToClipboard(emailBody)}>Copy Email Body</button>
                </div>
              </div>
            )}
          </section>

          <section className="members-section">
            <h3>Circle Members ({members.length})</h3>
            <div className="members-list">
              {members.map(member => (
                <div key={member.id} className="member-item">
                  <div className="member-info">
                    <span className="member-name">{member.display_name || member.email}</span>
                    {member.role === 'admin' && <span className="badge admin">Admin</span>}
                  </div>
                  {member.id !== user?.id && (
                    <button
                      className="remove-btn"
                      onClick={() => removeMember(member.id)}
                    >
                      Remove
                    </button>
                  )}
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {currentCircle && !isAdmin && (
        <p className="info-message">
          You are a member of {currentCircle.name}. Only admins can invite members and manage the circle.
        </p>
      )}
    </div>
  );
};

export default CircleManagement;
