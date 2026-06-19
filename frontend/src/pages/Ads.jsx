import React, { useState, useEffect } from "react";
import api from "../api";
import { DollarSign, PlusCircle, List, Trash2, Video, AlertCircle, PlayCircle } from "lucide-react";

export default function Ads() {
  const [ads, setAds] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const fetchAds = () => {
    api.get("/api/ads")
      .then((res) => {
        if (res.data && res.data.status === "success") {
          setAds(res.data.ads);
        }
      })
      .catch((err) => {
        console.error("Error fetching ads:", err);
      });
  };

  useEffect(() => {
    fetchAds();
    // Refresh list every 30 seconds to keep the active slot badge synchronized
    const interval = setInterval(fetchAds, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.name.endsWith(".mp4")) {
        setErrorMsg("Only MP4 files (.mp4) are allowed");
        setSelectedFile(null);
        return;
      }
      setErrorMsg("");
      setSelectedFile(file);
    }
  };

  const uploadAd = () => {
    if (!selectedFile) {
      setErrorMsg("Please select a valid MP4 video file first");
      return;
    }

    setUploading(true);
    setMessage("Uploading advertisement...");
    setErrorMsg("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    api.post("/api/ads/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    })
      .then((res) => {
        setUploading(false);
        if (res.data && res.data.status === "success") {
          setMessage("Advertisement uploaded successfully!");
          setSelectedFile(null);
          // Reset file input value
          const fileInput = document.getElementById("ad-file-input");
          if (fileInput) fileInput.value = "";
          fetchAds();
        } else {
          setErrorMsg(res.data.message || "Failed to upload advertisement");
          setMessage("");
        }
      })
      .catch((err) => {
        setUploading(false);
        setErrorMsg("Network error occurred during upload");
        setMessage("");
        console.error("Upload error:", err);
      });
  };

  const deleteAd = (filename) => {
    if (!window.confirm(`Are you sure you want to delete ${filename}?`)) {
      return;
    }

    api.delete(`/api/ads/${filename}`)
      .then((res) => {
        if (res.data && res.data.status === "success") {
          fetchAds();
        } else {
          alert(res.data.message || "Failed to delete ad");
        }
      })
      .catch((err) => {
        console.error("Delete error:", err);
        alert("Failed to connect to the server to delete");
      });
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
            Upload Commercial (MP4)
          </h3>
          <div className="space-y-4">
            <div className="flex flex-col gap-2">
              <input
                id="ad-file-input"
                type="file"
                accept="video/mp4"
                onChange={handleFileChange}
                disabled={uploading}
                className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-brand-accent file:mr-4 file:py-1 file:px-3 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-white/10 file:text-slate-300 hover:file:bg-white/20 file:cursor-pointer"
              />
              {selectedFile && (
                <span className="text-xs text-slate-400 font-mono">
                  Size: {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                </span>
              )}
            </div>

            {errorMsg && (
              <div className="flex items-center gap-2 text-xs text-rose-500 bg-rose-500/10 p-3 rounded-lg">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {message && (
              <div className="flex items-center gap-2 text-xs text-emerald-500 bg-emerald-500/10 p-3 rounded-lg">
                <PlayCircle className="w-4 h-4 shrink-0" />
                <span>{message}</span>
              </div>
            )}

            <button 
              onClick={uploadAd}
              disabled={uploading || !selectedFile}
              className={`w-full py-3 rounded-xl font-bold transition-all shadow-lg ${
                uploading || !selectedFile
                  ? "bg-slate-700/50 text-slate-400 cursor-not-allowed shadow-none"
                  : "bg-brand-accent hover:bg-sky-500 text-white shadow-brand-accent/20"
              }`}
            >
              {uploading ? "UPLOADING..." : "UPLOAD AD FILE"}
            </button>
          </div>
        </div>

        <div className="glass-card space-y-6 bg-brand-accent/5">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-brand-success" />
            Ad Settings & Info
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b border-white/5">
              <span className="text-slate-400">Total Uploaded Ads</span>
              <span className="font-mono font-bold">{ads.length}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-white/5">
              <span className="text-slate-400">Playout Cadence</span>
              <span className="font-mono font-bold">Rotated Every 15m</span>
            </div>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Ads are streamed sequentially, one-by-one, in 15-minute intervals. If no ads are uploaded, the playout system automatically falls back to your master standby advertisement.
            </p>
          </div>
        </div>
      </div>

      <div className="glass-card">
        <h3 className="text-lg font-bold flex items-center gap-2 mb-6">
          <List className="w-5 h-5 text-brand-accent" />
          Campaign Asset Inventory
        </h3>
        <div className="overflow-hidden rounded-xl border border-white/5">
          <table className="w-full text-left">
            <thead className="bg-white/5">
              <tr>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Asset Name</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">File Size</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {ads.length === 0 ? (
                <tr>
                  <td colSpan="4" className="px-6 py-8 text-center text-slate-500 text-sm">
                    No custom campaign assets uploaded. Playout is currently using default standby assets.
                  </td>
                </tr>
              ) : (
                ads.map((ad) => (
                  <tr key={ad.filename}>
                    <td className="px-6 py-4 font-mono text-xs flex items-center gap-2 text-white">
                      <Video className="w-4 h-4 text-slate-400 shrink-0" />
                      {ad.filename}
                    </td>
                    <td className="px-6 py-4 text-slate-400 text-sm font-mono">{ad.size_mb} MB</td>
                    <td className="px-6 py-4">
                      {ad.is_active ? (
                        <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-black border border-emerald-500/30 flex items-center gap-1 w-max animate-pulse">
                          ● BROADCASTING
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded-full bg-slate-500/10 text-slate-400 text-[10px] font-bold border border-white/5 flex items-center gap-1 w-max">
                          QUEUED
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => deleteAd(ad.filename)}
                        className="p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 hover:text-rose-500 transition-all"
                        title="Delete asset"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
