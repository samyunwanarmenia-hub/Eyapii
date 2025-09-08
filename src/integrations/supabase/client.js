import { createClient } from '@supabase/supabase-js';

// Hardcoding Supabase URL and Anon Key for frontend use.
export const SUPABASE_URL = "https://mvibvxkggerhsdhhwhsi.supabase.co";
export const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im12aWJ2eGtnZ2VyaHNkaGh3aHNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcyOTU0ODcsImV4cCI6MjA3Mjg3MTQ4N30.-kMWzL2a2tADTZEQibLYjlb3Hha20M4fGkw04sV8-mk";

// Ensure the values are not undefined before passing them
if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error("Supabase URL or Anon Key is missing or undefined. This should not happen with hardcoded values.");
}

// Directly pass the hardcoded values to createClient, bypassing any process.env checks.
export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);