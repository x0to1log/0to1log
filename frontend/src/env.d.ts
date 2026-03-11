/// <reference types="astro/client" />

declare namespace App {
  interface Locals {
    user?: import('@supabase/supabase-js').User;
    accessToken?: string;
    isAdmin?: boolean;
    cspNonce?: string;
    profile?: {
      display_name: string | null;
      username: string | null;
      username_changed_at: string | null;
      avatar_url: string | null;
      persona: string | null;
      preferred_locale: string;
      handbook_level: string;
      is_public: boolean;
      onboarding_completed: boolean;
    };
  }
}
