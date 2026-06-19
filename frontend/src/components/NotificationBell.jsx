import { useEffect, useState } from "react";
import { Bell, CheckCheck, LoaderCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

export function NotificationBell({ compact = false }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  async function loadNotifications() {
    setLoading(true);
    setError("");
    try {
      const result = await api("/api/v1/notifications?limit=10");
      setNotifications(result.notifications || []);
      setUnreadCount(result.unread_count || 0);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadNotifications();
  }, []);

  async function toggleOpen() {
    const nextOpen = !open;
    setOpen(nextOpen);
    if (nextOpen) await loadNotifications();
  }

  async function markOneRead(notificationId) {
    try {
      const updated = await api(`/api/v1/notifications/${notificationId}/read`, {
        method: "PATCH"
      });
      setNotifications((current) =>
        current.map((item) => (item.id === notificationId ? updated : item))
      );
      setUnreadCount((current) => Math.max(0, current - 1));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function markAllRead() {
    try {
      await api("/api/v1/notifications/mark-all-read", { method: "POST" });
      setNotifications((current) =>
        current.map((item) => ({
          ...item,
          read_at: item.read_at || new Date().toISOString()
        }))
      );
      setUnreadCount(0);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={toggleOpen}
        className={`relative grid place-items-center rounded-md border border-neutral-300 bg-white text-ink hover:border-green-400 hover:text-green-700 ${
          compact ? "h-11 w-full" : "h-10 w-10"
        }`}
        aria-label="Open notifications"
        title="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-red-600 px-1 text-[11px] font-bold leading-none text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-lg border border-neutral-200 bg-white shadow-soft">
          <div className="flex items-center justify-between border-b border-neutral-100 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-ink">Notifications</p>
              <p className="text-xs text-neutral-500">{unreadCount} unread</p>
            </div>
            <button
              type="button"
              onClick={markAllRead}
              disabled={unreadCount === 0}
              className="inline-flex h-8 items-center gap-1 rounded-md px-2 text-xs font-semibold text-green-700 hover:bg-green-50 disabled:text-neutral-300"
            >
              <CheckCheck size={14} />
              Read all
            </button>
          </div>

          <div className="max-h-96 overflow-y-auto p-2">
            {loading && (
              <div className="grid min-h-28 place-items-center text-neutral-400">
                <LoaderCircle className="animate-spin" />
              </div>
            )}

            {!loading && error && (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">
                {error}
              </p>
            )}

            {!loading && !error && notifications.length === 0 && (
              <p className="px-3 py-8 text-center text-sm text-neutral-500">
                Nothing important right now.
              </p>
            )}

            {!loading && !error && notifications.map((item) => (
              <NotificationItem
                key={item.id}
                item={item}
                onRead={() => markOneRead(item.id)}
                onNavigate={() => setOpen(false)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function NotificationItem({ item, onRead, onNavigate }) {
  const unread = !item.read_at;
  const content = (
    <div className={`rounded-md px-3 py-3 ${unread ? "bg-green-50" : "hover:bg-neutral-50"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">{item.title}</p>
          <p className="mt-1 text-sm leading-5 text-neutral-600">{item.body}</p>
          <p className="mt-2 text-xs font-semibold uppercase text-neutral-400">
            {item.category} · {formatRelativeTime(item.created_at)}
          </p>
        </div>
        {unread && (
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onRead();
            }}
            className="shrink-0 rounded-md px-2 py-1 text-xs font-semibold text-green-700 hover:bg-white"
          >
            Read
          </button>
        )}
      </div>
    </div>
  );

  if (item.action_url) {
    return (
      <Link to={item.action_url} onClick={onNavigate} className="block">
        {content}
      </Link>
    );
  }

  return content;
}

function formatRelativeTime(value) {
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return "recently";

  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 60) return "just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
