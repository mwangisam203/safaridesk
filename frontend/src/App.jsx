import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { AdminRoute } from "./components/AdminRoute";
import { AdminArticleEditorPage } from "./pages/AdminArticleEditorPage";
import { AdminArticlesPage } from "./pages/AdminArticlesPage";
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
        <Route
          path="/admin/articles"
          element={<AdminRoute><AdminArticlesPage /></AdminRoute>}
        />
        <Route
          path="/admin/articles/new"
          element={<AdminRoute><AdminArticleEditorPage /></AdminRoute>}
        />
        <Route
          path="/admin/articles/:slug/edit"
          element={<AdminRoute><AdminArticleEditorPage /></AdminRoute>}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
