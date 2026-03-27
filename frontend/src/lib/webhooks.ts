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
  locale: string;
  is_active: boolean;
  fail_count: number;
}

const MAX_FAILURES = 5;
const BOT_NAME = '0to1log';
const BOT_AVATAR = 'https://0to1log.com/og-default.png';

function formatDiscordPayload(post: WebhookPost, postUrl: string) {
  const typeLabel = post.post_type === 'weekly' ? 'Weekly Recap'
    : post.post_type === 'business' ? 'Business Digest'
    : 'Research Digest';

  return {
    username: BOT_NAME,
    avatar_url: BOT_AVATAR,
    embeds: [{
      title: `${typeLabel} — ${post.title}`,
      description: (post.excerpt || '').slice(0, 200),
      url: postUrl,
      color: 0xC4956A,
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

export function formatTestPayload(platform: string, locale: string = 'en') {
  const isKo = locale === 'ko';
  const testUrl = `https://0to1log.com/${locale}/news/test/`;

  if (platform === 'discord') {
    return {
      username: BOT_NAME,
      avatar_url: BOT_AVATAR,
      embeds: [{
        title: isKo ? '[Test] 0to1log VIP 초대장이 도착했습니다 ✉️' : "[Test] Your 0to1log VIP Invitation ✉️",
        description: isKo
          ? '성공적으로 웹훅이 연결되었습니다.\n본 알림은 정상 연동을 알리는 테스트 메시지이며, 앞으로 새로운 AI 뉴스가 발행되면 이곳으로 배달됩니다.\n\n👉 **나만의 초대장 열어보기**'
          : 'Webhook successfully connected.\nThis is a test message. Future AI news will be correctly delivered to this channel.\n\n👉 **Open your invitation**',
        url: testUrl,
        color: 0xC4956A,
        footer: { text: '0to1log AI News' },
        timestamp: new Date().toISOString(),
      }],
    };
  }

  // Slack / custom fallback
  const testPost: WebhookPost = {
    title: isKo ? '[Test] 0to1log VIP 초대장이 도착했습니다 ✉️' : "[Test] Your 0to1log VIP Invitation ✉️",
    slug: 'test',
    locale,
    excerpt: isKo
      ? '성공적으로 웹훅이 연결되었습니다! 초대장을 확인해주세요.'
      : 'Webhook successfully connected! Open your invitation.',
    post_type: 'research',
  };
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

  // Fetch admin webhooks and user webhooks in parallel
  const [{ data: adminHooks }, { data: userHooks }] = await Promise.all([
    supabase
      .from('webhooks')
      .select('id, url, platform, locale, is_active, fail_count')
      .eq('is_active', true),
    supabase
      .from('user_webhooks')
      .select('id, url, platform, locale, is_active, fail_count')
      .eq('is_active', true),
  ]);

  const allHooks: { hook: WebhookRow; table: 'webhooks' | 'user_webhooks' }[] = [];
  for (const h of (adminHooks as WebhookRow[]) || []) {
    if (h.locale === 'all' || h.locale === post.locale) {
      allHooks.push({ hook: h, table: 'webhooks' });
    }
  }
  for (const h of (userHooks as WebhookRow[]) || []) {
    if (h.locale === 'all' || h.locale === post.locale) {
      allHooks.push({ hook: h, table: 'user_webhooks' });
    }
  }

  if (!allHooks.length) return;

  const siteUrl = import.meta.env.PUBLIC_SITE_URL || 'https://0to1log.com';
  const postUrl = `${siteUrl}/${post.locale}/news/${post.slug}/`;

  for (const { hook, table } of allHooks) {
    const payload = formatPayload(hook.platform, post, postUrl);

    fetch(hook.url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(async (res) => {
        if (res.ok) {
          await supabase.from(table).update({
            fail_count: 0,
            last_fired_at: new Date().toISOString(),
            ...(table === 'webhooks' ? { updated_at: new Date().toISOString() } : {}),
          }).eq('id', hook.id);
        } else {
          await handleFailure(supabase, hook, `HTTP ${res.status}`, table);
        }
      })
      .catch(async (err) => {
        await handleFailure(supabase, hook, String(err?.message || err), table);
      });
  }
}

async function handleFailure(supabase: SupabaseClient, hook: WebhookRow, error: string, table: 'webhooks' | 'user_webhooks' = 'webhooks') {
  const newCount = hook.fail_count + 1;
  await supabase.from(table).update({
    fail_count: newCount,
    last_error: error,
    is_active: newCount < MAX_FAILURES,
    ...(table === 'webhooks' ? { updated_at: new Date().toISOString() } : {}),
  }).eq('id', hook.id);
}
