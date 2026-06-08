import { ArrowUpRight, Clock3, Eye } from "lucide-react";
import { Link } from "react-router-dom";
import { coverFor, formatDate, readTime } from "../lib/content";
import { TierBadge } from "./TierBadge";

export function ArticleCard({ article, featured = false }) {
  return (
    <article
      className={`lift overflow-hidden rounded-lg border border-neutral-200 bg-white ${
        featured ? "grid min-h-[360px] md:grid-cols-[1.2fr_1fr]" : ""
      }`}
    >
      <Link
        to={`/articles/${article.slug}`}
        className={`block overflow-hidden bg-neutral-100 ${featured ? "min-h-64" : "aspect-[16/10]"}`}
      >
        <img
          src={coverFor(article)}
          alt=""
          loading={featured ? "eager" : "lazy"}
          width="1280"
          height="800"
          className="h-full w-full object-cover"
        />
      </Link>
      <div className={`flex flex-col ${featured ? "p-6 sm:p-8" : "p-5"}`}>
        <div className="flex items-center justify-between gap-3">
          <TierBadge tier={article.tier} compact />
          <span className="text-xs text-neutral-500">{formatDate(article.published_at)}</span>
        </div>
        <Link to={`/articles/${article.slug}`} className="group mt-4">
          <h2
            className={`font-display font-semibold leading-tight text-ink group-hover:text-green-700 ${
              featured ? "text-3xl sm:text-4xl" : "text-2xl"
            }`}
          >
            {article.title}
          </h2>
        </Link>
        <p className={`mt-3 leading-6 text-neutral-600 ${featured ? "line-clamp-3" : "line-clamp-2 text-sm"}`}>
          {article.summary}
        </p>
        <div className="mt-auto flex items-center justify-between gap-4 pt-6 text-xs text-neutral-500">
          <span className="font-semibold text-neutral-700">By {article.author}</span>
          <span className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1"><Clock3 size={14} />{readTime(article)} min</span>
            <span className="inline-flex items-center gap-1"><Eye size={14} />{article.view_count}</span>
            <ArrowUpRight size={16} className="text-green-600" />
          </span>
        </div>
      </div>
    </article>
  );
}
