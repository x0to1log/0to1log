import { supabase } from '../supabase';
import { getPublicSupabase } from './shared';
import { renderMarkdown } from '../markdown';

// =============================================================================
// Types
// =============================================================================

export interface ProductCategory {
  id: string;
  label_en: string;
  label_ko: string;
  description_en: string | null;
  description_ko: string | null;
  icon: string | null;
  sort_order: number;
}

export interface ProductCardData {
  id: string;
  slug: string;
  name: string;
  tagline: string | null;
  logo_url: string | null;
  thumbnail_url: string | null;
  pricing: string | null;
  platform: string[] | null;
  korean_support: boolean;
  primary_category: string;
  featured: boolean;
  featured_order: number | null;
  demo_media: Array<{ type: string; url: string }> | null;
  view_count: number;
  sort_order: number | null;
  tags: string[] | null;
}

export interface ProductDetailData {
  id: string;
  slug: string;
  name: string;
  name_ko: string | null;
  url: string;
  tagline: string | null;
  tagline_ko: string | null;
  description: string | null;
  description_ko: string | null;
  primary_category: string;
  secondary_categories: string[] | null;
  logo_url: string | null;
  thumbnail_url: string | null;
  demo_media: Array<{ type: string; url: string; caption?: string }>;
  tags: string[] | null;
  platform: string[] | null;
  korean_support: boolean;
  released_at: string | null;
  pricing: string | null;
  pricing_note: string | null;
  view_count: number;
  like_count: number;
  features: string[];
  features_ko: string[];
  use_cases: string[];
  use_cases_ko: string[];
}

export interface ProductsPageData {
  categories: ProductCategory[];
  spotlightProduct: ProductCardData | null;
  allProducts: ProductCardData[];
  productsByCategory: Record<string, ProductCardData[]>;
  totalProducts: number;
  error: string | null;
}

export interface ProductDetailPageData {
  product: ProductDetailData | null;
  htmlDescription: string;
  error: string | null;
}

export interface HomeFeaturedProduct {
  id: string;
  slug: string;
  name: string;
  name_ko: string | null;
  tagline: string | null;
  tagline_ko: string | null;
  logo_url: string | null;
  pricing: string | null;
  korean_support: boolean;
}

// =============================================================================
// List page
// =============================================================================

const CARD_COLUMNS =
  'id, slug, name, tagline, logo_url, thumbnail_url, pricing, platform, korean_support, primary_category, featured, featured_order, demo_media, view_count, sort_order, tags';

export async function getProductsPageData(locale: 'en' | 'ko'): Promise<ProductsPageData> {
  if (!supabase) {
    return { categories: [], spotlightProduct: null, allProducts: [], productsByCategory: {}, totalProducts: 0, error: null };
  }

  const [categoriesRes, productsRes] = await Promise.all([
    supabase.from('ai_product_categories').select('*').order('sort_order'),
    supabase
      .from('ai_products')
      .select(CARD_COLUMNS)
      .eq('is_published', true)
      .order('sort_order')
      .order('name'),
  ]);

  if (categoriesRes.error) {
    return { categories: [], spotlightProduct: null, allProducts: [], productsByCategory: {}, totalProducts: 0, error: categoriesRes.error.message };
  }

  const categories = (categoriesRes.data ?? []) as ProductCategory[];
  const allProducts = (productsRes.data ?? []) as ProductCardData[];

  // Category sort order map for grouping products by category
  const catOrder = Object.fromEntries(categories.map((c) => [c.id, c.sort_order]));

  const resolvedProducts = allProducts.map((p) => ({
    ...p,
    name: (locale === 'ko' ? (p as any).name_ko || p.name : p.name) as string,
    tagline: (locale === 'ko' ? (p as any).tagline_ko || p.tagline : p.tagline) as string | null,
  }));

  // Sort: category order → product sort_order → name
  resolvedProducts.sort((a, b) => {
    const catA = catOrder[a.primary_category] ?? 99;
    const catB = catOrder[b.primary_category] ?? 99;
    if (catA !== catB) return catA - catB;
    const sortA = a.sort_order ?? 99;
    const sortB = b.sort_order ?? 99;
    if (sortA !== sortB) return sortA - sortB;
    return a.name.localeCompare(b.name);
  });

  // Spotlight: 가장 높은 featured_order를 가진 featured 제품 1개
  const spotlightProduct = resolvedProducts
    .filter((p) => p.featured)
    .sort((a, b) => (a.featured_order ?? 99) - (b.featured_order ?? 99))[0] ?? null;

  // Group by category for preview mode
  const productsByCategory: Record<string, ProductCardData[]> = {};
  for (const cat of categories) {
    productsByCategory[cat.id] = resolvedProducts.filter((p) => p.primary_category === cat.id);
  }

  return { categories, spotlightProduct, allProducts: resolvedProducts, productsByCategory, totalProducts: resolvedProducts.length, error: null };
}

