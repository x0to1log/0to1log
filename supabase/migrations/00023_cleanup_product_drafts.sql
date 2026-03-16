-- 00023_cleanup_product_drafts.sql
-- Clean up non-product entries from seed data and remove duplicates

-- =============================================================================
-- 1. Remove duplicates
-- =============================================================================
-- suno-ai is a duplicate of suno (same product, different URL)
DELETE FROM ai_products WHERE slug = 'suno-ai';

-- sora-2 is a duplicate of sora
DELETE FROM ai_products WHERE slug = 'sora-2';

-- klingai is a duplicate of kling-2.6
DELETE FROM ai_products WHERE slug = 'klingai';

-- posthog-a-b-testing is a guide, not a product (posthog already exists)
DELETE FROM ai_products WHERE slug = 'posthog-a-b-testing';

-- =============================================================================
-- 2. Remove blog posts, docs, and reference links (not products)
-- =============================================================================
DELETE FROM ai_products WHERE slug IN (
  -- Blog posts / articles
  'claude-code-is-a-beast',           -- Reddit post
  'antigravity',                       -- Blog post (product is google-antigravity)
  'antigravity-getting-started',       -- Tutorial codelab
  'minusx-what-makes-claude-code-so-damn-good',  -- Blog analysis

  -- Documentation pages (not standalone products)
  'extend-claude-code',                -- Claude Code docs page
  'how-claude-code-works',             -- Claude Code docs page
  'manage-claudes-memory',             -- Claude Code docs page
  'api-keys-openai-api',               -- OpenAI settings page
  'billing-overview-openai-api',       -- OpenAI billing page
  'openai-prompt-caching',             -- OpenAI docs page
  'openai-batch-api',                  -- OpenAI docs page
  'tokenizer-openai-api',              -- OpenAI tokenizer tool
  'cost-tracking-guide',               -- Helicone guide page
  'graph_recursion_limit',             -- LangChain error docs
  'aws-secrets-manager-best-practices', -- AWS docs
  'aws-waf-rate-based-request-limiting', -- AWS docs

  -- GitHub repos that are reference/learning, not products
  'chacha95-advanced-harness',
  'coleam00-second-brain-skills-a-collection-of-claude-skills-to-turn-claude-code-into-a-second-brain',
  'jordansinger-build-it-figma-ai',
  'github.com-berriai-litellm',        -- litellm product already covered

  -- Notion templates / marketplace profile (not products)
  'marketplace-profile-notion',
  'notion-prd-templates',

  -- Generic directory/index pages (meta, not products)
  'the-agent-skills-directory',
  'vibe-index'
);

-- =============================================================================
-- 3. Fix product names that have extra text
-- =============================================================================
UPDATE ai_products SET name = 'PixAI' WHERE slug = 'ai-pixai';
UPDATE ai_products SET name = 'SeaArt AI' WHERE slug = 'ai-seaart-ai';
UPDATE ai_products SET name = 'Microsoft Designer' WHERE slug = 'microsoft-designer';
UPDATE ai_products SET name = 'Eddie AI' WHERE slug = 'eddie-ai-the-assistant-video-editor-for-pros';
UPDATE ai_products SET name = 'Mockuper' WHERE slug = 'mockuper.net-free-custom-mockups-generator';
UPDATE ai_products SET name = 'Replicate' WHERE slug = 'replicate-run-ai-with-an-api';
UPDATE ai_products SET name = 'Liner' WHERE slug = 'app';
UPDATE ai_products SET name = '요즘IT' WHERE slug = 'it';
UPDATE ai_products SET name = 'Pangea AI Guard' WHERE slug = 'pangea-ai-guard-pii-redaction-prompt-injection';
UPDATE ai_products SET name = 'Microsoft Presidio' WHERE slug = 'microsoft-presidio-pii';
UPDATE ai_products SET name = 'LiteLLM' WHERE slug = 'litellm-proxy-ai-gateway';

-- Fix HeyGen miscategorized as image → should be video
UPDATE ai_products SET primary_category = 'video' WHERE slug = 'heygen-ai-video-generator';
UPDATE ai_products SET name = 'HeyGen' WHERE slug = 'heygen-ai-video-generator';

-- Fix Moltbot name
UPDATE ai_products SET name = 'Moltbot' WHERE slug = 'moltbot-personal-ai-assistant';
