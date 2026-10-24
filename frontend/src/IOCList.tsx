import { IOC_TYPES, type IOC, type IOCType } from "./types";

interface Props {
  iocs: IOC[];
  allTags: string[];
  tagFilter: string;
  typeFilter: IOCType | "";
  loading: boolean;
  onTagFilter: (tag: string) => void;
  onTypeFilter: (type: IOCType | "") => void;
  onDelete: (ioc: IOC) => void;
}

export default function IOCList(p: Props) {
  const filtered = p.tagFilter !== "" || p.typeFilter !== "";
  return (
    <section className="card">
      <div className="list-head">
        <h2>Watchlist ({p.iocs.length})</h2>
        <div className="filters">
          <label>
            Type
            <select value={p.typeFilter} onChange={(e) => p.onTypeFilter(e.target.value as IOCType | "")}>
              <option value="">All types</option>
              {IOC_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
          <label>
            Tag
            <select value={p.tagFilter} onChange={(e) => p.onTagFilter(e.target.value)}>
              <option value="">All tags</option>
              {p.allTags.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {p.loading && p.iocs.length === 0 ? (
        <p className="empty">Loading…</p>
      ) : p.iocs.length === 0 ? (
        <p className="empty">
          {filtered ? "No indicators match these filters." : "No indicators yet. Add one using the form."}
        </p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Indicator</th>
                <th>Tags</th>
                <th>Note</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {p.iocs.map((ioc) => (
                <tr key={ioc.id}>
                  <td><span className={`type type-${ioc.type}`}>{ioc.type}</span></td>
                  <td className="mono" title={`Entered as: ${ioc.raw_value}`}>{ioc.value}</td>
                  <td>
                    {ioc.tags.map((t) => (
                      <button key={t} type="button" className="tag" onClick={() => p.onTagFilter(t)} title="Filter by this tag">
                        {t}
                      </button>
                    ))}
                  </td>
                  <td>{ioc.note}</td>
                  <td>
                    <button type="button" className="danger" onClick={() => p.onDelete(ioc)} aria-label={`Delete ${ioc.value}`}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
