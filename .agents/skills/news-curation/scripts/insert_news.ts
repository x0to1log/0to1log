/**
 * Usage:
 * Execute this script using an agent by piping the generated JSON string in or writing a local file.
 * This script inserts the curated news JSON directly into the Supabase database.
 */
import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), 'frontend', '.env') });

async function insertNews(jsonData: any) {
    const url = process.env.PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
    const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!url || !key) {
        console.error('Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing.');
        process.exit(1);
    }

    const supabase = createClient(url, key);

    try {
        const { data, error } = await supabase
            .from('posts')
            .insert([{
                title_en: jsonData.title_en,
                title_ko: jsonData.title_ko,
                slug: jsonData.slug,
                excerpt_en: jsonData.excerpt_en,
                excerpt_ko: jsonData.excerpt_ko,
                category: jsonData.category,
                tags: jsonData.tags,
                reading_time_min: jsonData.reading_time_min || 3,
                body_markdown_en: jsonData.body_markdown_en,
                body_markdown_ko: jsonData.body_markdown_ko,
                canonical_url: jsonData.source_url, // map source_url to canonical_url if that is your schema
                post_type: 'research'
            }])
            .select();

        if (error) {
            console.error('Insert failed:', error.message);
            process.exit(1);
        }
        console.log(`Successfully inserted news post: ${data[0]?.slug}`);
    } catch (err) {
        console.error('Unexpected error:', err);
        process.exit(1);
    }
}

// Read JSON string from argument if provided
const inputJson = process.argv[2];
if (inputJson) {
    try {
        const parsed = JSON.parse(inputJson);
        insertNews(parsed);
    } catch (e) {
        console.error('Invalid JSON provided.');
    }
} else {
    console.log('Please provide a JSON string as an argument.');
}
