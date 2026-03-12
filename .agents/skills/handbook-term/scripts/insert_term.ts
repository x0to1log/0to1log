/**
 * Usage:
 * Execute this script using an agent by piping the generated JSON string in or writing a local file.
 * This script serves as a reference for how to insert terms automatically during the agent session.
 */
import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Note: Ensure the agent executes this script relative to the frontend directory
// and that .env contains SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
dotenv.config({ path: path.resolve(process.cwd(), 'frontend', '.env') });

async function insertTerm(jsonData: any) {
    const url = process.env.PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
    const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!url || !key) {
        console.error('Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing.');
        process.exit(1);
    }

    const supabase = createClient(url, key);

    try {
        const { data, error } = await supabase
            .from('handbook_terms')
            .insert([jsonData])
            .select();

        if (error) {
            console.error('Insert failed:', error.message);
            process.exit(1);
        }
        console.log('Successfully inserted term:', data[0]?.slug);
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
        insertTerm(parsed);
    } catch (e) {
        console.error('Invalid JSON provided.');
    }
} else {
    console.log('Please provide a JSON string as an argument.');
}
