import type { SupabaseClient } from '@supabase/supabase-js';

export interface BlogCategory {
  id: string;
  slug: string;
  label_ko: string;
  label_en: string;
  description_ko: string | null;
  description_en: string | null;
  color: string;
  icon: string | null;
  group_slug: string;
  sort_order: number;
  is_visible: boolean;
  write_mode: string;
  banner_url: string | null;
  guidelines: string | null;
}

export interface CategoryGroup {
  slug: string;
  label_ko: string;
  label_en: string;
  sort_order: number;
}

export async function fetchCategories(supabase: SupabaseClient): Promise<BlogCategory[]> {
  const { data } = await supabase
    .from('blog_categories')
    .select('*')
    .order('group_slug')
    .order('sort_order');
  return data ?? [];
}

export async function fetchCategoryBySlug(
  supabase: SupabaseClient,
  slug: string,
): Promise<BlogCategory | null> {
  const { data } = await supabase.from('blog_categories').select('*').eq('slug', slug).single();
  return data;
}

export async function fetchCategoryGroups(supabase: SupabaseClient): Promise<CategoryGroup[]> {
  const { data } = await supabase.from('category_groups').select('*').order('sort_order');
  return data ?? [];
}

export async function fetchCategoriesWithPostCount(
  supabase: SupabaseClient,
): Promise<(BlogCategory & { post_count: number })[]> {
  const { data: categories } = await supabase
    .from('blog_categories')
    .select('*')
    .order('group_slug')
    .order('sort_order');

  if (!categories) return [];

  const { data: counts } = await supabase
    .from('blog_posts')
    .select('category')
    .not('category', 'is', null);

  const countMap = new Map<string, number>();
  for (const row of counts ?? []) {
    countMap.set(row.category, (countMap.get(row.category) ?? 0) + 1);
  }

  return categories.map((cat) => ({
    ...cat,
    post_count: countMap.get(cat.slug) ?? 0,
  }));
}
