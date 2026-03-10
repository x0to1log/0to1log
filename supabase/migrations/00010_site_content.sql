-- Site Content: admin-editable editorial text (bilingual ko/en)
-- Used by list page rails, masthead, and other editorial sections.

CREATE TABLE site_content (
  key TEXT PRIMARY KEY,
  value_ko TEXT NOT NULL DEFAULT '',
  value_en TEXT NOT NULL DEFAULT '',
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE site_content ENABLE ROW LEVEL SECURITY;

-- Public read (site content is not secret)
CREATE POLICY "Anyone can read site_content"
  ON site_content FOR SELECT USING (true);

-- Admin-only update
CREATE POLICY "Admin can update site_content"
  ON site_content FOR UPDATE USING (
    EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid() AND is_active = true)
  );

-- Seed with current hardcoded values
INSERT INTO site_content (key, value_ko, value_en) VALUES
  ('editorial_note',
   '오늘의 변화와 작업 기록을 AI 뉴스, 서재, 커리어, 프로젝트의 흐름으로 엮어 둡니다.',
   'A daily record of shifts, working notes, and build logs across AI, study, career, and projects.'),

  ('handbook_intro',
   'AI, 백엔드, 프론트엔드, 보안 등 실무 기술 용어를 한눈에 정리합니다.',
   'A concise reference of technical terms across AI, backend, frontend, security, and more.'),

  ('news_masthead',
   '최신 AI 뉴스 모음집',
   'Latest AI News'),

  ('news_edition_label',
   '빌더스 데일리',
   'Builder''s Daily'),

  ('news_subkicker',
   '["AI · 논문 · 프로젝트", "데일리 큐레이션", "공개 열람"]',
   '["AI · Papers · Projects", "Daily Curation", "Open Access"]'),

  ('handbook_masthead',
   'AI 용어집',
   'AI Glossary'),

  ('handbook_edition_label',
   'CS · AI · Infra',
   'CS · AI · Infra'),

  ('handbook_subkicker',
   '["용어 사전", "레퍼런스", "학습"]',
   '["Glossary", "Reference", "Learn"]'),

  ('start_here_sections',
   '[{"slug":"ai-news","label":"AI 뉴스","description":"오늘 바뀐 것부터 가장 빠르게 봅니다."},{"slug":"study","label":"학습","description":"공부 개념과 메모 노트를 남깁니다."},{"slug":"career","label":"커리어","description":"일과 성장을 기록합니다."},{"slug":"project","label":"프로젝트","description":"만드는 과정과 회고를 기록합니다."}]',
   '[{"slug":"ai-news","label":"AI News","description":"Start with what changed today."},{"slug":"study","label":"Study","description":"Follow concepts, notes, and references."},{"slug":"career","label":"Career","description":"Read decisions about work and growth."},{"slug":"project","label":"Project","description":"See build logs and shipping notes."}]'),

  ('volume_issue',
   '제01권 · 제10호',
   'Vol.01 · No.10');
