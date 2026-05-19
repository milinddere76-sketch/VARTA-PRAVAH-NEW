import React, { useState } from "react";
import api from "../api";
import { DollarSign, PlusCircle, List } from "lucide-react";

export default function Ads() {
  const [file, setFile] = useState("");

  const uploadAd = () => {
    api.post("/upload-ad", { file });
    alert("Ad queued for upload");
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h2 className="text-3xl font-black">Monetization & Ads</h2>
        <p className="text-slate-400">Manage commercial breaks and sponsored segments</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="glass-card space-y-6">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <PlusCircle className="w-5 h-5 text-brand-accent" />
            Add Commercial
          </h3>
          <div className="space-y-4">
            <input
              type="text"
              placeholder="Ad Video Path"
              onChange={(e) => setFile(e.target.value)}
              className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-brand-accent"
            />
            <button 
              onClick={uploadAd}
              className="w-full py-3 rounded-xl bg-brand-accent hover:bg-sky-500 text-white font-bold transition-all shadow-lg shadow-brand-accent/20"
            >
              QUEUE FOR UPLOAD
            </button>
          </div>
        </div>

        <div className="glass-card space-y-6 bg-brand-accent/5">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-brand-success" />
            Ad Analytics
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b border-white/5">
              <span className="text-slate-400">Total Ads Played</span>
              <span className="font-mono font-bold">142</span>
            </div>
            <div className="flex justify-between py-2 border-b border-white/5">
              <span className="text-slate-400">Avg. Frequency</span>
              <span className="font-mono font-bold">Every 15m</span>
            </div>
          </div>
        </div>
      </div>

      <div className="glass-card">
        <h3 className="text-lg font-bold flex items-center gap-2 mb-6">
          <List className="w-5 h-5 text-brand-accent" />
          Active Campaign Assets
        </h3>
        <div className="overflow-hidden rounded-xl border border-white/5">
          <table className="w-full text-left">
            <thead className="bg-white/5">
              <tr>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Asset Name</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Duration</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              <tr>
                <td className="px-6 py-4 font-mono text-xs">promo_summer_sale.mp4</td>
                <td className="px-6 py-4"><span className="px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-bold">ACTIVE</span></td>
                <td className="px-6 py-4 text-slate-400 text-sm">30s</td>
              </tr>
              <tr>
                <td className="px-6 py-4 font-mono text-xs">govt_awareness_hindi.mp4</td>
                <td className="px-6 py-4"><span className="px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-bold">ACTIVE</span></td>
                <td className="px-6 py-4 text-slate-400 text-sm">45s</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
