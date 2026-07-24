import React from "react";
import ReactDOM from "react-dom/client";
import SilverApp from "./pages/SilverApp";
import PlatinumPalladiumApp from "./pages/PlatinumPalladiumApp";
import MonitoringApp from "./pages/MonitoringApp";
import "./styles.css";

const page = document.documentElement.dataset.dashboardPage;
const App = page === "platinum-palladium"
  ? PlatinumPalladiumApp
  : page === "monitoring"
    ? MonitoringApp
    : SilverApp;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
