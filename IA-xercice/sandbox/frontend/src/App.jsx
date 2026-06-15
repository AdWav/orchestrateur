import { useEffect, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function fetchEntries() {
  const response = await fetch(`${API_BASE_URL}/entries`);
  if (!response.ok) throw new Error("Impossible de charger les messages.");
  return response.json();
}

async function postEntry(payload) {
  const response = await fetch(`${API_BASE_URL}/entries`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Impossible d'ajouter le message.");
  return response.json();
}

export default function App() {
  const [entries, setEntries] = useState([]);
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const isInvalid = useMemo(
    () => name.trim().length === 0 || message.trim().length === 0,
    [name, message]
  );

  useEffect(() => {
    let active = true;
    fetchEntries()
      .then((data) => {
        if (active) setEntries(data);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isInvalid || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const created = await postEntry({ name, message });
      setEntries((prev) => [created, ...prev]);
      setName("");
      setMessage("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="page">
      <section className="card">
        <h1>Livre d'or</h1>
        <p className="subtitle">Laisse un petit message dans le sandbox.</p>

        <form onSubmit={handleSubmit} className="form">
          <input
            type="text"
            placeholder="Ton nom"
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={100}
          />
          <textarea
            placeholder="Ton message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            maxLength={2000}
            rows={4}
          />
          <button type="submit" disabled={isInvalid || submitting}>
            {submitting ? "Envoi..." : "Signer le livre d'or"}
          </button>
        </form>

        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="card">
        <h2>Messages</h2>
        {loading ? <p>Chargement...</p> : null}
        {!loading && entries.length === 0 ? <p>Aucun message pour le moment.</p> : null}
        <ul className="list">
          {entries.map((entry) => (
            <li key={entry.id}>
              <div className="line">
                <strong>{entry.name}</strong>
                <span>{new Date(entry.created_at).toLocaleString()}</span>
              </div>
              <p>{entry.message}</p>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
