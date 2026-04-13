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
            className={`py-1.5 rounded-lg text-xs font-bold transition-all border ${selected.has(h)
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
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  const [showAdModal, setShowAdModal] = useState(false);
  const [ads, setAds] = useState<AdCampaign[]>([]);
  const [adTab, setAdTab] = useState<'upload' | 'url'>('upload');
  const [newAd, setNewAd] = useState({ name: '', video_url: '', scheduled_hours: '08,12,18,21' });
  const [uploadState, setUploadState] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle');
  const [uploadedFile, setUploadedFile] = useState<{ filename: string; size_mb: number } | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [settingsData, setSettingsData] = useState({ groq_api_key: '', world_news_api_key: '', youtube_stream_key: '' });

  const fetchChannel = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/channels`);
      const data: Channel[] = await res.json();
      setChannels(data);
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

  const handleTrigger = async (channelId: number) => {
    setProcessing(true);
    try {
      const res = await fetch(`${API_URL}/channels/${channelId}/trigger`, { method: 'POST' });
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

  const handleStop = async (channelId: number) => {
    if (!confirm('Halt broadcast immediately? This will drop the YouTube stream.')) return;
    setProcessing(true);
    try {
      await fetch(`${API_URL}/channels/${channelId}/stop`, { method: 'POST' });
      await fetchChannel();
    } catch {
      alert('Error stopping stream.');
    } finally {
      setProcessing(false);
    }
  };

  const fetchAds = async (channelId: number) => {
    try {
      const res = await fetch(`${API_URL}/channels/${channelId}/ads`);
      setAds(await res.json());
    } catch { /* silent */ }
  };

  const uploadFile = async (file: File) => {
    setUploadState('uploading');
    setUploadProgress(0);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const progressInterval = setInterval(() => {
        setUploadProgress(p => Math.min(p + 10, 85));
      }, 200);
      const res = await fetch(`${API_URL}/ads/upload-video`, { method: 'POST', body: formData });
      clearInterval(progressInterval);
      setUploadProgress(100);
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      setNewAd(prev => ({ ...prev, video_url: data.video_url }));
      setUploadedFile({ filename: data.filename, size_mb: data.size_mb });
      setUploadState('done');
    } catch (e: any) {
      setUploadState('error');
      alert(`Upload error: ${e.message}`);
    }
  };

  const handleCreateAd = async (channelId: number) => {
    if (!newAd.video_url) { alert('Please upload a video first.'); return; }
    try {
      await fetch(`${API_URL}/channels/${channelId}/ads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...newAd, channel_id: channelId }),
      });
      setNewAd({ name: '', video_url: '', scheduled_hours: '08,12,18,21' });
      setUploadState('idle');
      fetchAds(channelId);
    } catch { alert('Error adding ad.'); }
  };

  const handleUpdateSettings = async (channelId: number) => {
    try {
      await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ groq_api_key: settingsData.groq_api_key, world_news_api_key: settingsData.world_news_api_key }),
      });
      await fetch(`${API_URL}/channels/${channelId}/stream-key`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stream_key: settingsData.youtube_stream_key }),
      });
      alert('Settings updated!');
      setShowSettingsModal(false);
      fetchChannel();
    } catch { alert('Error updating settings.'); }
  };

  return (
    <div className="min-h-screen bg-[#080b14] text-white font-sans flex flex-col">
      <nav className="border-b border-[#1c2035] bg-[#0d1120] px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
            <Activity size={18} className="text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight">VartaPravah</span>
          <span className="text-xs text-blue-400 font-semibold bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-full ml-1">Multi-Channel AI</span>
        </div>
      </nav>

      <main className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        {loading ? (
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500" />
        ) : channels.length === 0 ? (
          <div className="text-center">
            <div className="text-6xl mb-4">📡</div>
            <p className="text-gray-400 text-lg">Initializing Broadcast System…</p>
          </div>
        ) : (
          <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-2 gap-8">
            {channels.map(channel => (
              <div key={channel.id} className={`relative rounded-3xl border p-8 transition-all duration-500 ${channel.is_streaming ? 'bg-gradient-to-br from-[#0d1f12] to-[#0f1a1a] border-green-500/30 shadow-2xl' : 'bg-[#111623] border-[#1c2035]'
                }`}>
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h2 className="text-2xl font-bold">{channel.name}</h2>
                    <p className="text-gray-500 text-xs">ID: {channel.id} · Marathi</p>
                  </div>
                  <div className={`px-3 py-1.5 rounded-full text-[10px] font-bold uppercase border ${channel.is_streaming ? 'bg-green-500/15 text-green-400 border-green-500/30' : 'bg-gray-500/10 text-gray-500 border-gray-500/20'
                    }`}>
                    {channel.is_streaming ? '● Live' : 'Offline'}
                  </div>
                </div>

                <div className="bg-[#080b14] rounded-2xl border border-[#1c2035] p-4 mb-6">
                  <p className="text-gray-500 text-[10px] uppercase mb-1">YouTube Stream Key</p>
                  <p className="font-mono text-xs truncate text-gray-400">{channel.youtube_stream_key || 'Not Set'}</p>
                </div>

                <div className="flex gap-3">
                  {!channel.is_streaming ? (
                    <button onClick={() => handleTrigger(channel.id)} disabled={processing} className="flex-1 bg-green-500 hover:bg-green-400 text-black font-bold py-3 rounded-xl text-xs transition">
                      Start Broadcast
                    </button>
                  ) : (
                    <button onClick={() => handleStop(channel.id)} disabled={processing} className="flex-1 bg-red-500/10 border border-red-500/30 text-red-400 font-bold py-3 rounded-xl text-xs hover:bg-red-500 hover:text-white transition">
                      Stop
                    </button>
                  )}
                  <button onClick={() => { setSettingsData({ ...settingsData, youtube_stream_key: channel.youtube_stream_key }); setShowSettingsModal(true); }} className="p-3 bg-white/5 rounded-xl hover:bg-white/10 transition">
                    <Settings size={18} className="text-gray-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {showSettingsModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="bg-[#111623] w-full max-w-sm p-8 rounded-3xl border border-[#1c2035]">
            <h2 className="text-xl font-bold mb-6 text-center">Update Channel Key</h2>
            <div className="space-y-4">
              <input
                type="text"
                value={settingsData.youtube_stream_key}
                onChange={e => setSettingsData({ ...settingsData, youtube_stream_key: e.target.value })}
                className="w-full bg-[#080b14] border border-[#1c2035] rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none"
                placeholder="Stream Key..."
              />
              <div className="flex gap-3 pt-2">
                <button onClick={() => setShowSettingsModal(false)} className="flex-1 py-3 text-sm font-bold bg-white/5 rounded-xl">Cancel</button>
                <button onClick={() => handleUpdateSettings(channels[0].id)} className="flex-1 py-3 text-sm font-bold bg-blue-600 rounded-xl">Save</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
