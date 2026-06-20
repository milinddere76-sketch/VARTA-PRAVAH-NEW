import axios from "axios";

// Dynamically resolve base URL to avoid connection issues on different hosts/IPs
const getBaseURL = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    
    // Check if we are running locally or directly via IP for testing
    const isLocalOrIP = hostname === "localhost" || 
                        hostname === "127.0.0.1" || 
                        /^[0-9.]+$/.test(hostname);
                        
    if (isLocalOrIP) {
      return `${protocol}//${hostname}:8000`;
    }
    
    // In production domain mode, we proxy API and videos relative to the same domain (e.g. /api)
    // via our custom frontend Nginx reverse proxy.
    return "";
  }
  return "http://localhost:8000";
};

const api = axios.create({
  baseURL: getBaseURL(),
});

export default api;
