// clients/mobile/api/chatProfile.ts
export type Profile = {
  consent_personalization: boolean;
  memory_paused: boolean;
  allergies: string[];
  pregnancy_trimester?: number | null;
  pregnancy_due_date?: string | null; // ISO yyyy-mm-dd
  child_birthdate?: string | null;    // ISO yyyy-mm-dd
};

async function req<T>(url: string, init: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  return (await res.json()) as T;
}

export async function getProfile(apiBase: string, token?: string): Promise<Profile> {
  return await req<Profile>(`${apiBase}/api/v1/chat/profile`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
}

export async function putProfile(apiBase: string, body: Profile, token?: string): Promise<{ ok: boolean; updated_at: string }> {
  return await req<{ ok: boolean; updated_at: string }>(`${apiBase}/api/v1/chat/profile`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
}
