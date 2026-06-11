import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Clock3,
  Eye,
  LoaderCircle,
  LockKeyhole,
  Mail,
  UserRoundPlus
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { TierBadge } from "../components/TierBadge";
import { MarkdownContent } from "../components/MarkdownContent";
import { api } from "../lib/api";
import { coverFor, formatDate, readTime } from "../lib/content";

export function ArticlePage() {
  const { slug } = useParams();
  const [article, setArticle] = useState(null);
  const [gate, setGate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api(`/api/v1/content/articles/${slug}`)
      .then((data) => active && setArticle(data))
      .catch((requestError) => {
        if (!active) return;
        const detail = requestError.data?.detail;
        if (requestError.status === 403 && typeof detail === "object") setGate(detail);
        else setError(requestError.message);
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [slug]);

  useEffect(() => {
    if (!article) return undefined;
    const previousTitle = document.title;
    const description = document.querySelector('meta[name="description"]');
    const previousDescription = description?.getAttribute("content");
    document.title = article.seo_title || `${article.title} | SafariDesk`;
    if (description && (article.seo_description || article.summary)) {
      description.setAttribute("content", article.seo_description || article.summary);
    }
    return () => {
      document.title = previousTitle;
      if (description && previousDescription !== null) {
        description.setAttribute("content", previousDescription);
      }
    };
  }, [article]);

  if (loading) {
    return <div className="grid min-h-[70vh] place-items-center"><LoaderCircle className="animate-spin text-green-600" /></div>;
  }

  if (gate) return <ReaderGate gate={gate} />;

  if (error || !article) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-24 text-center">
        <h1 className="font-display text-3xl font-semibold">Article unavailable</h1>
        <p className="mt-3 text-neutral-600">{error || "This article could not be loaded."}</p>
        <Link to="/" className="mt-6 inline-flex h-10 items-center rounded-md bg-ink px-4 text-sm font-semibold text-white">
          Return to library
        </Link>
      </div>
    );
  }

  return (
    <article>
      <div className="mx-auto max-w-7xl px-4 pt-7 sm:px-6 lg:px-8">
        <Link to="/" className="inline-flex items-center gap-2 text-sm font-semibold text-neutral-500 hover:text-green-700">
          <ArrowLeft size={17} /> Back to library
        </Link>
      </div>

      <header className="mx-auto max-w-5xl px-4 py-10 text-center sm:px-6 lg:py-14">
        <TierBadge tier={article.tier} />
        <h1 className="mx-auto mt-5 max-w-4xl font-display text-4xl font-semibold leading-tight text-ink sm:text-6xl">
          {article.title}
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-neutral-600">{article.summary}</p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-4 text-sm text-neutral-500">
          <span className="font-semibold text-neutral-700">By {article.author}</span>
          <span>{formatDate(article.published_at)}</span>
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

      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[minmax(0,720px)_220px] lg:py-16">
        <MarkdownContent>{article.body}</MarkdownContent>
        <aside className="self-start border-l-2 border-green-500 pl-5 lg:sticky lg:top-24">
          <p className="text-xs font-semibold uppercase text-green-700">Field note</p>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            Save the patterns that matter, then adapt them to your own system. Reliable software is built by understanding tradeoffs, not copying snippets.
          </p>
          <Link to="/plans" className="mt-4 inline-flex text-sm font-semibold text-green-700">
            Explore subscription plans
          </Link>
        </aside>
      </div>
    </article>
  );
}

function ReaderGate({ gate }) {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const isSoftWall = gate.action === "soft_wall";
  const Icon = isSoftWall ? Mail : gate.action === "register" ? UserRoundPlus : LockKeyhole;

  async function submitEmail(event) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await api("/api/v1/content/email-capture", {
        method: "POST",
        body: JSON.stringify({ email })
      });
      setMessage(result.message);
      window.setTimeout(() => window.location.reload(), 800);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto grid min-h-[72vh] max-w-3xl place-items-center px-4 py-16">
      <div className="w-full border-y border-neutral-300 bg-white px-5 py-12 text-center sm:px-12">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-green-50 text-green-700">
          <Icon size={26} />
        </span>
        <p className="mt-5 text-xs font-semibold uppercase text-green-700">Continue reading</p>
        <h1 className="mt-2 font-display text-4xl font-semibold text-ink">
          {isSoftWall ? "One quick step" : gate.action === "register" ? "Create your free account" : "Unlock this guide"}
        </h1>
        <p className="mx-auto mt-4 max-w-lg leading-7 text-neutral-600">{gate.message}</p>

        {isSoftWall ? (
          <form onSubmit={submitEmail} className="mx-auto mt-7 flex max-w-md flex-col gap-2 sm:flex-row">
            <input
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              className="h-11 min-w-0 flex-1 rounded-md border border-neutral-300 px-3 outline-none focus:border-green-500"
            />
            <button disabled={busy} className="h-11 rounded-md bg-ink px-5 text-sm font-semibold text-white">
              {busy ? "Sending..." : "Keep reading"}
            </button>
          </form>
        ) : (
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <Link to="/plans" className="inline-flex h-11 items-center rounded-md bg-ink px-5 text-sm font-semibold text-white">
              View plans
            </Link>
            <Link to="/" className="inline-flex h-11 items-center rounded-md border border-neutral-300 bg-white px-5 text-sm font-semibold text-ink">
              Browse free articles
            </Link>
          </div>
        )}
        {message && <p className="mt-4 text-sm text-green-700">{message}</p>}
      </div>
    </div>
  );
}
