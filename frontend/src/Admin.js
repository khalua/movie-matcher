import React, { useState, useEffect } from 'react';
import client from './api/client';
import './Admin.css';

function Admin() {
  const [analytics, setAnalytics] = useState(null);
  const [circles, setCircles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [seeding, setSeeding] = useState(false);
  const [seedMessage, setSeedMessage] = useState(null);
  const [selectedCircle, setSelectedCircle] = useState(null);
  const [members, setMembers] = useState([]);
  const [loadingMembers, setLoadingMembers] = useState(false);

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const [analyticsRes, circlesRes] = await Promise.all([
        client.get('/api/admin/analytics'),
        client.get('/api/admin/circles')
      ]);
      setAnalytics(analyticsRes.data);
      setCircles(circlesRes.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching admin data:', err);
      setError('Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const handleCircleClick = async (circle) => {
    if (selectedCircle?.id === circle.id) {
      setSelectedCircle(null);
      setMembers([]);
      return;
    }

    setSelectedCircle(circle);
    setLoadingMembers(true);

    try {
      const response = await client.get(`/api/admin/circles/${circle.id}/members`);
      console.log('Members response:', response.data);
      setMembers(response.data);
    } catch (err) {
      console.error('Error fetching members:', err.response?.data || err.message);
      setMembers([]);
    } finally {
      setLoadingMembers(false);
    }
  };

  const handleSeedCircles = async () => {
    if (!window.confirm('This will add movies from top_movies.txt to ALL circles. Continue?')) {
      return;
    }

    try {
      setSeeding(true);
      setSeedMessage(null);
      const response = await client.post('/api/admin/seed-circles');
      setSeedMessage(response.data.message);
      fetchAdminData();
    } catch (err) {
      console.error('Error seeding circles:', err);
      setSeedMessage('Failed to seed circles');
    } finally {
      setSeeding(false);
    }
  };

  if (loading) {
    return <div className="admin-container"><p>Loading admin data...</p></div>;
  }

  if (error) {
    return <div className="admin-container"><p className="error">{error}</p></div>;
  }

  return (
    <div className="admin-container">
      <h2>Site Administration</h2>

      <section className="admin-section">
        <h3>Global Analytics</h3>
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-value">{analytics?.total_users || 0}</span>
            <span className="stat-label">Total Users</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{analytics?.total_circles || 0}</span>
            <span className="stat-label">Total Circles</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{analytics?.total_movies || 0}</span>
            <span className="stat-label">Total Movies</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{analytics?.active_circles_7d || 0}</span>
            <span className="stat-label">Active Circles (7d)</span>
          </div>
        </div>
      </section>

      <section className="admin-section">
        <h3>All Circles</h3>
        <p className="hint">Click a circle to view its members</p>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Members</th>
              <th>Movies</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {circles.map(circle => (
              <tr
                key={circle.id}
                onClick={() => handleCircleClick(circle)}
                className={`clickable ${selectedCircle?.id === circle.id ? 'selected' : ''}`}
              >
                <td>{circle.name}</td>
                <td>{circle.member_count}</td>
                <td>{circle.movie_count}</td>
                <td>{new Date(circle.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {selectedCircle && (
          <div className="members-panel">
            <h4>Members of "{selectedCircle.name}"</h4>
            {loadingMembers ? (
              <p>Loading members...</p>
            ) : members.length === 0 ? (
              <p>No members found</p>
            ) : (
              <table className="admin-table members-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map(member => (
                    <tr key={member.id}>
                      <td>{member.display_name || '-'}</td>
                      <td>{member.email}</td>
                      <td><span className={`role-badge ${member.role}`}>{member.role}</span></td>
                      <td>{new Date(member.joined_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </section>

      <section className="admin-section">
        <h3>Actions</h3>
        <button
          className="admin-action-btn"
          onClick={handleSeedCircles}
          disabled={seeding}
        >
          {seeding ? 'Seeding...' : 'Seed All Circles with Movies'}
        </button>
        {seedMessage && <p className="seed-message">{seedMessage}</p>}
      </section>
    </div>
  );
}

export default Admin;
