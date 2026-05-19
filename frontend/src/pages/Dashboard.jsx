import React, { useEffect, useState } from "react";
import api from "../api";
import { Play, Activity, Clock, Layout } from "lucide-react"; // I'll add lucide-react too

export default function Dashboard() {
  const [nowPlaying, setNowPlaying] = useState("Determining status...");
  const [stats, setStats] = useState({ generated: 0, errors: 0 });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get("/next");
        setNowPlaying(res.data.file || "Promo Loop (Fallback)");
      } catch (err) {
        setNowPlaying("Disconnected from backend");
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-black bg-clip-text text-transparent bg-gradient-to-r from-brand-accent to-white tracking-tight">
            VartaPravah Master
          </h1>
          <p className="text-slate-400 mt-1">Autonomous Hindi News Engine</p>
        </div>
        <div className="flex items-center gap-3 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-emerald-400 font-medium text-sm animate-pulse">
          <div className="w-2 h-2 rounded-full bg-emerald-400" />
          SYSTEM LIVE
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card flex flex-col justify-between">
          <div className="flex justify-between">
            <span className="text-slate-400 font-medium">News Bulletins</span>
            <Activity className="text-brand-accent w-5 h-5" />
          </div>
          <div className="mt-4 text-4xl font-bold">{stats.generated}</div>
          <p className="text-xs text-slate-500 mt-2">Generated today</p>
        </div>

        <div className="glass-card flex flex-col justify-between">
          <div className="flex justify-between">
            <span className="text-slate-400 font-medium">Uptime</span>
            <Clock className="text-brand-success w-5 h-5" />
          </div>
          <div className="mt-4 text-4xl font-bold">24/7</div>
          <p className="text-xs text-slate-500 mt-2">Active broadcast</p>
        </div>

        <div className="glass-card flex flex-col justify-between">
          <div className="flex justify-between">
            <span className="text-slate-400 font-medium">Critical Errors</span>
            <Layout className="text-brand-danger w-5 h-5" />
          </div>
          <div className="mt-4 text-4xl font-bold text-brand-danger">{stats.errors}</div>
          <p className="text-xs text-slate-500 mt-2">Requires attention</p>
        </div>
      </div>

      <div className="glass-card relative overflow-hidden group">
        <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:scale-110 transition-transform">
          <Play className="w-32 h-32" />
        </div>
        <h2 className="text-xl font-bold flex items-center gap-2 mb-4">
          <Play className="w-5 h-5 text-brand-accent fill-brand-accent" />
          Now On Air
        </h2>
        <div className="bg-black/40 rounded-xl p-6 border border-white/5">
          <p className="font-mono text-brand-accent text-lg truncate">
            {nowPlaying}
          </p>
          <div className="mt-4 flex gap-2">
            <span className="px-2 py-1 bg-white/5 rounded text-[10px] font-bold text-slate-500">RTMP STREAM</span>
            <span className="px-2 py-1 bg-white/5 rounded text-[10px] font-bold text-slate-500">2500 KBPS</span>
            <span className="px-2 py-1 bg-white/5 rounded text-[10px] font-bold text-slate-500">720P @ 24FPS</span>
          </div>
        </div>
      </div>
    </div>
  );
}
