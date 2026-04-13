"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Square, Play, Settings, ExternalLink } from 'lucide-react';

const API_URL = '/api';

interface Channel {
  id: number;
  name: string;
  language: string;
  youtube_stream_key: string;
  is_streaming: boolean;
}

export default function DashboardPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
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
    const interval = setInterval(fetchChannel, 10000);
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
      <div className="text-blue-500 font-bold tracking-widest">BOOTING VARTA PRAVAH...</div>
    </div>
  );

  const channel = channels[0] || { id: 1, name: "Varta Pravah Live", language: "Marathi", is_streaming: false, youtube_stream_key: "" };

  return (
    <div className="min-h-screen bg-[#05070a] text-[#e2e8f0] font-sans">
      <div className="max-w-4xl mx-auto pt-20 px-6">
        <div className="flex justify-between items-end mb-12">
          <div>
            <h1 className="text-5xl font-black tracking-tighter text-white mb-2 uppercase">Varta Pravah</h1>
            <p className="text-blue-400 font-bold text-sm tracking-wide">Language: <span className="text-white">Marathi</span></p>
          </div>
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full border ${channel.is_streaming ? 'bg-green-500/10 border-green-500/40 text-green-400' : 'bg-red-500/5 border-red-500/20 text-red-500/50'}`}>
            <div className={`w-2 h-2 rounded-full ${channel.is_streaming ? 'bg-green-500' : 'bg-red-500 opacity-20'}`} />
            <span className="text-[10px] font-black uppercase tracking-widest">{channel.is_streaming ? 'Live on YouTube' : 'Station Offline'}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className={`rounded-3xl border p-8 transition-all duration-500 ${channel.is_streaming ? 'bg-[#0a120d] border-green-500/20' : 'bg-[#0d1117] border-white/5'}`}>
            <div className="flex flex-col items-center text-center">
              <div className="text-4xl mb-4">👩🏼</div>
              <h3 className="text-xl font-bold text-white mb-1">Priya Desai</h3>
              <p className="text-gray-500 text-xs font-medium mb-4">Female Anchor</p>
              {channel.is_streaming && (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-pink-500/10 text-pink-500 text-[10px] font-black uppercase tracking-widest border border-pink-500/20">
                  On Air
                </div>
              )}
            </div>
          </div>

          <div className="rounded-3xl bg-[#0d1117] border border-white/5 p-8 opacity-40">
            <div className="flex flex-col items-center text-center">
              <div className="text-4xl mb-4">🧔🏼</div>
              <h3 className="text-xl font-bold text-white mb-1">Arjun Sharma</h3>
              <p className="text-gray-500 text-xs font-medium">Male Anchor</p>
              <div className="mt-4 text-[10px] font-bold text-gray-600 uppercase">Standby</div>
            </div>
          </div>

          <div className="rounded-3xl bg-[#090b10] border border-white/5 p-6 flex flex-col justify-between">
            <p className="text-[10px] uppercase font-bold text-gray-500 tracking-widest mb-2">Stream Key</p>
            <div className="flex items-center justify-between">
              <code className="text-sm font-mono text-blue-400 truncate max-w-[150px]">
                {channel.youtube_stream_key ? `${channel.youtube_stream_key.substring(0, 8)}••••••` : "NOT_CONFIGURED"}
              </code>
              <button onClick={() => { setStreamKey(channel.youtube_stream_key); setShowKeyModal(true); }} className="p-2 hover:bg-white/5 rounded-full">
                <Settings size={14} className="text-gray-500" />
              </button>
            </div>
          </div>

          <div className="rounded-3xl bg-[#090b10] border border-white/5 p-6 flex flex-col justify-between">
            <p className="text-[10px] uppercase font-bold text-gray-500 tracking-widest mb-2">Bulletins Delivered</p>
            <div className="text-3xl font-black text-white">0</div>
          </div>
        </div>

        <div className="flex gap-4">
          {!channel.is_streaming ? (
            <button 
              onClick={() => handleStart(channel.id)}
              className="flex-1 bg-white text-black font-black py-5 rounded-3xl text-sm uppercase tracking-tighter hover:bg-green-500 hover:text-white transition-all flex items-center justify-center gap-2"
            >
              <Play fill="currentColor" size={16} />
              Start 24/7 Broadcast
            </button>
          ) : (
            <button 
              onClick={() => handleStop(channel.id)}
              className="flex-1 bg-red-500/10 border border-red-500/30 text-red-500 font-black py-5 rounded-3xl text-sm uppercase tracking-tighter hover:bg-red-500 hover:text-white transition-all flex items-center justify-center gap-2"
            >
              <Square fill="currentColor" size={16} />
              Stop Broadcast
            </button>
          )}
          
          <a 
            href="https://studio.youtube.com" 
            target="_blank" 
            rel="noreferrer"
            className="px-8 bg-[#161920] border border-white/5 rounded-3xl flex items-center justify-center hover:bg-[#1c212a] transition-all"
          >
            <ExternalLink size={18} className="text-blue-400" />
            <span className="ml-3 font-bold text-xs">YouTube Studio</span>
          </a>
        </div>
      </div>

      {showKeyModal && (
        <div className="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-6">
          <div className="bg-[#0d1117] border border-white/10 w-full max-w-sm rounded-3xl p-10">
            <h2 className="text-2xl font-black text-white mb-2 text-center">Broadcast Key</h2>
            <p className="text-gray-500 text-xs text-center mb-8">Update the channel stream key.</p>
            <input 
              type="text" 
              value={streamKey}
              onChange={(e) => setStreamKey(e.target.value)}
              className="w-full bg-black border border-white/10 rounded-2xl px-6 py-4 text-sm font-mono text-green-400 mb-6"
              placeholder="qcu7-xe..."
            />
            <div className="flex gap-3">
              <button onClick={() => setShowKeyModal(false)} className="flex-1 py-4 text-xs font-black uppercase text-gray-500">Cancel</button>
              <button onClick={updateStreamKey} className="flex-1 py-4 text-xs font-black uppercase bg-blue-600 text-white rounded-2xl">Save Key</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
