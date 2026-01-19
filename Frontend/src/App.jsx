import React, { useState, useEffect } from 'react';
import { Settings, Camera, History, Bell, ShieldCheck, Volume2, Video, Download, Trash2, PauseCircle, PlayCircle } from 'lucide-react';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  
  const [settings, setSettings] = useState({
    start_time: "09:00", end_time: "17:00", parent_phone: "", notify_enabled: false
  });
  
  const [history, setHistory] = useState([]);
  const [recordings, setRecordings] = useState([]);
  const [isPaused, setIsPaused] = useState(false); // Controls the Pause/Resume Button
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000); // Poll status every 3s
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [sets, hist, recs, status] = await Promise.all([
        fetch('/api/settings').then(r => r.json()),
        fetch('/api/history').then(r => r.json()),
        fetch('/api/recordings').then(r => r.json()),
        fetch('/api/recording/status').then(r => r.json())
      ]);
      setSettings(sets);
      setHistory(hist);
      setRecordings(recs);
      setIsPaused(status.is_paused);
    } catch (e) { console.error(e); }
  };

  const handleTogglePause = async () => {
    try {
        const res = await fetch('/api/recording/toggle', { method: 'POST' });
        const data = await res.json();
        setIsPaused(data.is_paused);
    } catch (e) { alert("Connection Error"); }
  };

  const handleDeleteRecording = async (filename) => {
    if(!window.confirm(`Delete "${filename}"?`)) return;

    try {
        const res = await fetch(`/api/recordings/${filename}`, { method: 'DELETE' });
        const data = await res.json();

        if (res.ok) {
            // Remove file from list
            setRecordings(recordings.filter(f => f !== filename));
            
            // If backend says we paused (because we deleted active file), update UI
            if(data.paused) {
                setIsPaused(true);
                alert("⚠️ Active recording was deleted.\n\nRecording is now PAUSED.\nClick 'Resume Rec' to start a new file.");
            }
        } else {
            alert(`Failed: ${data.error}`);
        }
    } catch (e) { alert("Server Error"); }
  };

  const handleSave = async () => {
    setLoading(true);
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    });
    setLoading(false);
    alert("Configuration Saved!");
  };

  const handleAudioUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch('/api/upload_audio', { method: 'POST', body: formData });
      const data = await res.json();
      alert(res.ok ? data.status : data.error);
    } catch (error) { alert("Upload failed."); }
    setUploading(false);
  };

  const todayData = history.find(h => h.date === new Date().toISOString().split('T')[0]);
  const todayCount = todayData ? todayData.detections : 0;

  return (
    <div className="app-container">
      <header className="header">
        <div className="brand">
          <ShieldCheck size={32} color="#3b82f6" />
          <h1>SmartStudy Monitor</h1>
        </div>
        <div style={{display: 'flex', gap: '20px', alignItems: 'center'}}>
            <div className="status-badge">Violations: {todayCount}</div>
            <div className="nav-buttons" style={{display: 'flex', gap: '10px'}}>
                <button onClick={() => setActiveTab('dashboard')} style={{backgroundColor: activeTab==='dashboard'?'#3b82f6':'#334155'}}>Dashboard</button>
                <button onClick={() => setActiveTab('history')} style={{backgroundColor: activeTab==='history'?'#3b82f6':'#334155'}}>History</button>
            </div>
        </div>
      </header>

      {activeTab === 'dashboard' && (
      <div className="dashboard-grid">
        <div className="main-content">
          <div className="card">
            <div className="card-title" style={{justifyContent: 'space-between'}}>
              <div style={{display:'flex', gap:'10px', alignItems:'center'}}>
                  <Camera size={20} />
                  <span>Live Feed</span>
              </div>
              
              {/* PAUSE / RESUME BUTTON */}
              <button 
                onClick={handleTogglePause}
                style={{
                    display: 'flex', alignItems: 'center', gap: '5px',
                    backgroundColor: isPaused ? '#22c55e' : '#eab308',
                    border: 'none', padding: '5px 12px', borderRadius: '5px',
                    color: 'white', cursor: 'pointer', fontWeight: 'bold'
                }}
              >
                {isPaused ? <><PlayCircle size={16}/> Resume Rec</> : <><PauseCircle size={16}/> Pause Rec</>}
              </button>
            </div>

            <div className="video-wrapper">
              <img src="/video_feed" alt="Live Stream" className="video-feed" />
              <div className={`live-indicator ${isPaused ? 'paused' : ''}`}>
                 {isPaused ? "⏸️ PAUSED" : "REC ● LIVE"}
              </div>
            </div>
            
            <p style={{marginTop: '10px', fontSize: '0.9rem', color: '#94a3b8', textAlign: 'center'}}>
                {isPaused 
                    ? "Recording is PAUSED. AI detection is still running." 
                    : "Recording is ACTIVE. Video is being saved."}
            </p>
          </div>

          <div className="card" style={{marginTop: '30px'}}>
            <div className="card-title"><Volume2 size={20} /><span>Warning Voice</span></div>
            <div className="form-group">
                <label>Upload new Alert Sound (WAV/MP3)</label>
                <div style={{display: 'flex', gap: '10px'}}>
                    <input type="file" accept="audio/*" onChange={handleAudioUpload} />
                    {uploading && <span>Uploading...</span>}
                </div>
            </div>
          </div>
        </div>

        <div className="sidebar">
          <div className="card">
            <div className="card-title"><Settings size={20} /><span>Configuration</span></div>
            <div className="form-group"><label>Start Time</label><input type="time" value={settings.start_time} onChange={(e) => setSettings({...settings, start_time: e.target.value})} /></div>
            <div className="form-group"><label>End Time</label><input type="time" value={settings.end_time} onChange={(e) => setSettings({...settings, end_time: e.target.value})} /></div>
            <div className="card-title" style={{marginTop:'20px'}}><Bell size={20} /><span>Alerts</span></div>
            <div className="form-group"><label>Parent Phone</label><input type="text" value={settings.parent_phone} onChange={(e) => setSettings({...settings, parent_phone: e.target.value})} /></div>
            <div className="form-group"><label className="checkbox-group"><input type="checkbox" checked={settings.notify_enabled} onChange={(e) => setSettings({...settings, notify_enabled: e.target.checked})} /><span>Enable SMS</span></label></div>
            <button className="save-btn" onClick={handleSave} disabled={loading}>{loading?'Saving...':'Save Config'}</button>
          </div>
        </div>
      </div>
      )}

      {activeTab === 'history' && (
          <div className="history-grid" style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px'}}>
              <div className="card">
                <div className="card-title"><History size={20} /><span>7-Day History</span></div>
                <table>
                  <thead><tr><th>Date</th><th>Violations</th><th>Status</th></tr></thead>
                  <tbody>
                    {history.map((day, i) => (
                      <tr key={i}><td>{day.date}</td><td><span className="violation-count">{day.detections}</span></td><td>{day.detections>5?'🔴 Distracted':'🟢 Focused'}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="card">
                <div className="card-title"><Video size={20} /><span>Recordings</span></div>
                <div className="recordings-list" style={{maxHeight: '400px', overflowY: 'auto'}}>
                    {recordings.map((file, i) => (
                        <div key={i} style={{display:'flex',justifyContent:'space-between',padding:'15px',borderBottom:'1px solid #334155', alignItems: 'center'}}>
                            <span style={{color:'white', fontSize:'0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', maxWidth: '180px'}} title={file}>{file}</span>
                            <div style={{display:'flex', gap:'10px'}}>
                                <a href={`/api/recordings/${file}`} download className="action-btn" style={{backgroundColor:'#3b82f6'}}><Download size={16} /></a>
                                <button onClick={() => handleDeleteRecording(file)} className="action-btn" style={{backgroundColor:'#ef4444'}}><Trash2 size={16} /></button>
                            </div>
                        </div>
                    ))}
                </div>
              </div>
          </div>
      )}
    </div>
  )
}

export default App