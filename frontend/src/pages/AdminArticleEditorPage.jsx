import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Check,
  Eye,
  ImageUp,
  LoaderCircle,
  Save,
  Send
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { MarkdownContent } from "../components/MarkdownContent";
import { TierBadge } from "../components/TierBadge";
import { api } from "../lib/api";
import { coverFor } from "../lib/content";

const emptyArticle = {
  title: "",
  slug: "",
  summary: "",
  body: "",
  category: "",
  cover_image_url: "",
  cover_image_alt: "",
  seo_title: "",
  seo_description: "",
  author: "SafariDesk Team",
  tier: "basic",
  is_featured: false,
  is_published: false
};

export function AdminArticleEditorPage() {
  const { slug } = useParams();
  const isNew = !slug;
  const navigate = useNavigate();
  const [article, setArticle] = useState(emptyArticle);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const slugEdited = useRef(false);

  useEffect(() => {
    if (isNew) return;
    api(`/api/v1/content/admin/articles/${slug}`)
      .then((data) => setArticle(normalizeArticle(data)))
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false));
  }, [isNew, slug]);

  function setField(field, value) {
    setSaved(false);
    setArticle((current) => {
      const next = { ...current, [field]: value };
      if (field === "title" && isNew && !slugEdited.current) {
        next.slug = slugify(value);
      }
      return next;
    });
  }

  async function saveArticle(publish = article.is_published) {
    if (article.cover_image_url && !article.cover_image_alt.trim()) {
      setError("Add meaningful alt text for the cover image before saving.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const payload = {
        title: article.title,
        slug: article.slug,
        summary: article.summary || null,
        body: article.body,
        category: article.category || null,
        cover_image_url: article.cover_image_url || null,
        cover_image_alt: article.cover_image_alt || null,
        seo_title: article.seo_title || null,
        seo_description: article.seo_description || null,
        author: article.author,
        tier: article.tier,
        is_featured: article.is_featured,
        is_published: publish
      };
      const savedArticle = await api(
        isNew
          ? "/api/v1/content/admin/articles"
          : `/api/v1/content/admin/articles/${slug}`,
        {
          method: isNew ? "POST" : "PATCH",
          body: JSON.stringify(payload)
        }
      );
      setArticle(normalizeArticle(savedArticle));
      setSaved(true);
      if (isNew || savedArticle.slug !== slug) {
        navigate(`/admin/articles/${savedArticle.slug}/edit`, { replace: true });
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function uploadCoverImage(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setUploadingImage(true);
    setUploadedImage(null);
    setError("");

    try {
      const formData = new FormData();
      formData.append("image", file);
      const uploaded = await api("/api/v1/content/admin/article-images", {
        method: "POST",
        body: formData
      });
      setField("cover_image_url", uploaded.url);
      setUploadedImage(uploaded);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUploadingImage(false);
    }
  }

  if (loading) {
    return (
      <div className="grid min-h-[70vh] place-items-center">
        <LoaderCircle className="animate-spin text-green-600" />
      </div>
    );
  }

  return (
    <section className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-neutral-200 pb-5">
        <div className="flex items-center gap-3">
          <Link
            to="/admin/articles"
            aria-label="Back to articles"
            title="Back to articles"
            className="grid h-10 w-10 place-items-center rounded-md border border-neutral-300 bg-white text-neutral-600"
          >
            <ArrowLeft size={18} />
          </Link>
          <div>
            <p className="text-xs font-semibold uppercase text-green-700">
              {isNew ? "New draft" : "Editing article"}
            </p>
            <h1 className="font-display text-3xl font-semibold text-ink">
              {article.title || "Untitled article"}
            </h1>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {saved && (
            <span className="inline-flex items-center gap-1 text-sm font-semibold text-green-700">
              <Check size={16} />
              Saved
            </span>
          )}
          <button
            type="button"
            disabled={saving}
            onClick={() => saveArticle(article.is_published)}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-neutral-300 bg-white px-4 text-sm font-semibold text-ink disabled:opacity-50"
          >
            <Save size={17} />
            {article.is_published ? "Save changes" : "Save draft"}
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={() => saveArticle(true)}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-ink px-4 text-sm font-semibold text-white disabled:opacity-50"
          >
            {saving ? <LoaderCircle size={17} className="animate-spin" /> : <Send size={17} />}
            {article.is_published ? "Update published" : "Publish"}
          </button>
        </div>
      </div>

      {error && (
        <p className="mt-4 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div className="space-y-6">
          <EditorSection title="Article">
            <Field label="Title">
              <input value={article.title} onChange={(event) => setField("title", event.target.value)} required />
            </Field>
            <Field label="Slug">
              <input
                value={article.slug}
                onChange={(event) => {
                  slugEdited.current = true;
                  setField("slug", slugify(event.target.value));
                }}
                required
              />
            </Field>
            <Field label="Summary" hint={`${article.summary.length}/500`}>
              <textarea
                rows="3"
                maxLength="500"
                value={article.summary}
                onChange={(event) => setField("summary", event.target.value)}
              />
            </Field>
            <Field label="Body" hint="Markdown">
              <textarea
                rows="20"
                value={article.body}
                onChange={(event) => setField("body", event.target.value)}
                className="font-mono text-sm"
                required
              />
            </Field>
          </EditorSection>

          <EditorSection title="Publishing">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Author">
                <input value={article.author} onChange={(event) => setField("author", event.target.value)} />
              </Field>
              <Field label="Category">
                <input value={article.category} onChange={(event) => setField("category", event.target.value)} />
              </Field>
              <Field label="Access tier">
                <select value={article.tier} onChange={(event) => setField("tier", event.target.value)}>
                  <option value="basic">BASIC</option>
                  <option value="pro">PRO</option>
                </select>
              </Field>
              <label className="flex items-end">
                <span className="flex h-11 w-full items-center gap-3 rounded-md border border-neutral-300 bg-white px-3 text-sm font-semibold text-ink">
                  <input
                    type="checkbox"
                    checked={article.is_featured}
                    onChange={(event) => setField("is_featured", event.target.checked)}
                  />
                  Feature in library
                </span>
              </label>
            </div>
          </EditorSection>

          <EditorSection title="Cover and search">
            <div>
              <input
                id="article-cover-upload"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="sr-only"
                disabled={uploadingImage}
                onChange={uploadCoverImage}
              />
              <label
                htmlFor="article-cover-upload"
                className={`inline-flex h-10 cursor-pointer items-center gap-2 rounded-md border border-neutral-300 bg-white px-4 text-sm font-semibold text-ink ${
                  uploadingImage ? "pointer-events-none opacity-50" : ""
                }`}
              >
                {uploadingImage ? (
                  <LoaderCircle size={17} className="animate-spin" />
                ) : (
                  <ImageUp size={17} />
                )}
                {uploadingImage ? "Optimizing image..." : "Upload cover image"}
              </label>
              <p className="mt-2 text-xs leading-5 text-neutral-500">
                JPEG, PNG, or WebP. Maximum 8 MB. Large images are resized and converted to WebP.
              </p>
              {uploadedImage && (
                <p className="mt-2 text-xs font-medium text-green-700">
                  Uploaded {uploadedImage.width} x {uploadedImage.height} WebP
                </p>
              )}
            </div>
            <Field label="Cover image URL">
              <input
                value={article.cover_image_url}
                placeholder="/covers/example.webp or https://..."
                onChange={(event) => setField("cover_image_url", event.target.value)}
              />
            </Field>
            <Field label="Cover image alt text">
              <input
                value={article.cover_image_alt}
                onChange={(event) => setField("cover_image_alt", event.target.value)}
              />
            </Field>
            <Field label="SEO title">
              <input value={article.seo_title} onChange={(event) => setField("seo_title", event.target.value)} />
            </Field>
            <Field label="SEO description" hint={`${article.seo_description.length}/500`}>
              <textarea
                rows="3"
                maxLength="500"
                value={article.seo_description}
                onChange={(event) => setField("seo_description", event.target.value)}
              />
            </Field>
          </EditorSection>
        </div>

        <aside className="self-start xl:sticky xl:top-24">
          <div className="flex items-center gap-2 border-b border-neutral-200 pb-3 text-sm font-semibold text-neutral-600">
            <Eye size={17} />
            Live preview
          </div>
          <article className="mt-4 overflow-hidden rounded-lg border border-neutral-200 bg-white">
            <img
              src={article.cover_image_url || coverFor(article)}
              alt={article.cover_image_alt}
              className="aspect-[16/10] w-full bg-neutral-100 object-cover"
            />
            <div className="p-6 sm:p-8">
              <TierBadge tier={article.tier} />
              {article.category && (
                <p className="mt-4 text-xs font-semibold uppercase text-green-700">{article.category}</p>
              )}
              <h2 className="mt-4 font-display text-4xl font-semibold leading-tight text-ink">
                {article.title || "Untitled article"}
              </h2>
              <p className="mt-4 leading-7 text-neutral-600">
                {article.summary || "Add a concise summary for the library and search results."}
              </p>
              <div className="mt-8 border-t border-neutral-200 pt-7">
                <MarkdownContent>
                  {article.body || "Start writing the article body in Markdown."}
                </MarkdownContent>
              </div>
            </div>
          </article>
        </aside>
      </div>
    </section>
  );
}

function normalizeArticle(article) {
  return {
    ...emptyArticle,
    ...article,
    summary: article.summary || "",
    category: article.category || "",
    cover_image_url: article.cover_image_url || "",
    cover_image_alt: article.cover_image_alt || "",
    seo_title: article.seo_title || "",
    seo_description: article.seo_description || ""
  };
}

function slugify(value) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function EditorSection({ title, children }) {
  return (
    <section className="border-y border-neutral-200 bg-paper py-5">
      <h2 className="mb-4 text-sm font-semibold text-ink">{title}</h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-center justify-between gap-3 text-sm font-semibold text-neutral-700">
        {label}
        {hint && <span className="text-xs font-normal text-neutral-400">{hint}</span>}
      </span>
      <span className="editor-field block">{children}</span>
    </label>
  );
}
