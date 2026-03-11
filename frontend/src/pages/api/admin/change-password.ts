import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

// Rate limit: max 5 attempts per 15 minutes per user
const attempts = new Map<string, { count: number; resetAt: number }>();
const MAX_ATTEMPTS = 5;
const WINDOW_MS = 15 * 60 * 1000;

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken || !locals.isAdmin) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  const userId = locals.user.id;
  const now = Date.now();
  const entry = attempts.get(userId);
  if (entry && now < entry.resetAt) {
    if (entry.count >= MAX_ATTEMPTS) {
      return new Response(JSON.stringify({ error: 'Too many attempts. Try again later.' }), {
        status: 429, headers: { 'Content-Type': 'application/json' },
      });
    }
    entry.count++;
  } else {
    attempts.set(userId, { count: 1, resetAt: now + WINDOW_MS });
  }

  const body = await request.json();
  const { currentPassword, newPassword } = body;

  if (!currentPassword || !newPassword) {
    return new Response(JSON.stringify({ error: 'Both current and new password are required' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  if (newPassword.length < 8) {
    return new Response(JSON.stringify({ error: 'New password must be at least 8 characters' }), {
      status: 400, headers: { 'Content-Type': 'application/json' },
    });
  }

  const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;

  // Verify current password by attempting sign-in
  const verifySb = createClient(supabaseUrl, supabaseAnonKey);
  const { error: verifyError } = await verifySb.auth.signInWithPassword({
    email: locals.user.email!,
    password: currentPassword,
  });

  if (verifyError) {
    return new Response(JSON.stringify({ error: 'Current password is incorrect' }), {
      status: 403, headers: { 'Content-Type': 'application/json' },
    });
  }

  // Update password using the user's authenticated session
  const authSb = createClient(supabaseUrl, supabaseAnonKey, {
    global: { headers: { Authorization: `Bearer ${locals.accessToken}` } },
  });

  const { error: updateError } = await authSb.auth.updateUser({ password: newPassword });

  if (updateError) {
    return new Response(JSON.stringify({ error: updateError.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  });
};
