import type { SupabaseClient } from '@supabase/supabase-js';

interface WebhookPost {
  title: string;
  slug: string;
  locale: string;
  excerpt?: string | null;
  post_type?: string | null;
  published_at?: string | null;
}

const MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours

interface WebhookRow {
  id: string;
  url: string;
  platform: string;
  is_active: boolean;
  fail_count: number;
}

const MAX_FAILURES = 5;

function formatDiscordPayload(post: WebhookPost, postUrl: string) {
  const typeLabel = post.post_type === 'weekly' ? 'Weekly Recap'
    : post.post_type === 'business' ? 'Business Digest'
    : 'Research Digest';

  return {
    embeds: [{
      title: `${typeLabel} — ${post.title}`,
      description: (post.excerpt || '').slice(0, 200),
      url: postUrl,
      color: 0xC4956A, // accent gold
      footer: { text: '0to1log AI News' },
      timestamp: new Date().toISOString(),
    }],
  };
}

function formatSlackPayload(post: WebhookPost, postUrl: string) {
  const typeLabel = post.post_type === 'weekly' ? 'Weekly Recap'
    : post.post_type === 'business' ? 'Business Digest'
    : 'Research Digest';

  return {
    text: `${typeLabel}: ${post.title}`,
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*<${postUrl}|${typeLabel} — ${post.title}>*\n${(post.excerpt || '').slice(0, 200)}`,
        },
      },
      {
        type: 'context',
        elements: [{ type: 'mrkdwn', text: '0to1log AI News' }],
      },
    ],
  };
}

function formatCustomPayload(post: WebhookPost, postUrl: string) {
  return {
    event: 'news.published',
    title: post.title,
    url: postUrl,
    excerpt: (post.excerpt || '').slice(0, 200),
    post_type: post.post_type || 'research',
    locale: post.locale,
    timestamp: new Date().toISOString(),
  };
}

function formatPayload(platform: string, post: WebhookPost, postUrl: string) {
  if (platform === 'discord') return formatDiscordPayload(post, postUrl);
  if (platform === 'slack') return formatSlackPayload(post, postUrl);
  return formatCustomPayload(post, postUrl);
}

export function formatTestPayload(platform: string) {
  const testPost: WebhookPost = {
    title: 'Test Notification',
    slug: 'test',
    locale: 'en',
    excerpt: 'This is a test message from 0to1log to verify your webhook is working correctly.',
    post_type: 'research',
  };
  const testUrl = 'https://0to1log.com/en/news/test/';
  return formatPayload(platform, testPost, testUrl);
}

export async function fireWebhooks(
  supabase: SupabaseClient,
  post: WebhookPost,
): Promise<void> {
  // Skip backfill: only notify for posts published within last 24h
  if (post.published_at) {
    const age = Date.now() - new Date(post.published_at).getTime();
    if (age > MAX_AGE_MS) return;
  }

  const { data: hooks } = await supabase
    .from('webhooks')
    .select('id, url, platform, is_active, fail_count')
    .eq('is_active', true);

  if (!hooks?.length) return;

  const siteUrl = import.meta.env.PUBLIC_SITE_URL || 'https://0to1log.com';
  const postUrl = `${siteUrl}/${post.locale}/news/${post.slug}/`;

  for (const hook of hooks as WebhookRow[]) {
    const payload = formatPayload(hook.platform, post, postUrl);

    fetch(hook.url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(async (res) => {
        if (res.ok) {
          await supabase.from('webhooks').update({
            fail_count: 0,
            last_fired_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }).eq('id', hook.id);
        } else {
          await handleFailure(supabase, hook, `HTTP ${res.status}`);
        }
      })
      .catch(async (err) => {
        await handleFailure(supabase, hook, String(err?.message || err));
      });
  }
}

async function handleFailure(supabase: SupabaseClient, hook: WebhookRow, error: string) {
  const newCount = hook.fail_count + 1;
  await supabase.from('webhooks').update({
    fail_count: newCount,
    last_error: error,
    is_active: newCount < MAX_FAILURES,
    updated_at: new Date().toISOString(),
  }).eq('id', hook.id);
}
