import { useCallback, useEffect, useState } from "react";
import AddIOCForm from "./AddIOCForm";
import IOCList from "./IOCList";
import { ApiError, api } from "./api";
import type { IOC, IOCType } from "./types";

export default function App() {
  const [iocs, setIocs] = useState<IOC[]>([]);
  const [allTags, setAllTags] = useState<string[]>([]);
  const [tagFilter, setTagFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState<IOCType | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [list, tags] = await Promise.all([
        api.list({ tag: tagFilter, type: typeFilter }),
        api.tags(),
      ]);
      setIocs(list);
      setAllTags(tags);
      // A filter on a tag that no longer exists would show an empty list with no way out.
      if (tagFilter && !tags.includes(tagFilter)) setTagFilter("");
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load indicators.");
    } finally {
      setLoading(false);
    }
  }, [tagFilter, typeFilter]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function remove(ioc: IOC) {
    if (!window.confirm(`Delete ${ioc.type} ${ioc.value}?`)) return;
    try {
      await api.remove(ioc.id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed.");
    }
  }

  return (
    <main>
      <h1>IOC Watchlist Manager</h1>
      <AddIOCForm onAdded={refresh} />
      {error && <p role="alert" className="msg error">{error}</p>}
      <IOCList
        iocs={iocs}
        allTags={allTags}
        tagFilter={tagFilter}
        typeFilter={typeFilter}
        loading={loading}
        onTagFilter={setTagFilter}
        onTypeFilter={setTypeFilter}
        onDelete={remove}
      />
    </main>
  );
}
