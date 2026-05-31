import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import AnalyzePage from "./pages/AnalyzePage";
import ReportPage from "./pages/ReportPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/reports/:runId" element={<ReportPage />} />
      </Routes>
    </Layout>
  );
}
