import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

const USERNAME_RE = /^[a-z0-9][a-z0-9-]{1,18}[a-z0-9]$/;
const VALID_PERSONAS = ['learner', 'expert'];
const VALID_LOCALES = ['en', 'ko'];
const VALID_HANDBOOK_LEVELS = ['basic', 'advanced'];
const USERNAME_COOLDOWN_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function makeAuthClient(accessToken: string) {
  return createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );
}

export const GET: APIRoute = async ({ locals, request }) => {
  if (!locals.user || !locals.accessToken) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  const supabase = makeAuthClient(locals.accessToken);
  const { data, error } = await supabase
    .from('profiles')
    .select('*')
    .eq('id', locals.user.id)
    .maybeSingle();

  if (error) {
    return jsonResponse({ error: 'Database error' }, 500);
  }

  // No profile yet — return fallback from user metadata
  if (!data) {
    const acceptLang = request.headers.get('accept-language') || '';
    const defaultLocale = acceptLang.split(',').some(l => l.trim().startsWith('ko')) ? 'ko' : 'en';
    return jsonResponse({
      id: locals.user.id,
      display_name: locals.user.user_metadata?.full_name || locals.user.email || '',
      username: null,
      avatar_url: locals.user.user_metadata?.avatar_url || null,
      bio: null,
      persona: null,
      preferred_locale: defaultLocale,
      is_public: false,
      onboarding_completed: false,
    });
  }

  return jsonResponse(data);
};

export const PUT: APIRoute = async ({ request, locals, cookies }) => {
  if (!locals.user || !locals.accessToken) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  const body = await request.json();
  const { display_name, username, bio, persona, preferred_locale, is_public, onboarding_completed, handbook_level } = body;

  // Validate persona
  if (persona && !VALID_PERSONAS.includes(persona)) {
    return jsonResponse({ error: 'Invalid persona' }, 400);
  }

  // Validate handbook_level
  if (handbook_level && !VALID_HANDBOOK_LEVELS.includes(handbook_level)) {
    return jsonResponse({ error: 'Invalid handbook_level' }, 400);
  }

  // Validate preferred_locale
  if (preferred_locale && !VALID_LOCALES.includes(preferred_locale)) {
    return jsonResponse({ error: 'Invalid locale' }, 400);
  }

  // Validate username format (if provided)
  if (username !== undefined && username !== null && username !== '') {
    if (!USERNAME_RE.test(username)) {
      return jsonResponse({
        error: 'Username must be 3-20 characters, lowercase letters, numbers, and hyphens only',
      }, 400);
    }
  }

  const supabase = makeAuthClient(locals.accessToken);

  // If username is changing, enforce 30-day cooldown and track change timestamp
  const newUsername = username || null;
  let usernameActuallyChanged = false;
  if (username !== undefined) {
    const { data: current } = await supabase
      .from('profiles')
      .select('username, username_changed_at')
      .eq('id', locals.user.id)
      .maybeSingle();

    if (current && newUsername !== current.username) {
      if (current.username_changed_at) {
        const elapsed = Date.now() - new Date(current.username_changed_at).getTime();
        if (elapsed < USERNAME_COOLDOWN_MS) {
          return jsonResponse({ error: 'User ID can only be changed once every 30 days' }, 429);
        }
      }
      usernameActuallyChanged = true;
    } else if (!current && newUsername) {
      usernameActuallyChanged = true; // first time setting
    }
  }

  const upsertData: Record<string, unknown> = {
    id: locals.user.id,
    updated_at: new Date().toISOString(),
  };

  // Only include fields that were sent in the request
  if (display_name !== undefined) upsertData.display_name = display_name || null;
  if (username !== undefined) {
    upsertData.username = newUsername;
    if (usernameActuallyChanged) {
      upsertData.username_changed_at = new Date().toISOString();
    }
  }
  if (bio !== undefined) upsertData.bio = bio || null;
  if (persona !== undefined) upsertData.persona = persona || null;
  if (handbook_level !== undefined) upsertData.handbook_level = handbook_level || 'basic';
  if (preferred_locale !== undefined) upsertData.preferred_locale = preferred_locale;
  if (is_public !== undefined) upsertData.is_public = !!is_public;
  if (onboarding_completed !== undefined) upsertData.onboarding_completed = !!onboarding_completed;

  const { data, error } = await supabase
    .from('profiles')
    .upsert(upsertData, { onConflict: 'id' })
    .select()
    .single();

  if (error) {
    // Handle unique constraint violation for username
    if (error.code === '23505' && error.message.includes('username')) {
      return jsonResponse({ error: 'Username already taken' }, 409);
    }
    return jsonResponse({ error: 'Database error' }, 500);
  }

  // Invalidate cached user extras so next page load fetches fresh profile
  cookies.delete('user-extras-cache', { path: '/' });

  return jsonResponse(data);
};
