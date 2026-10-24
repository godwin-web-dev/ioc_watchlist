import { useState, type FormEvent } from "react";
import { ApiError, api } from "./api";

interface Props {
  onAdded: () => void;
}

export default function AddIOCForm({ onAdded }: Props) {
  const [value, setValue] = useState("");
  const [note, setNote] = useState("");
  const [tagText, setTagText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const tags = tagText.split(",").map((t) => t.trim()).filter(Boolean);
      const created = await api.create({ value, note: note || undefined, tags });
      setSuccess(`Added ${created.type}: ${created.value}`);
      setValue("");
      setNote("");
      setTagText("");
      onAdded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unexpected error.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="card">
      <h2>Add indicator</h2>
      <label>
        Value
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="e.g. hxxps://evil[.]example[.]com/login"
          required
          autoFocus
        />
      </label>
      <label>
        Note (optional)
        <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} />
      </label>
      <label>
        Tags (comma-separated)
        <input
          value={tagText}
          onChange={(e) => setTagText(e.target.value)}
          placeholder="phishing, c2, ransomware"
        />
      </label>
      <button type="submit" disabled={busy || !value.trim()}>
        {busy ? "Adding…" : "Add indicator"}
      </button>
      {error && <p role="alert" className="msg error">{error}</p>}
      {success && <p role="status" className="msg ok">{success}</p>}
    </form>
  );
}
