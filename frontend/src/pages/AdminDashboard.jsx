import { useState, useEffect } from 'react';

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actioningId, setActioningId] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const statsRes = await fetch('/api/admin/system/stats');
      const usersRes = await fetch('/api/admin/users');

      if (!statsRes.ok || !usersRes.ok) {
        throw new Error('Failed to fetch admin data. Check your credentials.');
      }

      const statsData = await statsRes.json();
      const usersData = await usersRes.json();

      setStats(statsData);
      setUsers(usersData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusToggle = async (userId, currentStatus) => {
    setActioningId(userId);
    try {
      const res = await fetch(`/api/admin/users/${userId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !currentStatus })
      });
      if (!res.ok) throw new Error('Failed to update status');
      const updatedUser = await res.json();
      
      setUsers(users.map(u => u.id === userId ? { ...u, is_active: updatedUser.is_active } : u));
      // Refresh stats counters
      const statsRes = await fetch('/api/admin/system/stats');
      if (statsRes.ok) setStats(await statsRes.json());
    } catch (err) {
      alert(err.message);
    } finally {
      setActioningId(null);
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    setActioningId(userId);
    try {
      const res = await fetch(`/api/admin/users/${userId}/role`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole })
      });
      if (!res.ok) throw new Error('Failed to update role');
      const updatedUser = await res.json();
      
      setUsers(users.map(u => u.id === userId ? { ...u, role: updatedUser.role } : u));
      // Refresh stats
      const statsRes = await fetch('/api/admin/system/stats');
      if (statsRes.ok) setStats(await statsRes.json());
    } catch (err) {
      alert(err.message);
    } finally {
      setActioningId(null);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '40px', color: '#fff', textAlign: 'center', fontFamily: 'Space Grotesk, sans-serif' }}>
        <span className="material-symbols-outlined" style={{ fontSize: '48px', animation: 'spin 1.5s infinite linear' }}>sync</span>
        <p style={{ marginTop: '12px' }}>Loading Administration Console...</p>
        <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '40px', color: '#e63946', textAlign: 'center', fontFamily: 'Space Grotesk, sans-serif' }}>
        <span className="material-symbols-outlined" style={{ fontSize: '48px' }}>error</span>
        <p style={{ marginTop: '12px' }}>Error: {error}</p>
        <button onClick={fetchData} style={{ marginTop: '16px', background: '#e63946', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer' }}>Retry</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto', fontFamily: 'Inter, sans-serif', color: '#fff' }}>
      <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: '28px', fontWeight: 700, marginBottom: '24px', color: '#fca311' }}>
        System Administration
      </h1>

      {/* ── STATS CARDS ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '16px',
        marginBottom: '32px'
      }}>
        {[
          { title: 'Total Users', val: stats?.total_users, icon: 'group', color: '#4cc9f0' },
          { title: 'Responders', val: stats?.total_responders, icon: 'badge', color: '#f72585' },
          { title: 'Active Accounts', val: stats?.active_users, icon: 'how_to_reg', color: '#27ae60' },
          { title: 'SOS Triggers', val: stats?.sos_requests, icon: 'emergency', color: '#e63946' },
          { title: 'AI Triages', val: stats?.ai_requests, icon: 'psychology', color: '#a2d2ff' },
          { title: 'Hospital Searches', val: stats?.hospital_searches, icon: 'local_hospital', color: '#fca311' }
        ].map((s, idx) => (
          <div key={idx} style={{
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '12px',
            padding: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px'
          }}>
            <div style={{
              background: `rgba(${s.color === '#27ae60' ? '39,174,96' : s.color === '#e63946' ? '230,57,70' : '252,163,17'}, 0.1)`,
              borderRadius: '10px',
              padding: '10px',
              display: 'flex'
            }}>
              <span className="material-symbols-outlined" style={{ color: s.color, fontSize: '24px' }}>{s.icon}</span>
            </div>
            <div>
              <p style={{ fontSize: '12px', color: '#a0a0b0', margin: 0, fontWeight: 500 }}>{s.title}</p>
              <h3 style={{ fontSize: '22px', margin: '4px 0 0 0', fontWeight: 700, fontFamily: 'Space Grotesk, sans-serif' }}>{s.val}</h3>
            </div>
          </div>
        ))}
      </div>

      {/* ── USER MANAGEMENT TABLE ── */}
      <div style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid rgba(255, 255, 255, 0.06)',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.15)'
      }}>
        <h2 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: '18px', fontWeight: 600, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="material-symbols-outlined" style={{ color: '#fca311' }}>manage_accounts</span>
          User & Permission Control
        </h2>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#a0a0b0', fontSize: '13px', fontWeight: 600 }}>
                <th style={{ padding: '12px 16px' }}>Name</th>
                <th style={{ padding: '12px 16px' }}>Email</th>
                <th style={{ padding: '12px 16px' }}>Role</th>
                <th style={{ padding: '12px 16px' }}>Status</th>
                <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} style={{
                  borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                  fontSize: '14px',
                  transition: 'background 0.2s'
                }} onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.01)'; }}
                   onMouseOut={(e) => { e.currentTarget.style.background = 'none'; }}>
                  <td style={{ padding: '16px', fontWeight: 600 }}>{u.name}</td>
                  <td style={{ padding: '16px', color: '#d0d0d0' }}>{u.email}</td>
                  <td style={{ padding: '16px' }}>
                    <select
                      value={u.role}
                      disabled={actioningId === u.id}
                      onChange={(e) => handleRoleChange(u.id, e.target.value)}
                      style={{
                        background: '#14213d',
                        color: '#fff',
                        border: '1px solid rgba(255,255,255,0.15)',
                        borderRadius: '6px',
                        padding: '4px 8px',
                        fontSize: '13px',
                        cursor: 'pointer',
                        outline: 'none'
                      }}
                    >
                      <option value="USER">USER</option>
                      <option value="RESPONDER">RESPONDER</option>
                      <option value="ADMIN">ADMIN</option>
                    </select>
                  </td>
                  <td style={{ padding: '16px' }}>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      fontSize: '11px',
                      fontWeight: 600,
                      color: u.is_active ? '#27ae60' : '#e63946',
                      background: u.is_active ? 'rgba(39,174,96,0.1)' : 'rgba(230,57,70,0.1)',
                      padding: '3px 8px',
                      borderRadius: '10px'
                    }}>
                      <span style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background: u.is_active ? '#27ae60' : '#e63946'
                      }} />
                      {u.is_active ? 'ACTIVE' : 'SUSPENDED'}
                    </span>
                  </td>
                  <td style={{ padding: '16px', textAlign: 'right' }}>
                    <button
                      disabled={actioningId === u.id}
                      onClick={() => handleStatusToggle(u.id, u.is_active)}
                      style={{
                        background: u.is_active ? 'rgba(230,57,70,0.1)' : 'rgba(39,174,96,0.1)',
                        border: `1px solid ${u.is_active ? 'rgba(230,57,70,0.2)' : 'rgba(39,174,96,0.2)'}`,
                        color: u.is_active ? '#ff4d4d' : '#27ae60',
                        padding: '6px 12px',
                        borderRadius: '8px',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                      onMouseOver={(e) => { e.currentTarget.style.transform = 'scale(1.02)'; }}
                      onMouseOut={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
                    >
                      {u.is_active ? 'Suspend Account' : 'Activate Account'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
