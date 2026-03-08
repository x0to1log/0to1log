import type { APIRoute } from 'astro';
import { createClient } from '@supabase/supabase-js';

export const prerender = false;

const MAX_SIZE = 2 * 1024 * 1024; // 2MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
const BUCKET = 'avatars';

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

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.user || !locals.accessToken) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  const formData = await request.formData();
  const file = formData.get('avatar') as File | null;

  if (!file) {
    return jsonResponse({ error: 'No file provided' }, 400);
  }

  if (!ALLOWED_TYPES.includes(file.type)) {
    return jsonResponse({ error: 'Only JPEG, PNG, WebP, and GIF are allowed' }, 400);
  }

  if (file.size > MAX_SIZE) {
    return jsonResponse({ error: 'File must be under 2MB' }, 400);
  }

  const ext = file.name.split('.').pop()?.toLowerCase() || 'jpg';
  const filePath = `${locals.user.id}.${ext}`;

  const supabase = makeAuthClient(locals.accessToken);
  const buffer = await file.arrayBuffer();

  // Upload (upsert to overwrite existing)
  const { error: uploadError } = await supabase.storage
    .from(BUCKET)
    .upload(filePath, buffer, {
      contentType: file.type,
      upsert: true,
    });

  if (uploadError) {
    return jsonResponse({ error: uploadError.message }, 500);
  }

  // Get public URL
  const { data: urlData } = supabase.storage
    .from(BUCKET)
    .getPublicUrl(filePath);

  const avatarUrl = urlData.publicUrl;

  // Update profile
  const { error: updateError } = await supabase
    .from('profiles')
    .update({ avatar_url: avatarUrl, updated_at: new Date().toISOString() })
    .eq('id', locals.user.id);

  if (updateError) {
    return jsonResponse({ error: updateError.message }, 500);
  }

  return jsonResponse({ avatar_url: avatarUrl });
};

export const DELETE: APIRoute = async ({ locals }) => {
  if (!locals.user || !locals.accessToken) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  const supabase = makeAuthClient(locals.accessToken);

  // Remove all possible extensions
  const extensions = ['jpg', 'jpeg', 'png', 'webp', 'gif'];
  const paths = extensions.map((ext) => `${locals.user!.id}.${ext}`);
  await supabase.storage.from(BUCKET).remove(paths);

  // Revert to OAuth avatar
  const oauthAvatar = locals.user.user_metadata?.avatar_url || null;
  const { error } = await supabase
    .from('profiles')
    .update({ avatar_url: oauthAvatar, updated_at: new Date().toISOString() })
    .eq('id', locals.user.id);

  if (error) {
    return jsonResponse({ error: error.message }, 500);
  }

  return jsonResponse({ avatar_url: oauthAvatar });
};
