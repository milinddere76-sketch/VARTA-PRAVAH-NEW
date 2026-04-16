"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Activity, ExternalLink, Square, Play, Settings, Megaphone, Trash2, Upload, Link, CheckCircle, Clock } from 'lucide-react';

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

const ALL_HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));

function HourPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const selected = new Set(value.split(',').map(h => h.trim().padStart(2, '0')).filter(Boolean));

  const toggle = (h: string) => {
    const next = new Set(selected);
    next.has(h) ? next.delete(h) : next.add(h);
    onChange([...next].sort().join(','));
  };

  return (
    <div>
      <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Schedule Hours (IST)</p>
      <div className="grid grid-cols-8 gap-1.5">
        {ALL_HOURS.map(h => (
          <button
            key={h}
            type="button"
            onClick={() => toggle(h)}
            className={`py-1.5 rounded-lg text-xs font-bold transition-all border ${
              selected.has(h)
                ? 'bg-purple-600 border-purple-500 text-white shadow-lg shadow-purple-500/20'
                : 'bg-[#0d1120] border-[#1c2035] text-gray-500 hover:border-purple-500/40 hover:text-gray-300'
            }`}
          >
            {h}
          </button>
        ))}
      </div>
      {selected.size > 0 && (
        <p className="text-xs text-purple-400 mt-2">
          ✓ Runs at: {[...selected].sort().map(h => `${h}:00`).join(' · ')}
        </p>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const [channel, setChannel]       = useState<Channel | null>(null);
  const [loading, setLoading]       = useState(true);
  const [processing, setProcessing] = useState(false);

  const [showAdModal, setShowAdModal]   = useState(false);
  const [ads, setAds]                   = useState<AdCampaign[]>([]);
  const [adTab, setAdTab]               = useState<'upload' | 'url'>('upload');
  const [newAd, setNewAd]               = useState({ name: '', video_url: '', scheduled_hours: '08,12,18,21' });
  const [uploadState, setUploadState]   = useState<'idle' | 'uploading' | 'done' | 'error'>('idle');
  const [uploadedFile, setUploadedFile] = useState<{ filename: string; size_mb: number } | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragOver, setIsDragOver]     = useState(false);
  const fileInputRef                    = useRef<HTMLInputElement>(null);

  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [settingsData, setSettingsData] = useState({ groq_api_key: '', world_news_api_key: '', youtube_stream_key: '' });

  const [bulletinCount, setBulletinCount] = useState(0);
  const [currentAnchor, setCurrentAnchor] = useState<'Priya Desai ♀' | 'Arjun Sharma ♂'>('Priya Desai ♀');

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
    const interval = setInterval(fetchChannel, 15_000);
    return () => clearInterval(interval);
  }, [fetchChannel]);

  useEffect(() => {
    if (!channel?.is_streaming) return;
    const interval = setInterval(() => {
      setBulletinCount(n => n + 1);
      setCurrentAnchor(n => n === 'Priya Desai ♀' ? 'Arjun Sharma ♂' : 'Priya Desai ♀');
    }, 30 * 60 * 1000);
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

  const handleRegeneratePromo = async () => {
    if (!confirm('Regenerate high-fidelity promo video? This takes ~20s.')) return;
    setProcessing(true);
    try {
      const res = await fetch(`${API_URL}/system/regenerate-promo`, { method: 'POST' });
      if (res.ok) alert('✨ Premium promo regenerated!');
      else alert('Failed to regenerate promo.');
    } catch {
      alert('Network error.');
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

  // ── File upload handler ────────────────────────────────────────────
  const uploadFile = async (file: File) => {
    setUploadState('uploading');
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Simulate progress (XHR would give real progress; fetch doesn't)
      const progressInterval = setInterval(() => {
        setUploadProgress(p => Math.min(p + 10, 85));
      }, 200);

      const res = await fetch(`${API_URL}/ads/upload-video`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Upload failed');
      }

      const data = await res.json();
      setNewAd(prev => ({ ...prev, video_url: data.video_url }));
      setUploadedFile({ filename: data.filename, size_mb: data.size_mb });
      setUploadState('done');
    } catch (e: unknown) {
      setUploadState('error');
      alert(`Upload error: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
  };

  const resetUpload = () => {
    setUploadState('idle');
    setUploadedFile(null);
    setUploadProgress(0);
    setNewAd(prev => ({ ...prev, video_url: '' }));
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleCreateAd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!channel) return;
    if (!newAd.video_url) { alert('Please upload a video or paste a URL first.'); return; }
    if (!newAd.scheduled_hours) { alert('Please select at least one broadcast hour.'); return; }
    try {
      await fetch(`${API_URL}/channels/${channel.id}/ads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...newAd, channel_id: channel.id }),
      });
      setNewAd({ name: '', video_url: '', scheduled_hours: '08,12,18,21' });
      resetUpload();
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
    if (!channel) return;
    try {
      // 1. Update Env Keys
      const resEnv = await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          groq_api_key: settingsData.groq_api_key, 
          world_news_api_key: settingsData.world_news_api_key 
        }),
      });

      // 2. Update Stream Key in DB
      const resKey = await fetch(`${API_URL}/channels/${channel.id}/stream-key`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ youtube_stream_key: settingsData.youtube_stream_key }),
      });

      if (resEnv.ok && resKey.ok) { 
        alert('Settings & Stream Key updated!'); 
        setShowSettingsModal(false); 
        fetchChannel();
      } else {
        alert('Partial success or failure. Check logs.');
      }
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
            onClick={handleRegeneratePromo}
            disabled={processing}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-blue-400 transition px-3 py-2 rounded-lg hover:bg-blue-500/10 border border-transparent hover:border-blue-500/20"
          >
            <Activity size={16} /> {processing ? 'Generating...' : 'Refresh Assets'}
          </button>
          <button
            onClick={() => {
              setSettingsData({
                groq_api_key: '', 
                world_news_api_key: '', 
                youtube_stream_key: channel?.youtube_stream_key || ''
              });
              setShowSettingsModal(true);
            }}
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

              <div className="relative grid grid-cols-2 gap-4 mb-8">
                <div className="bg-[#080b14] rounded-2xl border border-[#1c2035] p-4 group relative">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-gray-500 text-xs uppercase tracking-wider">Stream Key</p>
                    <button 
                      onClick={() => {
                        setSettingsData(prev => ({ ...prev, youtube_stream_key: channel.youtube_stream_key || '' }));
                        setShowSettingsModal(true);
                      }}
                      className="text-[10px] text-blue-400 hover:text-blue-300 transition font-bold"
                    >
                      EDIT
                    </button>
                  </div>
                  <p className="font-mono text-sm truncate text-gray-300">
                    {channel.youtube_stream_key ? `${channel.youtube_stream_key.slice(0, 8)}••••••` : '⚠️ Not configured'}
                  </p>
                </div>
                <div className="bg-[#080b14] rounded-2xl border border-[#1c2035] p-4">
                  <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">Bulletins Delivered</p>
                  <p className="text-2xl font-bold text-white">{bulletinCount}</p>
                </div>
              </div>

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
            <button
              onClick={() => {
                const host = window.location.hostname;
                window.open(`http://${host}:8088`, '_blank');
              }}
              className="w-full flex items-center justify-between bg-[#111623] hover:bg-[#161d2e] border border-[#1c2035] hover:border-blue-500/30 px-6 py-4 rounded-2xl transition-all group"
            >
              <div className="flex items-center gap-3">
                <Activity size={20} className="text-blue-400" />
                <div>
                  <p className="font-bold text-sm">Temporal Workflow Monitor</p>
                  <p className="text-gray-500 text-xs">View live task execution and history</p>
                </div>
              </div>
              <ExternalLink size={16} className="text-gray-600 group-hover:text-blue-400 transition" />
            </button>
          </div>
        )}
      </main>

      {/* ─── Ad Scheduler Modal ──────────────────────────────────── */}
      {showAdModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="bg-[#111623] w-full max-w-2xl rounded-3xl border border-[#1c2035] shadow-2xl max-h-[92vh] overflow-y-auto">

            {/* Modal header */}
            <div className="flex justify-between items-start p-8 pb-0">
              <div>
                <h2 className="text-2xl font-bold mb-1 flex items-center gap-2">
                  <Megaphone size={22} className="text-purple-400" /> Ad Scheduler
                </h2>
                <p className="text-gray-400 text-sm">Upload commercials and set when they broadcast.</p>
              </div>
              <button onClick={() => setShowAdModal(false)} className="text-gray-500 hover:text-white text-xl p-1">✕</button>
            </div>

            {/* Add new ad form */}
            <form onSubmit={handleCreateAd} className="p-8 space-y-5">

              {/* Ad name */}
              <input
                placeholder="Campaign name (e.g. Morning Promo)"
                className="w-full bg-[#080b14] border border-[#1c2035] rounded-xl px-4 py-3 focus:border-purple-500 outline-none text-sm transition"
                value={newAd.name}
                onChange={e => setNewAd({ ...newAd, name: e.target.value })}
                required
              />

              {/* Source tabs */}
              <div>
                <div className="flex gap-1 mb-4 bg-[#080b14] p-1 rounded-xl border border-[#1c2035]">
                  <button
                    type="button"
                    onClick={() => { setAdTab('upload'); resetUpload(); }}
                    className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                      adTab === 'upload'
                        ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
                        : 'text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    <Upload size={15} /> Upload Video File
                  </button>
                  <button
                    type="button"
                    onClick={() => { setAdTab('url'); resetUpload(); }}
                    className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                      adTab === 'url'
                        ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
                        : 'text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    <Link size={15} /> Paste URL
                  </button>
                </div>

                {adTab === 'upload' ? (
                  <div>
                    {uploadState === 'idle' && (
                      <div
                        onDragOver={e => { e.preventDefault(); setIsDragOver(true); }}
                        onDragLeave={() => setIsDragOver(false)}
                        onDrop={handleFileDrop}
                        onClick={() => fileInputRef.current?.click()}
                        className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all ${
                          isDragOver
                            ? 'border-purple-500 bg-purple-500/10'
                            : 'border-[#1c2035] hover:border-purple-500/40 hover:bg-purple-500/5'
                        }`}
                      >
                        <Upload size={32} className="mx-auto mb-3 text-gray-500" />
                        <p className="font-semibold text-sm text-gray-300">Drag & drop your video here</p>
                        <p className="text-xs text-gray-600 mt-1">or click to browse · MP4, MOV, AVI, WebM</p>
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept="video/*"
                          className="hidden"
                          onChange={handleFileSelect}
                        />
                      </div>
                    )}

                    {uploadState === 'uploading' && (
                      <div className="border border-[#1c2035] rounded-2xl p-6 text-center">
                        <p className="text-sm text-gray-400 mb-3">Uploading to server…</p>
                        <div className="w-full bg-[#080b14] rounded-full h-2 overflow-hidden">
                          <div
                            className="h-2 bg-purple-600 rounded-full transition-all duration-300"
                            style={{ width: `${uploadProgress}%` }}
                          />
                        </div>
                        <p className="text-xs text-purple-400 mt-2">{uploadProgress}%</p>
                      </div>
                    )}

                    {uploadState === 'done' && uploadedFile && (
                      <div className="flex items-center justify-between bg-green-500/10 border border-green-500/30 rounded-2xl px-5 py-4">
                        <div className="flex items-center gap-3">
                          <CheckCircle size={20} className="text-green-400 shrink-0" />
                          <div>
                            <p className="text-sm font-semibold text-green-300">{uploadedFile.filename}</p>
                            <p className="text-xs text-gray-500">{uploadedFile.size_mb} MB · Ready to schedule</p>
                          </div>
                        </div>
                        <button type="button" onClick={resetUpload} className="text-gray-500 hover:text-white text-sm transition">
                          ✕
                        </button>
                      </div>
                    )}

                    {uploadState === 'error' && (
                      <div className="border border-red-500/30 rounded-2xl p-4 text-center">
                        <p className="text-sm text-red-400">Upload failed. <button type="button" onClick={resetUpload} className="underline">Try again</button></p>
                      </div>
                    )}
                  </div>
                ) : (
                  <input
                    placeholder="https://… or /app/videos/my-ad.mp4"
                    className="w-full bg-[#080b14] border border-[#1c2035] rounded-xl px-4 py-3 focus:border-purple-500 outline-none text-sm transition"
                    value={newAd.video_url}
                    onChange={e => setNewAd({ ...newAd, video_url: e.target.value })}
                  />
                )}
              </div>

              {/* Hour picker */}
              <div className="bg-[#080b14] border border-[#1c2035] rounded-2xl p-5">
                <HourPicker
                  value={newAd.scheduled_hours}
                  onChange={v => setNewAd({ ...newAd, scheduled_hours: v })}
                />
              </div>

              <button
                type="submit"
                disabled={uploadState === 'uploading'}
                className="w-full bg-purple-600 hover:bg-purple-500 disabled:opacity-50 py-3.5 rounded-xl font-bold text-sm transition shadow-lg shadow-purple-500/20"
              >
                Add to Schedule
              </button>
            </form>

            {/* Divider */}
            <div className="px-8 pb-3">
              <p className="text-xs font-bold uppercase tracking-widest text-gray-500 flex items-center gap-2">
                <Clock size={12} /> Active Campaigns
              </p>
            </div>

            {/* Existing ads */}
            <div className="px-8 pb-8 space-y-3">
              {ads.map(ad => (
                <div key={ad.id} className="bg-[#161d2e] border border-[#1c2035] rounded-2xl p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="font-bold text-sm">{ad.name}</p>
                      <p className="text-xs text-gray-500 truncate mt-0.5 max-w-xs">{ad.video_url}</p>
                    </div>
                    <button
                      onClick={() => handleDeleteAd(ad.id)}
                      className="text-red-500/60 hover:text-red-400 hover:bg-red-500/10 p-2 rounded-lg transition"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {ad.scheduled_hours.split(',').filter(Boolean).map(h => (
                      <span
                        key={h}
                        className="px-2.5 py-1 rounded-lg bg-purple-600/20 border border-purple-500/30 text-purple-300 text-xs font-bold"
                      >
                        {h.padStart(2,'0')}:00
                      </span>
                    ))}
                  </div>
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
              <div className="h-px bg-[#1c2035] my-6" />
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">YouTube Stream Key</label>
                <div className="relative">
                  <input
                    type="password"
                    value={settingsData.youtube_stream_key}
                    onChange={e => setSettingsData({ ...settingsData, youtube_stream_key: e.target.value })}
                    className="w-full bg-[#080b14] border border-[#1c2035] rounded-xl px-5 py-4 focus:outline-none focus:border-red-500/50 transition text-sm font-mono"
                    placeholder="qcu7-..."
                  />
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2 pointer-events-none">
                    <span className="text-[10px] bg-red-500/10 text-red-500 px-2 py-1 rounded border border-red-500/20 font-bold">RTMP</span>
                  </div>
                </div>
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
