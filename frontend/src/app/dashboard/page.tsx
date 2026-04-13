"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Square, Play, Settings, ExternalLink, ShieldCheck } from 'lucide-react';

const API_URL = '/api';

interface Channel {
  id: number;
  name: string;
  language: string;
  youtube_stream_key: string;
  is_streaming: boolean;
  active_anchor?: string;
}

export default function DashboardPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'status' | 'settings'>('status');
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [streamKey, setStreamKey] = useState("");

  const fetchChannel = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/channels`);
      const data: Channel[] = await res.json();
      setChannels(data);
    } catch (err) {
      console.error('API Error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchChannel();
    const interval = setInterval(fetchChannel, 5000);
    return () => clearInterval(interval);
  }, [fetchChannel]);

  const handleStart = async (channelId: number) => {
    try {
      await fetch(`${API_URL}/channels/${channelId}/trigger`, { method: 'POST' });
      fetchChannel();
    } catch {
      alert('Network error — backend unreachable.');
    }
  };

  const handleStop = async (channelId: number) => {
    if (!confirm('Halt broadcast immediately?')) return;
    try {
      await fetch(`${API_URL}/channels/${channelId}/stop`, { method: 'POST' });
      fetchChannel();
    } catch {
      alert('Control error.');
    }
  };

  const updateStreamKey = async () => {
    if (!channels[0]) return;
    try {
      await fetch(`${API_URL}/channels/${channels[0].id}/stream-key`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stream_key: streamKey }),
      });
      setShowKeyModal(false);
      fetchChannel();
    } catch {
      alert('Failed to save key.');
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-[#05070a] flex items-center justify-center">
      <div className="animate-pulse text-blue-500 font-bold tracking-widest">BOOTING VARTA PRAVAH...</div>
    </div>
  );

  const channel = channels[0] || { id: 1, name: "Varta Pravah Live", language: "Marathi", is_streaming: false, youtube_stream_key: "" };

  return (
    <div className="min-h-screen bg-[#05070a] text-[#e2e8f0] font-sans selection:bg-green-500/30">
      {/* Header Overlay */}
      <div className="max-w-4xl mx-auto pt-20 px-6">
        <div className="flex justify-between items-end mb-12">
          <div>
            <h1 className="text-5xl font-black tracking-tighter text-white mb-2">VARTA PRAVAH</h1>
            <p className="text-blue-400 font-bold text-sm tracking-wide">Language: <span className="text-white">Marathi</span></p>
          </div>
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full border transition-all duration-700 ${channel.is_streaming ? 'bg-green-500/10 border-green-500/40 text-green-400 shadow-[0_0_20px_rgba(34,197,94,0.2)]' : 'bg-red-500/5 border-red-500/20 text-red-500/50'}`}>
            <div className={`w-2 h-2 rounded-full ${channel.is_streaming ? 'bg-green-500 animate-pulse' : 'bg-red-500 opacity-20'}`} />
            <span className="text-[10px] font-black uppercase tracking-widest">{channel.is_streaming ? 'Live on YouTube' : 'Station Offline'}</span>
          </div>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Female Anchor Selection */}
          <div className={`group relative rounded-[2.5rem] border p-8 transition-all duration-500 ${channel.is_streaming ? 'bg-[#0a120d] border-green-500/20 shadow-2xl' : 'bg-[#0d1117] border-white/5 shadow-xl'}`}>
            <div className="flex flex-col items-center text-center">
              <div className="text-4xl mb-4 grayscale group-hover:grayscale-0 transition-all duration-500">👩🏼</div>
              <h3 className="text-xl font-bold text-white mb-1">Priya Desai</h3>
              <p className="text-gray-500 text-xs font-medium mb-4">Female Anchor</p>
              {channel.is_streaming && (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-pink-500/10 text-pink-500 text-[10px] font-black uppercase tracking-widest border border-pink-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-pink-500" />
                  On Air
                </div>
              )}
            </div>
          </div>

          {/* Male Anchor Selection */}
          <div className="group relative rounded-[2.5rem] bg-[#0d1117] border border-white/5 p-8 transition-all duration-500 opacity-40">
            <div className="flex flex-col items-center text-center">
              <div className="text-4xl mb-4 grayscale">🧔🏼</div>
              <h3 className="text-xl font-bold text-white mb-1">Arjun Sharma</h3>
              <p className="text-gray-500 text-xs font-medium">Male Anchor</p>
              <div className="mt-4 text-[10px] font-bold text-gray-600 uppercase">Standby</div>
            </div>
          </div>

          {/* Stream Key Info */}
          <div className="rounded-3xl bg-[#090b10] border border-white/5 p-6 flex flex-col justify-between">
            <p className="text-[10px] uppercase font-bold text-gray-500 tracking-widest mb-2">Stream Key</p>
            <div className="flex items-center justify-between">
              <code className="text-sm font-mono text-blue-400 truncate max-w-[150px]">
                {channel.youtube_stream_key ? `${channel.youtube_stream_key.substring(0, 8)}••••••` : "NOT_CONFIGURED"}
              </code>
              <button onClick={() => { setStreamKey(channel.youtube_stream_key); setShowKeyModal(true); }} className="p-2 hover:bg-white/5 rounded-full transition">
                <Settings size={14} className="text-gray-500" />
              </button>
            </div>
          </div>

          {/* Activity Metrics */}
          <div className="rounded-3xl bg-[#090b10] border border-white/5 p-6 flex flex-col justify-between">
            <p className="text-[10px] uppercase font-bold text-gray-500 tracking-widest mb-2">Bulletins Delivered</p>
            <div className="text-3xl font-black text-white">0</div>
          </div>
        </div>

        {/* Global Controls */}
        <div className="flex gap-4">
          {!channel.is_streaming ? (
            <button 
              onClick={() => handleStart(channel.id)}
              className="flex-1 group relative overflow-hidden bg-white text-black font-black py-5 rounded-[2rem] text-sm uppercase tracking-tighter active:scale-95 transition-all"
            >
              <div className="absolute inset-0 bg-green-500 translate-y-full group-hover:translate-y-0 transition-transform duration-500" />
              <span className="relative z-10 flex items-center justify-center gap-2 group-hover:text-white transition-colors">
                <Play fill="currentColor" size={16} />
                Start 24/7 Broadcast
              </span>
            </button>
          ) : (
            <button 
              onClick={() => handleStop(channel.id)}
              className="flex-1 bg-red-500/10 border border-red-500/30 text-red-500 font-black py-5 rounded-[2rem] text-sm uppercase tracking-tighter hover:bg-red-500 hover:text-white transition-all flex items-center justify-center gap-2"
            >
              <Square fill="currentColor" size={16} />
              Stop Broadcast
            </button>
          )}
          
          <a 
            href="https://studio.youtube.com" 
            target="_blank" 
            className="px-8 bg-[#161920] border border-white/5 rounded-[2rem] flex items-center justify-center hover:bg-[#1c212a] transition-all"
          >
            <ExternalLink size={18} className="text-blue-400" />
            <span className="ml-3 font-bold text-xs">YouTube Studio</span>
          </a>
        </div>
      </div>

      {/* Stream Key Modal */}
      {showKeyModal && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-2xl flex items-center justify-center z-50 p-6 animate-in fade-in zoom-in duration-300">
          <div className="bg-[#0d1117] border border-white/10 w-full max-w-sm rounded-[3rem] p-10">
            <h2 className="text-2xl font-black text-white mb-2 text-center">Broadcast Key</h2>
            <p className="text-gray-500 text-xs text-center mb-8">Updating this will affect the next broadcast cycle.</p>
            <input 
              type="text" 
              value={streamKey}
              onChange={(e) => setStreamKey(e.target.value)}
              className="w-full bg-black border border-white/10 rounded-2xl px-6 py-4 text-sm font-mono text-green-400 focus:outline-none focus:border-blue-500 transition-all mb-6"
              placeholder="qcu7-xe..."
            />
            <div className="flex gap-3">
              <button onClick={() => setShowKeyModal(false)} className="flex-1 py-4 text-xs font-black uppercase text-gray-500 hover:text-white">Cancel</button>
              <button onClick={updateStreamKey} className="flex-1 py-4 text-xs font-black uppercase bg-blue-600 text-white rounded-2xl shadow-xl shadow-blue-600/20">Save Key</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
