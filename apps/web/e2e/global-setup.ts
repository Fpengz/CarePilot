/**
 * Playwright global setup.
 *
 * The backend auto-seeds demo users on startup (member@example.com, helper@example.com,
 * admin@example.com) via demo_defaults.py, so no extra seeding is needed here.
 * This file exists as a hook for future per-run setup (e.g. resetting state).
 */
async function globalSetup() {
  // Demo users are auto-seeded by the backend — nothing to do.
}

export default globalSetup;

