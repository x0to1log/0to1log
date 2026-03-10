-- Sync site_content keys and copy for existing databases.
-- Use after 00010_site_content.sql has already created the table.

INSERT INTO site_content (key, value_ko, value_en) VALUES
  ('editorial_note',
   '오늘 바뀐 것부터 가장 빠르게 보고, 필요한 맥락은 차분하게 붙이는 AI 퍼블리케이션입니다.',
   'A daily publication for reading the latest AI shifts first, then slowing down for the right context.'),

  ('handbook_intro',
   'AI, 백엔드, 보안, 인프라 실무에서 자주 만나는 기술 용어를 짧고 또렷하게 정리합니다.',
   'A concise reference for technical terms that appear across AI, backend, security, and infrastructure work.'),

  ('news_masthead',
   '최신 AI 뉴스 모음집',
   'Latest AI News'),

  ('news_edition_label',
   '빌더의 데일리',
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
   'Vol.01 · No.10'),

  ('home_title',
   'AI 뉴스와 인사이트',
   'AI News & Insights'),

  ('home_subtitle',
   '가치를 담는 기록',
   'From Void to Value'),

  ('home_intro',
   '지금 중요한 AI 변화를 빠르게 읽고, 실무 맥락까지 함께 이해할 수 있도록 정리한 데일리 퍼블리케이션입니다.',
   'A concise publication for people who want the latest AI shifts, the right technical context, and a clearer path from signal to action.'),

  ('about_tagline',
   '신호를 맥락으로 바꾸는 기록',
   'From signal to understanding'),

  ('about_publication_intro',
   '0to1log는 빠르게 쏟아지는 AI 소식 속에서 중요한 변화만 골라, 실무 맥락과 함께 정리하는 퍼블리케이션입니다.',
   '0to1log is a focused publication for people who want the latest AI shifts without losing technical context or practical relevance.'),

  ('about_publication_detail',
   'AI 뉴스와 AI 용어집을 함께 운영해, 빠른 변화는 빠르게 읽고 필요한 개념은 다시 돌아와 정리할 수 있게 만드는 것이 목표입니다.',
   'The publication pairs AI News with an AI Glossary so readers can follow fast-moving stories and still slow down when a concept needs unpacking.'),

  ('about_editor_intro',
   'Amy Domin Kim은 LLM 애플리케이션, 데이터 시스템, 웹 제품을 연결해 만드는 엔지니어입니다. 0to1log는 개인 학습 기록에서 시작해, 지금은 AI를 더 잘 이해하기 위한 공개 작업실로 확장되고 있습니다.',
   'Amy Domin Kim builds with LLM applications, data systems, and product-minded engineering. 0to1log started as a personal learning record and grew into a public operating surface for AI curation and explanation.'),

  ('library_empty_saved',
   '아직 저장한 글이 없습니다. 나중에 다시 볼 기사와 용어를 모아둘 수 있습니다.',
   'No saved items yet. Bookmark articles and terms to keep them here.'),

  ('library_empty_read',
   '아직 읽은 기록이 없습니다. AI 뉴스와 용어집을 둘러보며 흐름을 시작해 보세요.',
   'No reading history yet. Start exploring articles and glossary terms.'),

  ('library_empty_progress',
   '용어집을 읽기 시작하면 학습 현황이 여기에 쌓입니다.',
   'Visit handbook terms to start tracking your learning progress.')
ON CONFLICT (key) DO UPDATE
SET
  value_ko = EXCLUDED.value_ko,
  value_en = EXCLUDED.value_en,
  updated_at = now();
