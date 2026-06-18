import { useEffect, useState } from "react";
import { LoaderCircle, RefreshCcw, ShieldCheck, UserCog } from "lucide-react";
import { api } from "../lib/api";
import { formatDate } from "../lib/content";
import { TierBadge } from "../components/TierBadge";

const tiers = ["free", "basic", "pro"];

export function AdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [message, setMessage] = useState("");

  async function loadUsers() {
    setLoading(true);
    setMessage("");
    try {
      setUsers(await api("/api/v1/users/admin/users"));
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function updateUser(user, patch) {
    setSavingId(user.id);
    setMessage("");
    try {
      const updated = await api(`/api/v1/users/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify(patch)
      });
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      setMessage(error.message);
    } finally {
      setSavingId(null);
    }
  }

  return (
    <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-4 border-b border-neutral-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-green-700">Admin</p>
          <h1 className="mt-2 font-display text-4xl font-semibold text-ink">Users</h1>
          <p className="mt-2 text-neutral-500">Manage access flags without touching the database manually.</p>
        </div>
        <button
          type="button"
          onClick={loadUsers}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-neutral-300 bg-white px-4 text-sm font-semibold text-ink"
        >
          <RefreshCcw size={16} />
          Refresh
        </button>
      </div>

      {message && (
        <p className="mt-5 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {message}
        </p>
      )}

      {loading ? (
        <div className="grid min-h-80 place-items-center">
          <LoaderCircle className="animate-spin text-green-600" size={30} />
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-lg border border-neutral-200 bg-white">
          <table className="min-w-[980px] w-full text-left text-sm">
            <thead className="border-b border-neutral-200 bg-neutral-50 text-xs uppercase text-neutral-500">
              <tr>
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">Tier</th>
                <th className="px-4 py-3">Active</th>
                <th className="px-4 py-3">Verified</th>
                <th className="px-4 py-3">Admin</th>
                <th className="px-4 py-3">Joined</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {users.map((user) => (
                <tr key={user.id}>
                  <td className="px-4 py-4">
                    <div className="flex items-start gap-3">
                      <span className="mt-0.5 grid h-9 w-9 place-items-center rounded-md bg-green-50 text-green-700">
                        {user.is_admin ? <ShieldCheck size={18} /> : <UserCog size={18} />}
                      </span>
                      <div>
                        <p className="font-semibold text-ink">{user.full_name}</p>
                        <p className="mt-0.5 text-neutral-500">{user.email}</p>
                        <p className="mt-0.5 text-xs text-neutral-400">{user.phone_number}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <select
                      value={user.subscription_tier}
                      disabled={savingId === user.id}
                      onChange={(event) => updateUser(user, { subscription_tier: event.target.value })}
                      className="h-9 rounded-md border border-neutral-300 bg-white px-2 text-sm"
                    >
                      {tiers.map((tier) => (
                        <option key={tier} value={tier}>{tier.toUpperCase()}</option>
                      ))}
                    </select>
                    <div className="mt-2"><TierBadge tier={user.subscription_tier} compact /></div>
                  </td>
                  <td className="px-4 py-4">
                    <FlagSwitch
                      checked={user.is_active}
                      disabled={savingId === user.id}
                      onChange={(value) => updateUser(user, { is_active: value })}
                    />
                  </td>
                  <td className="px-4 py-4">
                    <FlagSwitch
                      checked={user.is_verified}
                      disabled={savingId === user.id}
                      onChange={(value) => updateUser(user, { is_verified: value })}
                    />
                  </td>
                  <td className="px-4 py-4">
                    <FlagSwitch
                      checked={user.is_admin}
                      disabled={savingId === user.id}
                      onChange={(value) => updateUser(user, { is_admin: value })}
                    />
                  </td>
                  <td className="px-4 py-4 text-neutral-500">{formatDate(user.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function FlagSwitch({ checked, disabled, onChange }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`h-8 min-w-20 rounded-md border px-3 text-xs font-semibold ${
        checked
          ? "border-green-200 bg-green-50 text-green-700"
          : "border-neutral-300 bg-white text-neutral-500"
      } disabled:opacity-60`}
    >
      {checked ? "Yes" : "No"}
    </button>
  );
}
