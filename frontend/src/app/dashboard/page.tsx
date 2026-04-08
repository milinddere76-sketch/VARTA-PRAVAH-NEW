"use client";

import React, { useState, useEffect } from 'react';
import { Plus, Play, ExternalLink, Activity, Info, AlertCircle, Settings, Trash2, Square, Megaphone } from 'lucide-react';

interface Channel {
  id: number;
  name: string;
  language: string;
  youtube_stream_key: string;
  is_streaming: boolean;
  created_at: string;
}

interface AdCampaign {
  id: number;
  name: string;
  video_url: string;
  scheduled_hours: string;
  is_active: boolean;
}

export default function DashboardPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [newChannel, setNewChannel] = useState({ name: '', youtube_stream_key: '', language: 'Marathi' });
  const [processing, setProcessing] = useState<number | null>(null);
  
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [settingsData, setSettingsData] = useState({ groq_api_key: '', world_news_api_key: '' });
  
  const [showAdModal, setShowAdModal] = useState<number | null>(null);
  const [ads, setAds] = useState<AdCampaign[]>([]);
  const [newAd, setNewAd] = useState({ name: '', video_url: '', scheduled_hours: '08,12,18,21' });
  
  const API_URL = '/api';

  useEffect(() => {
    fetchChannels();
  }, []);

  const fetchChannels = async () => {
    try {
      const res = await fetch(`${API_URL}/channels`);
      const data = await res.json();
      setChannels(data);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch channels", err);
      setLoading(false);
    }
  };

  const handleCreateChannel = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/channels`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...newChannel, owner_id: 1 })
      });

      if (res.ok) {
        setShowModal(false);
        setNewChannel({ name: '', youtube_stream_key: '', language: 'Marathi' });
        fetchChannels();
      } else {
        const errorData = await res.json().catch(() => ({}));
        alert(`Failed to create channel: ${errorData.detail || res.statusText}`);
      }
    } catch (err) {
      console.error("Failed to create channel", err);
      alert("Network error: Could not connect to the backend API.");
    }
  };

  const handleUpdateSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsData)
      });
      if (res.ok) {
        alert("API Config updated successfully! Live across backend.");
        setShowSettingsModal(false);
      } else {
        alert("Failed to update keys.");
      }
    } catch(err) {
      alert("Network Error");
    }
  };

  const handleTriggerNews = async (channelId: number) => {
    setProcessing(channelId);
    
    // Optimistically update the UI to show LIVE immediately
    setChannels(prevChannels => 
      prevChannels.map(ch => 
        ch.id === channelId ? { ...ch, is_streaming: true } : ch
      )
    );

    try {
      const res = await fetch(`${API_URL}/channels/${channelId}/trigger`, {
        method: 'POST'
      });
      if (res.ok) {
        // No alert needed for "News generation triggered!" if the status pill already updated.
        // But we refresh to get the definite state from the server.
        await fetchChannels();
      } else {
        const errorData = await res.json().catch(() => ({}));
        alert(`Failed to trigger news: ${errorData.detail || res.statusText}`);
        // Revert optimistic update on failure
        await fetchChannels();
      }
    } catch (err) {
      console.error("Failed to trigger news", err);
      alert("Network error: Could not connect to the backend API. Check if the server is running.");
      // Revert optimistic update on failure
      await fetchChannels();
    } finally {
      setProcessing(null);
    }
  };

  const handleStopChannel = async (channelId: number) => {
    if (!confirm("Are you sure you want to halt broadcasting immediately? This will drop the YouTube stream.")) return;
    
    // Optimistic UI update
    setChannels(prev => prev.map(ch => ch.id === channelId ? { ...ch, is_streaming: false } : ch));
    
    try {
      const res = await fetch(`${API_URL}/channels/${channelId}/stop`, { method: 'POST' });
      if (!res.ok) throw new Error("Failed to stop.");
      await fetchChannels();
    } catch (err) {
      alert("Error stopping stream.");
      await fetchChannels();
    }
  };

  const handleDeleteChannel = async (channelId: number) => {
    if (!confirm("Are you sure you want to permanently delete this channel and stop any active streams?")) return;
    
    try {
      const res = await fetch(`${API_URL}/channels/${channelId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error("Failed to delete.");
      await fetchChannels();
    } catch (err) {
      alert("Error deleting channel.");
    }
  };

  const fetchAds = async (channelId: number) => {
    try {
      const res = await fetch(`${API_URL}/channels/${channelId}/ads`);
      const data = await res.json();
      setAds(data);
    } catch (err) { console.error(err); }
  };

  const handleCreateAd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!showAdModal) return;
    try {
      const res = await fetch(`${API_URL}/channels/${showAdModal}/ads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...newAd, channel_id: showAdModal })
      });
      if (res.ok) {
        setNewAd({ name: '', video_url: '', scheduled_hours: '08,12,18,21' });
        fetchAds(showAdModal);
      }
    } catch (err) { alert("Error adding ad."); }
  };

  const handleDeleteAd = async (adId: number) => {
    try {
      await fetch(`${API_URL}/ads/${adId}`, { method: 'DELETE' });
      if (showAdModal) fetchAds(showAdModal);
    } catch (err) { alert("Error."); }
  };

  return (
    <div className="min-h-screen bg-[#0f111a] text-white flex font-sans">
      {/* Sidebar */}
      <aside className="w-72 bg-[#161926] p-8 border-r border-[#22273a] flex flex-col">
        <div className="flex items-center space-x-3 mb-12">
          <div className="w-10 h-10 bg-gradient-to-tr from-blue-600 to-indigo-400 rounded-lg flex items-center justify-center">
            <Activity size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">VartaPravah</h1>
        </div>
        
        <nav className="flex-1 space-y-2">
          <NavItem icon={<Activity size={20}/>} label="Dashboard" href="/dashboard" active />
          <NavItem 
            icon={<Plus size={20}/>} 
            label="Channels" 
            onClick={() => setShowModal(true)} 
          />
          <NavItem icon={<Info size={20}/>} label="Workflows" href="http://localhost:8080" target="_blank" />
          <NavItem icon={<Settings size={20}/>} label="API Config" onClick={() => setShowSettingsModal(true)} />
        </nav>

        <div className="mt-auto pt-8 border-t border-[#22273a]">
          <div className="bg-gradient-to-r from-blue-600/20 to-transparent p-4 rounded-xl border border-blue-600/30">
            <p className="text-xs text-blue-400 font-bold uppercase tracking-wider mb-1">Status</p>
            <p className="text-sm text-gray-300">All systems operational</p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-10 overflow-y-auto">
        <header className="flex justify-between items-center mb-12">
          <div>
            <h2 className="text-4xl font-bold mb-2">Control Center</h2>
            <p className="text-gray-400">Manage your AI-powered 24x7 news network.</p>
          </div>
          <button 
            onClick={() => setShowModal(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold transition-all shadow-lg shadow-blue-600/20 flex items-center space-x-2"
          >
            <Plus size={20} />
            <span>New Channel</span>
          </button>
        </header>

        {loading ? (
          <div className="flex justify-center items-center h-96">
            <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
            {channels.map(channel => (
              <div key={channel.id} className="bg-[#161926] p-8 rounded-2xl border border-[#22273a] hover:border-blue-500/50 transition">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-2xl font-bold mb-1">{channel.name}</h3>
                    <p className="text-gray-400 text-sm">Language: <span className="text-blue-400 font-medium">{channel.language}</span></p>
                  </div>
                  <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest ${channel.is_streaming ? 'bg-green-500/10 text-green-400 border border-green-500/30' : 'bg-gray-500/10 text-gray-400 border border-gray-500/30'}`}>
                    {channel.is_streaming ? '● Live' : '● Inactive'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-8">
                  <div className="bg-[#0f111a] p-4 rounded-xl border border-[#22273a]">
                    <p className="text-gray-500 text-xs uppercase mb-1">Stream Key</p>
                    <p className="text-sm font-mono truncate">{channel.youtube_stream_key || 'Not Set'}</p>
                  </div>
                  <div className="bg-[#0f111a] p-4 rounded-xl border border-[#22273a]">
                    <p className="text-gray-500 text-xs uppercase mb-1">Created</p>
                    <p className="text-sm">{new Date(channel.created_at).toLocaleDateString()}</p>
                  </div>
                </div>

                <div className="flex space-x-3">
                  <div className="flex-1 bg-blue-600/10 border border-blue-500/30 text-blue-400 py-3.5 rounded-xl font-bold flex items-center justify-center space-x-2 animate-pulse">
                    <Activity size={18} />
                    <span>🛰️ Automator: ACTIVE</span>
                  </div>
                  <button
                    onClick={() => handleStopChannel(channel.id)}
                    className="bg-red-500/10 hover:bg-red-600 border border-red-500/30 hover:border-red-600 text-red-500 hover:text-white px-5 rounded-xl font-bold transition flex items-center justify-center"
                    title="Stop Broadcast"
                  >
                    <Square fill="currentColor" size={14} />
                  </button>
                  <button
                    onClick={() => { setShowAdModal(channel.id); fetchAds(channel.id); }}
                    className="bg-purple-500/10 hover:bg-purple-600 border border-purple-500/30 hover:border-purple-600 text-purple-500 hover:text-white px-5 rounded-xl font-bold transition flex items-center justify-center"
                    title="Ad Campaigns"
                  >
                    <Megaphone size={18} />
                  </button>
                  <a 
                    href="https://studio.youtube.com/channel/live" 
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-[#22273a] hover:bg-[#2c324a] text-white px-5 rounded-xl font-bold transition flex items-center justify-center"
                    title="View Stream Status"
                  >
                    <ExternalLink size={18} />
                  </a>
                  <button
                    onClick={() => handleDeleteChannel(channel.id)}
                    className="bg-transparent hover:bg-red-900/30 border border-transparent hover:border-red-600/30 text-gray-500 hover:text-red-400 px-4 rounded-xl transition flex items-center justify-center"
                    title="Delete Channel"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))}

            {channels.length === 0 && (
              <div className="col-span-full bg-[#161926] border-2 border-dashed border-[#22273a] p-20 rounded-3xl flex flex-col items-center justify-center text-center">
                <AlertCircle size={64} className="text-gray-600 mb-6" />
                <h3 className="text-2xl font-bold mb-2">No Channels Yet</h3>
                <p className="text-gray-400 mb-8 max-w-md">Create your first 24x7 AI news channel to start broadcasting Marathi content to the world.</p>
                <button 
                  onClick={() => setShowModal(true)}
                  className="text-blue-400 hover:text-blue-300 font-bold underline underline-offset-4"
                >
                  Create your first channel now
                </button>
              </div>
            )}
          </div>
        )}

        {/* Ads Management Modal */}
        {showAdModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
            <div className="bg-[#161926] w-full max-w-2xl p-10 rounded-3xl border border-[#22273a] shadow-2xl max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-start mb-8">
                <div>
                  <h3 className="text-3xl font-bold mb-2">Ad Scheduler</h3>
                  <p className="text-gray-400">Manage commercials & custom clips for this channel.</p>
                </div>
                <button onClick={() => setShowAdModal(null)} className="text-gray-500 hover:text-white">✕</button>
              </div>

              <form onSubmit={handleCreateAd} className="bg-[#0f111a] p-6 rounded-2xl border border-[#22273a] mb-10 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <input 
                    placeholder="Ad Name (e.g. Morning Promo)"
                    className="bg-transparent border border-[#22273a] rounded-xl px-4 py-3 focus:border-blue-500 outline-none"
                    value={newAd.name}
                    onChange={e => setNewAd({...newAd, name: e.target.value})}
                    required
                  />
                  <input 
                    placeholder="Hours (e.g. 09,14,21)"
                    className="bg-transparent border border-[#22273a] rounded-xl px-4 py-3 focus:border-blue-500 outline-none"
                    value={newAd.scheduled_hours}
                    onChange={e => setNewAd({...newAd, scheduled_hours: e.target.value})}
                    required
                  />
                </div>
                <input 
                  placeholder="Video URL (S3 or Direct Link)"
                  className="w-full bg-transparent border border-[#22273a] rounded-xl px-4 py-3 focus:border-blue-500 outline-none"
                  value={newAd.video_url}
                  onChange={e => setNewAd({...newAd, video_url: e.target.value})}
                  required
                />
                <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-xl font-bold">Add to Schedule</button>
              </form>

              <div className="space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-widest text-gray-500">Active Campaigns</h4>
                {ads.map(ad => (
                  <div key={ad.id} className="flex items-center justify-between bg-[#1f2335] p-5 rounded-2xl border border-[#2c324a]">
                    <div>
                      <p className="font-bold">{ad.name}</p>
                      <p className="text-xs text-blue-400">Plays at: {ad.scheduled_hours}:00</p>
                    </div>
                    <button onClick={() => handleDeleteAd(ad.id)} className="text-red-500 hover:bg-red-500/10 p-2 rounded-lg transition">
                      <Trash2 size={20} />
                    </button>
                  </div>
                ))}
                {ads.length === 0 && <p className="text-center text-gray-600 py-10">No advertisements scheduled yet.</p>}
              </div>
            </div>
          </div>
        )}

        {/* Modal */}
        {showSettingsModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-[#161926] w-full max-w-lg p-10 rounded-3xl border border-[#22273a] shadow-2xl">
              <h3 className="text-3xl font-bold mb-2">Global Settings</h3>
              <p className="text-gray-400 mb-8">Update your backend API keys.</p>
              
              <form onSubmit={handleUpdateSettings} className="space-y-6">
                <div>
                  <label className="block text-sm font-bold text-gray-400 mb-2 uppercase tracking-wider">Groq API Key</label>
                  <input 
                    type="password"
                    value={settingsData.groq_api_key}
                    onChange={(e) => setSettingsData({...settingsData, groq_api_key: e.target.value})}
                    className="w-full bg-[#0f111a] border border-[#22273a] rounded-xl px-5 py-4 focus:outline-none focus:border-blue-500 transition"
                    placeholder="gsk_..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-gray-400 mb-2 uppercase tracking-wider">World News API Key</label>
                  <input 
                    type="password"
                    value={settingsData.world_news_api_key}
                    onChange={(e) => setSettingsData({...settingsData, world_news_api_key: e.target.value})}
                    className="w-full bg-[#0f111a] border border-[#22273a] rounded-xl px-5 py-4 focus:outline-none focus:border-blue-500 transition"
                  />
                </div>
                
                <div className="flex space-x-4 pt-4">
                  <button type="button" onClick={() => setShowSettingsModal(false)} className="flex-1 bg-transparent hover:bg-[#22273a] text-white py-4 rounded-xl font-bold transition border border-[#22273a]">
                    Cancel
                  </button>
                  <button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl font-bold transition shadow-lg shadow-blue-600/20">
                    Save Config
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-[#161926] w-full max-w-lg p-10 rounded-3xl border border-[#22273a] shadow-2xl">
              <h3 className="text-3xl font-bold mb-2">Create New Channel</h3>
              <p className="text-gray-400 mb-8">Set up your streaming configuration.</p>
              
              <form onSubmit={handleCreateChannel} className="space-y-6">
                <div>
                  <label className="block text-sm font-bold text-gray-400 mb-2 uppercase tracking-wider">Channel Name</label>
                  <input 
                    type="text"
                    required
                    value={newChannel.name}
                    onChange={(e) => setNewChannel({...newChannel, name: e.target.value})}
                    className="w-full bg-[#0f111a] border border-[#22273a] rounded-xl px-5 py-4 focus:outline-none focus:border-blue-500 transition"
                    placeholder="e.g. Marathi Express Live"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-gray-400 mb-2 uppercase tracking-wider">YouTube Stream Key</label>
                  <input 
                    type="text"
                    required
                    value={newChannel.youtube_stream_key}
                    onChange={(e) => setNewChannel({...newChannel, youtube_stream_key: e.target.value})}
                    className="w-full bg-[#0f111a] border border-[#22273a] rounded-xl px-5 py-4 focus:outline-none focus:border-blue-500 transition font-mono"
                    placeholder="qcu7-xe..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-gray-400 mb-2 uppercase tracking-wider">Broadcast Language</label>
                  <select 
                    value={newChannel.language}
                    onChange={(e) => setNewChannel({...newChannel, language: e.target.value})}
                    className="w-full bg-[#0f111a] border border-[#22273a] rounded-xl px-5 py-4 focus:outline-none focus:border-blue-500 transition appearance-none"
                  >
                    <option value="Hindi">Hindi</option>
                    <option value="Marathi">Marathi</option>
                    <option value="Bengali">Bengali</option>
                    <option value="Telugu">Telugu</option>
                    <option value="Tamil">Tamil</option>
                    <option value="Gujarati">Gujarati</option>
                    <option value="Kannada">Kannada</option>
                    <option value="Malayalam">Malayalam</option>
                    <option value="Odia">Odia</option>
                    <option value="Punjabi">Punjabi</option>
                    <option value="Assamese">Assamese</option>
                    <option value="English">English</option>
                  </select>
                </div>
                
                <div className="flex space-x-4 pt-4">
                  <button 
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="flex-1 bg-[#22273a] hover:bg-[#2c324a] py-4 rounded-xl font-bold transition"
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit"
                    className="flex-1 bg-blue-600 hover:bg-blue-700 py-4 rounded-xl font-bold transition shadow-lg shadow-blue-600/20"
                  >
                    Create Channel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function NavItem({ 
  icon, 
  label, 
  href, 
  active = false, 
  target = "_self",
  onClick
}: { 
  icon: React.ReactNode, 
  label: string, 
  href?: string, 
  active?: boolean,
  target?: string,
  onClick?: () => void
}) {
  const className = `w-full flex items-center space-x-3 py-3.5 px-5 rounded-xl font-bold transition ${active ? 'bg-blue-600 text-white' : 'text-gray-500 hover:bg-[#22273a] hover:text-gray-300'}`;

  if (onClick) {
    return (
      <button onClick={onClick} className={className}>
        {icon}
        <span>{label}</span>
      </button>
    );
  }

  return (
    <a href={href || "#"} target={target} className={className}>
      {icon}
      <span>{label}</span>
    </a>
  );
}
