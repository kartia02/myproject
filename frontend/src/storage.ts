import type { PersonalWorkspace } from "./types";

const STORAGE_KEY = "pet-detective.workspace.v1";

export function loadWorkspace(): PersonalWorkspace | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as PersonalWorkspace;
    if (!value?.profile?.name || !["sample", "personal"].includes(value.profile.mode)) return null;
    return {
      profile: value.profile,
      records: Array.isArray(value.records) ? value.records : [],
      events: Array.isArray(value.events) ? value.events : []
    };
  } catch {
    return null;
  }
}

export function saveWorkspace(workspace: PersonalWorkspace): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(workspace));
}

export function clearWorkspace(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}
