import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Clock3,
  Eye,
  FilePenLine,
  LoaderCircle
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { MarkdownContent } from "../components/MarkdownContent";
import { TierBadge } from "../components/TierBadge";
import { api } from "../lib/api";
import { coverFor, formatDate, readTime } from "../lib/content";

export function AdminArticlePreviewPage() {
  const { slug } = useParams();
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api(`/api/v1/content/admin/articles/${slug}`)
      .then((data) => active && setArticle(data))
      .catch((requestError) => active && setError(requestError.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [slug]);

  if (loading) {
    return (
      <div className="grid min-h-[70vh] place-items-center">
        <LoaderCircle className="animate-spin text-green-600" />
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-24 text-center">
        <h1 className="font-display text-3xl font-semibold">Preview unavailable</h1>
        <p className="mt-3 text-neutral-600">{error || "This article could not be loaded."}</p>
        <Link to="/admin/articles" className="mt-6 inline-flex h-10 items-center rounded-md bg-ink px-4 text-sm font-semibold text-white">
          Return to articles
        </Link>
      </div>
    );
  }

  return (
    <article>
      <div className="border-b border-sun bg-[#fff9e8]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm sm:px-6 lg:px-8">
          <p className="font-semibold text-ink">
            Admin preview · {article.is_published ? "Published" : "Draft"}
          </p>
          <div className="flex items-center gap-2">
            <Link
              to="/admin/articles"
              className="inline-flex h-9 items-center gap-2 rounded-md border border-neutral-300 bg-white px-3 font-semibold text-neutral-700"
            >
              <ArrowLeft size={16} />
              Articles
            </Link>
            <Link
              to={`/admin/articles/${article.slug}/edit`}
              className="inline-flex h-9 items-center gap-2 rounded-md bg-ink px-3 font-semibold text-white"
            >
              <FilePenLine size={16} />
              Edit
            </Link>
          </div>
        </div>
      </div>

      <header className="mx-auto max-w-5xl px-4 py-10 text-center sm:px-6 lg:py-14">
        <TierBadge tier={article.tier} />
        {article.category && (
          <p className="mt-4 text-xs font-semibold uppercase text-green-700">{article.category}</p>
        )}
        <h1 className="mx-auto mt-4 max-w-4xl font-display text-4xl font-semibold leading-tight text-ink sm:text-6xl">
          {article.title}
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-neutral-600">{article.summary}</p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-4 text-sm text-neutral-500">
          <span className="font-semibold text-neutral-700">By {article.author}</span>
          <span>{article.published_at ? formatDate(article.published_at) : "Not published"}</span>
          <span className="inline-flex items-center gap-1.5"><Clock3 size={16} />{readTime(article)} min read</span>
          <span className="inline-flex items-center gap-1.5"><Eye size={16} />{article.view_count} views</span>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <img
          src={coverFor(article)}
          alt={article.cover_image_alt || ""}
          width="1280"
          height="800"
          className="aspect-[16/10] w-full rounded-lg border border-neutral-200 object-cover shadow-soft"
        />
      </div>

      <div className="mx-auto max-w-[720px] px-4 py-12 sm:px-6 lg:py-16">
        <MarkdownContent>{article.body}</MarkdownContent>
      </div>
    </article>
  );
}