// =============================================================================
// Detail page
// =============================================================================

export async function getProductDetailData(
  slug: string,
  locale: 'en' | 'ko',
): Promise<ProductDetailPageData> {
  const db = getPublicSupabase();
  if (!db) {
    return { product: null, htmlDescription: '', error: 'Database unavailable.' };
  }

  const { data, error } = await db
    .from('ai_products')
    .select('*')
    .eq('slug', slug)
    .eq('is_published', true)
    .single();

  if (error) {
    // PGRST116 = no rows found
    if (error.code === 'PGRST116') {
      return { product: null, htmlDescription: '', error: null };
    }
    return { product: null, htmlDescription: '', error: error.message };
  }

  const raw = data as any;

  // Resolve locale fields
  const product: ProductDetailData = {
    id: raw.id,
    slug: raw.slug,
    name: (locale === 'ko' ? raw.name_ko || raw.name : raw.name) as string,
    name_ko: raw.name_ko,
    url: raw.url,
    tagline: (locale === 'ko' ? raw.tagline_ko || raw.tagline : raw.tagline) as string | null,
    tagline_ko: raw.tagline_ko,
    description: raw.description,
    description_ko: raw.description_ko,
    primary_category: raw.primary_category,
    secondary_categories: raw.secondary_categories,
    logo_url: raw.logo_url,
    thumbnail_url: raw.thumbnail_url,
    demo_media: (raw.demo_media as Array<{ type: string; url: string; caption?: string }>) ?? [],
    tags: raw.tags,
    platform: raw.platform,
    korean_support: raw.korean_support ?? false,
    released_at: raw.released_at,
    pricing: raw.pricing,
    pricing_note: raw.pricing_note,
    view_count: raw.view_count ?? 0,
    like_count: raw.like_count ?? 0,
    features: (raw.features as string[]) ?? [],
    features_ko: (raw.features_ko as string[]) ?? [],
    use_cases: (raw.use_cases as string[]) ?? [],
    use_cases_ko: (raw.use_cases_ko as string[]) ?? [],
  };

  const rawDescription =
    locale === 'ko' ? raw.description_ko || raw.description : raw.description;

  const htmlDescription = rawDescription ? await renderMarkdown(rawDescription) : '';

  return { product, htmlDescription, error: null };
}

// =============================================================================
// Detail page: alternatives
// =============================================================================

export async function fetchAlternatives(
  category: string,
  excludeSlug: string,
  locale: 'en' | 'ko',
  limit = 4,
): Promise<ProductCardData[]> {
  const db = getPublicSupabase();
  if (!db) return [];
  const { data } = await db
    .from('ai_products')
    .select(CARD_COLUMNS)
    .eq('primary_category', category)
    .eq('is_published', true)
    .neq('slug', excludeSlug)
    .order('featured', { ascending: false })
    .order('sort_order')
    .limit(limit);
  if (!data) return [];
  return (data as ProductCardData[]).map((p) => ({
    ...p,
    name: (locale === 'ko' ? (p as any).name_ko || p.name : p.name) as string,
    tagline: (locale === 'ko' ? (p as any).tagline_ko || p.tagline : p.tagline) as string | null,
  }));
}

// =============================================================================
// Homepage featured
// =============================================================================

export async function fetchHomeFeaturedProducts(): Promise<HomeFeaturedProduct[]> {
  if (!supabase) return [];

  const { data, error } = await supabase
    .from('ai_products')
    .select('id, slug, name, name_ko, tagline, tagline_ko, logo_url, pricing, korean_support')
    .eq('is_published', true)
    .eq('featured', true)
    .order('featured_order')
    .limit(5);

  if (error) return [];
  return (data ?? []) as HomeFeaturedProduct[];
}
