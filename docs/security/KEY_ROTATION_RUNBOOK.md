# Secret Key Rotation Runbook

When a key is compromised or as part of periodic rotation, follow the steps below.

## 1. Supabase Keys (anon / service_role)

1. Supabase Dashboard > Project Settings > API > Regenerate keys
2. Update environment variables:
   - **Vercel** (frontend): `PUBLIC_SUPABASE_URL`, `PUBLIC_SUPABASE_ANON_KEY`
   - **Railway** (backend): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
3. Redeploy both services
4. Verify: visit site, confirm login works, admin panel loads
5. Old JWTs become invalid immediately — active users will need to re-login

## 2. OpenAI API Key

1. OpenAI Dashboard > API Keys > Create new key
2. Update Railway env: `OPENAI_API_KEY`
3. Revoke old key in OpenAI Dashboard
4. Redeploy backend
5. Verify: trigger a test pipeline run

## 3. Tavily API Key

1. Tavily Dashboard > API Keys > Regenerate
2. Update Railway env: `TAVILY_API_KEY`
3. Redeploy backend
4. Verify: trigger a test pipeline run with search step

## 4. Vercel Revalidate Secret

1. Generate new secret: `openssl rand -base64 32`
2. Update Vercel env: `REVALIDATE_SECRET`
3. Update Railway env: `REVALIDATE_SECRET` (backend calls frontend revalidate)
4. Redeploy both services
5. Verify: publish a post via admin, confirm revalidation works

## 5. Google Analytics / Clarity (public, low risk)

These are public measurement IDs, not secrets. Rotation is only needed if the property itself is compromised.

1. Create new GA4 property / Clarity project
2. Update Vercel env: `PUBLIC_GA4_ID`, `PUBLIC_CLARITY_ID`
3. Redeploy frontend

## Post-Rotation Checklist

- [ ] Old key revoked/deleted at source
- [ ] New key set in all environments (Vercel + Railway)
- [ ] Both services redeployed
- [ ] Smoke test passed (login, admin, pipeline)
- [ ] No old key references in logs or error tracking
