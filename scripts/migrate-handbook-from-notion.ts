/**
 * One-time migration: Notion Words DB → Supabase handbook_terms
 *
 * Usage:
 *   npx tsx scripts/migrate-handbook-from-notion.ts
 *
 * Requires .env:
 *   NOTION_API_KEY=secret_xxx
 *   SUPABASE_URL=https://xxx.supabase.co
 *   SUPABASE_SERVICE_ROLE_KEY=eyJxxx  (service role, not anon)
 *   NOTION_WORDS_DB_ID=xxx            (Notion Words database ID)
 */

import { Client } from '@notionhq/client';
import { createClient } from '@supabase/supabase-js';
import 'dotenv/config';

const notion = new Client({ auth: process.env.NOTION_API_KEY });
const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);
const dbId = process.env.NOTION_WORDS_DB_ID!;

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim();
}

function richTextToPlain(richText: any[]): string {
  return richText?.map((rt: any) => rt.plain_text).join('') || '';
}

const CATEGORY_MAP: Record<string, string> = {
  'AI/ML & Algorithm': 'ai-ml',
  'DB / Data Infra': 'db-data',
  'Backend / Service Architecture': 'backend',
  'Frontend & UX/UI': 'frontend-ux',
  'Network / Communication': 'network',
  'Security / Access Control': 'security',
  'OS / Core Principle': 'os-core',
  'DevOps / Operation': 'devops',
  'Performance / Cost Mgt': 'performance',
  'Decentralization / Web3': 'web3',
};

async function getBlockChildren(blockId: string): Promise<string> {
  const blocks: any[] = [];
  let cursor: string | undefined;

  do {
    const res = await notion.blocks.children.list({
      block_id: blockId,
      start_cursor: cursor,
    });
    blocks.push(...res.results);
    cursor = res.has_more ? res.next_cursor! : undefined;
  } while (cursor);

  return blocks.map((block: any) => {
    const type = block.type;
    if (!block[type]) return '';

    switch (type) {
      case 'paragraph':
        return richTextToPlain(block.paragraph.rich_text) + '\n';
      case 'heading_1':
        return '# ' + richTextToPlain(block.heading_1.rich_text) + '\n';
      case 'heading_2':
        return '## ' + richTextToPlain(block.heading_2.rich_text) + '\n';
      case 'heading_3':
        return '### ' + richTextToPlain(block.heading_3.rich_text) + '\n';
      case 'bulleted_list_item':
        return '- ' + richTextToPlain(block.bulleted_list_item.rich_text) + '\n';
      case 'numbered_list_item':
        return '1. ' + richTextToPlain(block.numbered_list_item.rich_text) + '\n';
      case 'code': {
        const lang = block.code.language || '';
        return '```' + lang + '\n' + richTextToPlain(block.code.rich_text) + '\n```\n';
      }
      case 'quote':
        return '> ' + richTextToPlain(block.quote.rich_text) + '\n';
      case 'divider':
        return '---\n';
      case 'toggle': {
        const summary = richTextToPlain(block.toggle.rich_text);
        return `<details>\n<summary>${summary}</summary>\n\n</details>\n`;
      }
      default:
        return '';
    }
  }).join('\n');
}

async function main() {
  console.log('Fetching Notion Words DB...');

  const pages: any[] = [];
  let cursor: string | undefined;

  do {
    const res = await notion.databases.query({
      database_id: dbId,
      start_cursor: cursor,
    });
    pages.push(...res.results);
    cursor = res.has_more ? res.next_cursor! : undefined;
  } while (cursor);

  console.log(`Found ${pages.length} terms.`);

  for (const page of pages) {
    const props = page.properties;
    const term = richTextToPlain(props['Term']?.title || []);
    if (!term) { console.log('  Skipping page with no term'); continue; }

    const slug = slugify(term);
    const koreanName = richTextToPlain(props['Korean (한글명)']?.rich_text || []);
    const definition = richTextToPlain(props['Definition (정의)']?.rich_text || []);
    const plainExplanation = richTextToPlain(props['Plain Explanation (쉬운 설명)']?.rich_text || []);
    const technicalDescription = richTextToPlain(props['Technical Description (기술적 설명)']?.rich_text || []);
    const exampleAnalogy = richTextToPlain(props['Example/Analogy (예시/비유)']?.rich_text || []);
    const difficulty = props['Difficulty']?.select?.name?.toLowerCase() || null;
    const isFavourite = props['Favourite']?.checkbox || false;

    // Category (relation)
    let category: string | null = null;
    const catRelation = props['Category']?.relation || [];
    if (catRelation.length > 0) {
      try {
        const catPage = await notion.pages.retrieve({ page_id: catRelation[0].id });
        const catTitle = richTextToPlain((catPage as any).properties?.Name?.title || []);
        category = CATEGORY_MAP[catTitle] || catTitle;
      } catch { /* skip */ }
    }

    // Related Terms (self-relation)
    const relatedSlugs: string[] = [];
    const relatedRelation = props['Related Terms (관련 개념)']?.relation || [];
    for (const rel of relatedRelation) {
      try {
        const relPage = await notion.pages.retrieve({ page_id: rel.id });
        const relTerm = richTextToPlain((relPage as any).properties?.['Term']?.title || []);
        if (relTerm) relatedSlugs.push(slugify(relTerm));
      } catch { /* skip */ }
    }

    // Body markdown (page content)
    const bodyMarkdown = await getBlockChildren(page.id);

    console.log(`  Inserting: ${term} (${slug})`);

    const { error } = await supabase.from('handbook_terms').upsert({
      term,
      slug,
      korean_name: koreanName || null,
      difficulty,
      category,
      related_term_slugs: relatedSlugs.length ? relatedSlugs : null,
      is_favourite: isFavourite,
      definition_ko: definition || null,
      plain_explanation_ko: plainExplanation || null,
      technical_description_ko: technicalDescription || null,
      example_analogy_ko: exampleAnalogy || null,
      body_markdown_ko: bodyMarkdown || null,
      // EN fields intentionally NULL
      definition_en: null,
      plain_explanation_en: null,
      technical_description_en: null,
      example_analogy_en: null,
      body_markdown_en: null,
      status: 'draft',
      notion_page_id: page.id,
    }, { onConflict: 'slug' });

    if (error) {
      console.error(`  ERROR inserting ${term}:`, error.message);
    }
  }

  console.log('Migration complete.');
}

main().catch(console.error);
