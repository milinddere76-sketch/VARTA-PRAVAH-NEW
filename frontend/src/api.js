import axios from "axios";

// Dynamically resolve base URL to avoid connection issues on different hosts/IPs
const getBaseURL = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8000`;
  }
  return "http://localhost:8000";
};

const api = axios.create({
  baseURL: getBaseURL(),
});

export default api;
