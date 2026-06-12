import { useEffect, useMemo, useState } from "react";
import {
  Eye,
  FilePenLine,
  FileText,
  LoaderCircle,
  Plus,
  Send,
  Trash2
} from "lucide-react";
import { Link } from "react-router-dom";
import { TierBadge } from "../components/TierBadge";
import { api } from "../lib/api";
import { formatDate } from "../lib/content";

export function AdminArticlesPage() {
  const [articles, setArticles] = useState([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busySlug, setBusySlug] = useState("");

  async function loadArticles() {
    setLoading(true);
    setError("");
    try {
      setArticles(await api("/api/v1/content/admin/articles"));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadArticles();
  }, []);

  const visibleArticles = useMemo(() => {
    if (filter === "published") return articles.filter((article) => article.is_published);
    if (filter === "draft") return articles.filter((article) => !article.is_published);
    return articles;
  }, [articles, filter]);

  async function togglePublished(article) {
    setBusySlug(article.slug);
    try {
      await api(`/api/v1/content/admin/articles/${article.slug}`, {
        method: "PATCH",
        body: JSON.stringify({ is_published: !article.is_published })
      });
      await loadArticles();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusySlug("");
    }
  }

  async function removeArticle(article) {
    if (!window.confirm(`Delete "${article.title}" permanently?`)) return;
    setBusySlug(article.slug);
    try {
      await api(`/api/v1/content/admin/articles/${article.slug}`, {
        method: "DELETE"
      });
      setArticles((current) => current.filter((item) => item.slug !== article.slug));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusySlug("");
    }
  }

  return (
    <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-5 border-b border-neutral-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-green-700">Editorial workspace</p>
          <h1 className="mt-1 font-display text-4xl font-semibold text-ink">Articles</h1>
          <p className="mt-2 text-sm text-neutral-600">
            Draft, preview, and publish SafariDesk guides.
          </p>
        </div>
        <Link
          to="/admin/articles/new"
          className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-ink px-4 text-sm font-semibold text-white hover:bg-green-700"
        >
          <Plus size={18} />
          New article
        </Link>
      </div>

      <div className="flex gap-2 border-b border-neutral-200 py-5">
        {["all", "draft", "published"].map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setFilter(option)}
            className={`h-9 rounded-md border px-3 text-sm font-semibold capitalize ${
              filter === option
                ? "border-ink bg-ink text-white"
                : "border-neutral-300 bg-white text-neutral-600"
            }`}
          >
            {option}
          </button>
        ))}
      </div>

      {error && (
        <p className="mt-5 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </p>
      )}

      {loading ? (
        <div className="grid min-h-72 place-items-center">
          <LoaderCircle className="animate-spin text-green-600" />
        </div>
      ) : (
        <div className="mt-5 overflow-x-auto border-y border-neutral-200 bg-white">
          <table className="w-full min-w-[1040px] border-collapse text-left">
            <thead className="bg-paper text-xs uppercase text-neutral-500">
              <tr>
                <th className="px-4 py-3 font-semibold">Article</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Tier</th>
                <th className="px-4 py-3 font-semibold">Author</th>
                <th className="px-4 py-3 text-right font-semibold">Views</th>
                <th className="px-4 py-3 font-semibold">Updated</th>
                <th className="px-4 py-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {visibleArticles.map((article) => (
                <tr key={article.id} className="border-t border-neutral-200">
                  <td className="max-w-md px-4 py-4">
                    <p className="font-semibold text-ink">{article.title}</p>
                    <p className="mt-1 truncate text-xs text-neutral-500">/{article.slug}</p>
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge published={article.is_published} />
                  </td>
                  <td className="px-4 py-4">
                    <TierBadge tier={article.tier} compact />
                  </td>
                  <td className="px-4 py-4 text-sm text-neutral-600">{article.author}</td>
                  <td className="px-4 py-4 text-right text-sm tabular-nums text-neutral-600">
                    {article.view_count}
                  </td>
                  <td className="px-4 py-4 text-sm text-neutral-500">
                    {formatDate(article.updated_at || article.created_at)}
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex justify-end gap-1">
                      <IconLink
                        to={`/admin/articles/${article.slug}/preview`}
                        label="Preview article"
                      >
                        <Eye size={17} />
                      </IconLink>
                      <IconLink to={`/admin/articles/${article.slug}/edit`} label="Edit article">
                        <FilePenLine size={17} />
                      </IconLink>
                      <IconButton
                        label={article.is_published ? "Unpublish article" : "Publish article"}
                        disabled={busySlug === article.slug}
                        onClick={() => togglePublished(article)}
                      >
                        {article.is_published ? <FileText size={17} /> : <Send size={17} />}
                      </IconButton>
                      <IconButton
                        label="Delete article"
                        disabled={busySlug === article.slug}
                        onClick={() => removeArticle(article)}
                        danger
                      >
                        <Trash2 size={17} />
                      </IconButton>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {visibleArticles.length === 0 && (
            <p className="px-4 py-16 text-center text-sm text-neutral-500">
              No articles match this view.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function StatusBadge({ published }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${
        published
          ? "border-green-100 bg-green-50 text-green-700"
          : "border-neutral-300 bg-neutral-100 text-neutral-600"
      }`}
    >
      {published ? "Published" : "Draft"}
    </span>
  );
}

function IconLink({ to, label, children }) {
  return (
    <Link
      to={to}
      title={label}
      aria-label={label}
      className="grid h-9 w-9 place-items-center rounded-md border border-neutral-300 text-neutral-600 hover:border-green-500 hover:text-green-700"
    >
      {children}
    </Link>
  );
}

function IconButton({ label, onClick, disabled, danger = false, children }) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className={`grid h-9 w-9 place-items-center rounded-md border disabled:opacity-50 ${
        danger
          ? "border-red-200 text-red-600 hover:bg-red-50"
          : "border-neutral-300 text-neutral-600 hover:border-green-500 hover:text-green-700"
      }`}
    >
      {children}
    </button>
  );
}
