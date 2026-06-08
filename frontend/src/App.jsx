import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { AccountPage } from "./pages/AccountPage";
import { ArticlePage } from "./pages/ArticlePage";
import { LibraryPage } from "./pages/LibraryPage";
import { PlansPage } from "./pages/PlansPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<LibraryPage />} />
        <Route path="/articles/:slug" element={<ArticlePage />} />
        <Route path="/plans" element={<PlansPage />} />
        <Route path="/account" element={<AccountPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
