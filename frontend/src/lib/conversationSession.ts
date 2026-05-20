const STORAGE_KEY = "orchestrateur.journey.conversationId";

/** Identifiant stable de session Parcours (localStorage). */
export function getJourneyConversationId(): string {
  try {
    const existing = localStorage.getItem(STORAGE_KEY);
    if (existing) {
      return existing;
    }
    const id = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, id);
    return id;
  } catch {
    return `ephemeral-${Date.now()}`;
  }
}

/** Nouvelle conversation : nouvel id persisté et retourné. */
export function resetJourneyConversationId(): string {
  const id = crypto.randomUUID();
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    /* ignore */
  }
  return id;
}
