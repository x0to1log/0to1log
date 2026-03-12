import { createClient } from '@supabase/supabase-js';
import { supabase } from '../supabase';

export interface DetailPageContext {
  locale: 'en' | 'ko';
  slug: string;
  previewMode: boolean;
  locals: Record<string, any>;
}

export function getPublicSupabase() {
  return supabase;
}

export function getAuthorizedSupabase(accessToken?: string | null) {
  if (!accessToken) return null;

  return createClient(
    import.meta.env.PUBLIC_SUPABASE_URL,
    import.meta.env.PUBLIC_SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${accessToken}` } } },
  );
}

export function getDefinitionField(locale: 'en' | 'ko'): 'definition_en' | 'definition_ko' {
  return locale === 'ko' ? 'definition_ko' : 'definition_en';
}
