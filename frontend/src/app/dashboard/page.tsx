"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Activity, ExternalLink, Square, Play, Settings, Megaphone, Trash2 } from 'lucide-react';

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

const API_URL = '/api';

export default function DashboardPage() {
  const [channel, setChannel]     = useState<Channel | null>(null);
  const [loading, setLoading]     = useState(true);
  const [processing, setProcessing] = useState(false);

  const [showAdModal, setShowAdModal] = useState(false);
  const [ads, setAds]             = useState<AdCampaign[]>([]);
  const [newAd, setNewAd]         = useState({ name: '', video_url: '', scheduled_hours: '08,12,18,21' });

  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [settingsData, setSettingsData] = useState({ groq_api_key: '', world_news_api_key: '' });

  const [bulletinCount, setBulletinCount] = useState(0);
  const [currentAnchor, setCurrentAnchor] = useState<'Priya Desai ♀' | 'Arjun Sharma ♂'>('Priya Desai ♀');

  // Fetch the single default channel (id=1)
  const fetchChannel = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/channels`);
      const data: Channel[] = await res.json();
      setChannel(data[0] ?? null);
    } catch (err) {
      console.error('Failed to fetch channel', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchChannel();
    const interval = setInterval(fetchChannel, 15_000); // refresh every 15s
    return () => clearInterval(interval);
  }, [fetchChannel]);

  // Simulate anchor alternation indicator (purely cosmetic — actual alternation is in the workflow)
  useEffect(() => {
    if (!channel?.is_streaming) return;
    const interval = setInterval(() => {
      setBulletinCount(n => n + 1);
      setCurrentAnchor(n => n === 'Priya Desai ♀' ? 'Arjun Sharma ♂' : 'Priya Desai ♀');
    }, 30 * 60 * 1000); // 30 min to match workflow cadence
    return () => clearInterval(interval);
  }, [channel?.is_streaming]);

  const handleTrigger = async () => {
    if (!channel) return;
    setProcessing(true);
    try {
      const res = await fetch(`${API_URL}/channels/${channel.id}/trigger`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(`Failed: ${err.detail || res.statusText}`);
      }
      await fetchChannel();
    } catch {
      alert('Network error — backend unreachable.');
    } finally {
      setProcessing(false);
    }
  };

  const handleStop = async () => {
    if (!channel || !confirm('Halt broadcast immediately? This will drop the YouTube stream.')) return;
    setProcessing(true);
    try {
      await fetch(`${API_URL}/channels/${channel.id}/stop`, { method: 'POST' });
      await fetchChannel();
    } catch {
      alert('Error stopping stream.');
    } finally {
      setProcessing(false);
    }
  };

  const fetchAds = async () => {
    if (!channel) return;
    try {
      const res = await fetch(`${API_URL}/channels/${channel.id}/ads`);
      setAds(await res.json());
    } catch { /* silent */ }
  };

  const handleCreateAd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!channel) return;
    try {
      await fetch(`${API_URL}/channels/${channel.id}/ads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...newAd, channel_id: channel.id }),
      });
      setNewAd({ name: '', video_url: '', scheduled_hours: '08,12,18,21' });
      fetchAds();
    } catch { alert('Error adding ad.'); }
  };

  const handleDeleteAd = async (adId: number) => {
    try {
      await fetch(`${API_URL}/ads/${adId}`, { method: 'DELETE' });
      fetchAds();
    } catch { /* silent */ }
  };

  const handleUpdateSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsData),
      });
      if (res.ok) { alert('API keys updated!'); setShowSettingsModal(false); }
      else alert('Failed to update keys.');
    } catch { alert('Network error.'); }
  };

  return (
    <div className="min-h-screen bg-[#080b14] text-white font-sans flex flex-col">

      {/* ─── Top Nav ─────────────────────────────────────────────── */}
      <nav className="border-b border-[#1c2035] bg-[#0d1120] px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
            <Activity size={18} className="text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight">VartaPravah</span>
          <span className="text-xs text-blue-400 font-semibold bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-full ml-1">24×7 AI Broadcast</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setShowAdModal(true); fetchAds(); }}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-purple-400 transition px-3 py-2 rounded-lg hover:bg-purple-500/10 border border-transparent hover:border-purple-500/20"
          >
            <Megaphone size={16} /> Ad Scheduler
          </button>
          <button
            onClick={() => setShowSettingsModal(true)}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition px-3 py-2 rounded-lg hover:bg-white/5"
          >
            <Settings size={16} /> API Config
          </button>
        </div>
      </nav>

      {/* ─── Main ────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-12">

        {loading ? (
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500" />
        ) : !channel ? (
          <div className="text-center">
            <div className="text-6xl mb-4">📡</div>
            <p className="text-gray-400 text-lg">Connecting to broadcast system…</p>
            <p className="text-gray-600 text-sm mt-2">Channel will appear automatically once the backend is ready.</p>
          </div>
        ) : (
          <div className="w-full max-w-2xl space-y-6">

            {/* ── Live Status Card ── */}
            <div className={`relative rounded-3xl border p-8 overflow-hidden transition-all duration-500 ${
              channel.is_streaming
                ? 'bg-gradient-to-br from-[#0d1f12] to-[#0f1a1a] border-green-500/30 shadow-2xl shadow-green-500/10'
                : 'bg-[#111623] border-[#1c2035]'
            }`}>

              {/* Glow effect when live */}
              {channel.is_streaming && (
                <div className="absolute inset-0 bg-gradient-to-br from-green-500/5 to-transparent pointer-events-none" />
              )}

              <div className="relative flex items-start justify-between mb-8">
                <div>
                  <h1 className="text-3xl font-bold mb-1">{channel.name}</h1>
                  <p className="text-gray-400 text-sm">Language: <span className="text-blue-400 font-semibold">{channel.language}</span></p>
                </div>
                <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest border ${
                  channel.is_streaming
                    ? 'bg-green-500/15 text-green-400 border-green-500/30'
                    : 'bg-gray-500/10 text-gray-500 border-gray-500/20'
                }`}>
                  <span className={`w-2 h-2 rounded-full ${channel.is_streaming ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
                  {channel.is_streaming ? 'Live on YouTube' : 'Offline'}
                </div>
              </div>

              {/* ── Anchor alternation indicator ── */}
              {channel.is_streaming && (
                <div className="relative grid grid-cols-2 gap-4 mb-8">
                  <div className={`p-4 rounded-2xl border text-center transition-all ${
                    currentAnchor === 'Priya Desai ♀'
                      ? 'bg-pink-500/10 border-pink-500/30'
                      : 'bg-[#0d1120] border-[#1c2035] opacity-50'
                  }`}>
                    <p className="text-2xl mb-1">👩</p>
                    <p className="font-bold text-sm">Priya Desai</p>
                    <p className="text-xs text-gray-500">Female Anchor</p>
                    {currentAnchor === 'Priya Desai ♀' && (
                      <span className="text-xs text-pink-400 font-semibold">● On Air</span>
                    )}
                  </div>
                  <div className={`p-4 rounded-2xl border text-center transition-all ${
                    currentAnchor === 'Arjun Sharma ♂'
                      ? 'bg-blue-500/10 border-blue-500/30'
                      : 'bg-[#0d1120] border-[#1c2035] opacity-50'
                  }`}>
                    <p className="text-2xl mb-1">👨</p>
                    <p className="font-bold text-sm">Arjun Sharma</p>
                    <p className="text-xs text-gray-500">Male Anchor</p>
                    {currentAnchor === 'Arjun Sharma ♂' && (
                      <span className="text-xs text-blue-400 font-semibold">● On Air</span>
                    )}
                  </div>
                </div>
              )}

              {/* ── Stream info ── */}
              <div className="relative grid grid-cols-2 gap-4 mb-8">
                <div className="bg-[#080b14] rounded-2xl border border-[#1c2035] p-4">
                  <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">Stream Key</p>
                  <p className="font-mono text-sm truncate text-gray-300">
                    {channel.youtube_stream_key ? `${channel.youtube_stream_key.slice(0, 8)}••••••` : '⚠️ Not configured'}
                  </p>
                </div>
                <div className="bg-[#080b14] rounded-2xl border border-[#1c2035] p-4">
                  <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">Bulletins Delivered</p>
                  <p className="text-2xl font-bold text-white">{bulletinCount}</p>
                </div>
              </div>

              {/* ── Controls ── */}
              <div className="relative flex gap-3">
                {!channel.is_streaming ? (
                  <button
                    onClick={handleTrigger}
                    disabled={processing}
                    className="flex-1 flex items-center justify-center gap-2 bg-green-500 hover:bg-green-400 disabled:opacity-50 text-black font-bold py-4 rounded-2xl transition-all shadow-lg shadow-green-500/20 text-sm"
                  >
                    <Play fill="currentColor" size={16} />
                    {processing ? 'Connecting…' : 'Go Live Now'}
                  </button>
                ) : (
                  <button
                    onClick={handleStop}
                    disabled={processing}
                    className="flex-1 flex items-center justify-center gap-2 bg-red-500/10 hover:bg-red-500 border border-red-500/30 hover:border-red-500 text-red-400 hover:text-white font-bold py-4 rounded-2xl transition-all text-sm disabled:opacity-50"
                  >
                    <Square fill="currentColor" size={14} />
                    {processing ? 'Stopping…' : 'Stop Broadcast'}
                  </button>
                )}
                <a
                  href="https://studio.youtube.com/channel/live"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 bg-[#1c2035] hover:bg-[#252b45] border border-[#252b45] text-gray-400 hover:text-white font-bold py-4 px-6 rounded-2xl transition-all text-sm"
                >
                  <ExternalLink size={16} /> YouTube Studio
                </a>
              </div>
            </div>

            {/* ── Workflow Monitor link ── */}
            <a
              href="http://localhost:8080"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between bg-[#111623] hover:bg-[#161d2e] border border-[#1c2035] hover:border-blue-500/30 px-6 py-4 rounded-2xl transition-all group"
            >
              <div className="flex items-center gap-3">
                <Activity size={20} className="text-blue-400" />
                <div>
                  <p className="font-bold text-sm">Temporal Workflow Monitor</p>
                  <p className="text-gray-500 text-xs">View live task execution and history</p>
                </div>
              </div>
              <ExternalLink size={16} className="text-gray-600 group-hover:text-blue-400 transition" />
            </a>
          </div>
        )}
      </main>

      {/* ─── Ad Scheduler Modal ──────────────────────────────────── */}
      {showAdModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="bg-[#111623] w-full max-w-2xl p-10 rounded-3xl border border-[#1c2035] shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-8">
              <div>
                <h2 className="text-2xl font-bold mb-1">Ad Scheduler</h2>
                <p className="text-gray-400 text-sm">Schedule commercials to inject between news bulletins.</p>
              </div>
              <button onClick={() => setShowAdModal(false)} className="text-gray-500 hover:text-white text-xl">✕</button>
            </div>

            <form onSubmit={handleCreateAd} className="bg-[#080b14] p-6 rounded-2xl border border-[#1c2035] mb-8 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <input
                  placeholder="Ad name (e.g. Morning Promo)"
                  className="bg-transparent border border-[#1c2035] rounded-xl px-4 py-3 focus:border-blue-500 outline-none text-sm"
                  value={newAd.name}
                  onChange={e => setNewAd({ ...newAd, name: e.target.value })}
                  required
                />
                <input
                  placeholder="Hours (e.g. 09,14,21)"
                  className="bg-transparent border border-[#1c2035] rounded-xl px-4 py-3 focus:border-blue-500 outline-none text-sm"
                  value={newAd.scheduled_hours}
                  onChange={e => setNewAd({ ...newAd, scheduled_hours: e.target.value })}
                  required
                />
              </div>
              <input
                placeholder="Video URL (S3 / direct link)"
                className="w-full bg-transparent border border-[#1c2035] rounded-xl px-4 py-3 focus:border-blue-500 outline-none text-sm"
                value={newAd.video_url}
                onChange={e => setNewAd({ ...newAd, video_url: e.target.value })}
                required
              />
              <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 py-3 rounded-xl font-bold text-sm transition">
                Add to Schedule
              </button>
            </form>

            <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4">Active Campaigns</h3>
            <div className="space-y-3">
              {ads.map(ad => (
                <div key={ad.id} className="flex items-center justify-between bg-[#161d2e] p-5 rounded-2xl border border-[#1c2035]">
                  <div>
                    <p className="font-bold text-sm">{ad.name}</p>
                    <p className="text-xs text-blue-400">{ad.scheduled_hours}:00</p>
                  </div>
                  <button onClick={() => handleDeleteAd(ad.id)} className="text-red-500 hover:bg-red-500/10 p-2 rounded-lg transition">
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
              {ads.length === 0 && (
                <p className="text-center text-gray-600 py-10 text-sm">No ads scheduled yet.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── Settings Modal ───────────────────────────────────────── */}
      {showSettingsModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#111623] w-full max-w-md p-10 rounded-3xl border border-[#1c2035] shadow-2xl">
            <h2 className="text-2xl font-bold mb-1">API Config</h2>
            <p className="text-gray-400 text-sm mb-8">Update backend API keys live.</p>
            <form onSubmit={handleUpdateSettings} className="space-y-5">
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Groq API Key</label>
                <input
                  type="password"
                  value={settingsData.groq_api_key}
                  onChange={e => setSettingsData({ ...settingsData, groq_api_key: e.target.value })}
                  className="w-full bg-[#080b14] border border-[#1c2035] rounded-xl px-5 py-4 focus:outline-none focus:border-blue-500 transition text-sm"
                  placeholder="gsk_..."
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">World News API Key</label>
                <input
                  type="password"
                  value={settingsData.world_news_api_key}
                  onChange={e => setSettingsData({ ...settingsData, world_news_api_key: e.target.value })}
                  className="w-full bg-[#080b14] border border-[#1c2035] rounded-xl px-5 py-4 focus:outline-none focus:border-blue-500 transition text-sm"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowSettingsModal(false)} className="flex-1 py-4 rounded-xl font-bold text-sm border border-[#1c2035] hover:bg-[#1c2035] transition">
                  Cancel
                </button>
                <button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-500 py-4 rounded-xl font-bold text-sm transition shadow-lg shadow-blue-500/20">
                  Save Keys
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
