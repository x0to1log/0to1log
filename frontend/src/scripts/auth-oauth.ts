import { createClient } from '@supabase/supabase-js';

const COMING_SOON_PROVIDERS = new Set(['kakao']);

function resolveRedirectTarget(button: HTMLButtonElement, root: HTMLElement): string {
  return (
    button.dataset.redirectTo ||
    root.dataset.redirectTo ||
    new URLSearchParams(window.location.search).get('redirectTo') ||
    '/'
  );
}

function setButtonsDisabled(buttons: HTMLButtonElement[], disabled: boolean): void {
  buttons.forEach((button) => {
    button.disabled = disabled;
  });
}

export function initOAuthButtons(rootNode: ParentNode = document): void {
  const roots =
    rootNode instanceof HTMLElement && rootNode.matches('[data-oauth-root]')
      ? [rootNode]
      : Array.from(rootNode.querySelectorAll<HTMLElement>('[data-oauth-root]'));

  const supabaseUrl = import.meta.env.PUBLIC_SUPABASE_URL;
  const supabaseKey = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseKey) return;

  roots.forEach((root) => {
    const buttons = Array.from(root.querySelectorAll<HTMLButtonElement>('[data-provider]'));

    buttons.forEach((button) => {
      if (button.dataset.oauthInit === 'true') return;
      button.dataset.oauthInit = 'true';

      button.addEventListener('click', async () => {
        const provider = button.dataset.provider;
        if (!provider) return;

        if (COMING_SOON_PROVIDERS.has(provider)) {
          const message =
            button.dataset.comingSoonMessage ||
            root.dataset.comingSoonMessage ||
            'Coming soon.';
          window.alert(message);
          return;
        }

        const signingInLabel =
          button.dataset.signingIn ||
          root.dataset.signingIn ||
          'Signing in...';
        const redirectTo = resolveRedirectTarget(button, root);
        const callbackUrl = `${window.location.origin}/auth/callback`;

        setButtonsDisabled(buttons, true);
        button.textContent = signingInLabel;
        sessionStorage.setItem('oauth_redirect', redirectTo);

        try {
          const supabase = createClient(supabaseUrl, supabaseKey);
          const { error } = await supabase.auth.signInWithOAuth({
            provider: provider as 'github' | 'google' | 'kakao',
            options: { redirectTo: callbackUrl },
          });

          if (error) {
            setButtonsDisabled(buttons, false);
          }
        } catch {
          setButtonsDisabled(buttons, false);
        }
      });
    });
  });
}
