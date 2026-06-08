import { useEffect, useMemo, useState } from "react";
import { BookOpenCheck, LoaderCircle, SearchX, Sparkles } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { ArticleCard } from "../components/ArticleCard";
import { TierBadge } from "../components/TierBadge";
import { api } from "../lib/api";
import { matchesTopic, topicFilters } from "../lib/content";

export function LibraryPage() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q")?.trim() || "";
  const [articles, setArticles] = useState([]);
  const [topic, setTopic] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    api(query ? `/api/v1/content/articles/search?q=${encodeURIComponent(query)}` : "/api/v1/content/articles")
      .then((data) => active && setArticles(data))
      .catch((requestError) => {
        if (!active) return;
        if (requestError.status === 404) setArticles([]);
        else setError(requestError.message);
      })
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [query]);

  const filtered = useMemo(
    () => articles.filter((article) => matchesTopic(article, topic)),
    [articles, topic]
  );
  const featured = filtered[0];
  const rest = filtered.slice(1);

  return (
    <>
      <section className="border-b border-neutral-200 bg-white">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[1fr_auto] lg:px-8 lg:py-12">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase text-green-600">
              <Sparkles size={15} />
              Technical knowledge for working developers
            </div>
            <h1 className="mt-3 max-w-3xl font-display text-4xl font-semibold leading-tight text-ink sm:text-5xl">
              Build dependable backend systems, one practical guide at a time.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-neutral-600">
              Deep guides on APIs, databases, payments, background jobs, testing, and production.
            </p>
          </div>
          <div className="flex min-w-60 items-center gap-4 self-end border-l-4 border-coral bg-paper px-5 py-4">
            <BookOpenCheck size={27} className="text-coral" />
            <div>
              <p className="font-display text-2xl font-semibold text-ink">{articles.length}</p>
              <p className="text-sm text-neutral-500">published guides</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 border-b border-neutral-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase text-neutral-500">
              {query ? `Search results for "${query}"` : "Browse the library"}
            </p>
            <h2 className="mt-1 font-display text-3xl font-semibold text-ink">
              {query ? `${filtered.length} matching articles` : "Latest field notes"}
            </h2>
          </div>
          <div className="flex max-w-full gap-2 overflow-x-auto pb-1">
            {topicFilters.map((filter) => (
              <button
                key={filter.id}
                type="button"
                onClick={() => setTopic(filter.id)}
                className={`h-9 shrink-0 rounded-md border px-3 text-sm font-semibold ${
                  topic === filter.id
                    ? "border-ink bg-ink text-white"
                    : "border-neutral-300 bg-white text-neutral-600 hover:border-green-500"
                }`}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>

        {loading && (
          <div className="grid min-h-80 place-items-center">
            <LoaderCircle className="animate-spin text-green-600" size={30} />
          </div>
        )}

        {error && (
          <div className="mt-8 rounded-md border border-red-200 bg-red-50 p-5 text-red-700">
            <p className="font-semibold">The library could not be loaded.</p>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        {!loading && !error && !featured && (
          <div className="grid min-h-80 place-items-center text-center">
            <div>
              <SearchX size={36} className="mx-auto text-neutral-400" />
              <h3 className="mt-3 font-display text-2xl font-semibold">No articles found</h3>
              <p className="mt-2 text-sm text-neutral-500">Try another search or topic filter.</p>
            </div>
          </div>
        )}

        {!loading && featured && (
          <div className="mt-7">
            <ArticleCard article={featured} featured />
            {rest.length > 0 && (
              <div className="mt-7 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {rest.map((article) => (
                  <ArticleCard key={article.id} article={article} />
                ))}
              </div>
            )}
          </div>
        )}

        <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-y border-neutral-200 py-5">
          <div className="flex items-center gap-3">
            <TierBadge tier="basic" />
            <p className="text-sm text-neutral-600">Unlimited BASIC reading for subscribers.</p>
          </div>
          <div className="flex items-center gap-3">
            <TierBadge tier="pro" />
            <p className="text-sm text-neutral-600">Advanced production and fintech guides.</p>
          </div>
        </div>
      </section>
    </>
  );
}
