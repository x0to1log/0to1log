-- Site Content: admin-editable editorial text (bilingual ko/en)
-- Used by public rails, masthead copy, and marketing/onboarding sections.

CREATE TABLE site_content (
  key TEXT PRIMARY KEY,
  value_ko TEXT NOT NULL DEFAULT '',
  value_en TEXT NOT NULL DEFAULT '',
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE site_content ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read site_content"
  ON site_content FOR SELECT USING (true);

CREATE POLICY "Admin can update site_content"
  ON site_content FOR UPDATE USING (
    EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid() AND is_active = true)
  );

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
   '[{\"label\":\"AI 뉴스\",\"description\":\"오늘 꼭 봐야 할 AI 변화부터 빠르게 읽습니다.\",\"slug\":\"ai-news\"},{\"label\":\"AI 용어집\",\"description\":\"읽다가 막히는 AI 용어를 바로 찾아 이해합니다.\",\"slug\":\"study\"},{\"label\":\"나의 서재\",\"description\":\"읽은 뉴스와 용어를 차곡차곡 모아둡니다.\",\"slug\":\"career\"},{\"label\":\"IT 블로그\",\"description\":\"빌드 과정과 기록을 찬찬히 풀어봅니다.\",\"slug\":\"project\"}]',
   '[{"slug":"ai-news","label":"AI News","description":"Read the most important AI shifts first."},{"slug":"study","label":"AI Glossary","description":"Look up unfamiliar terms without leaving the flow."},{"slug":"career","label":"My Library","description":"Keep the news and terms that stay with you."},{"slug":"project","label":"IT Blog","description":"Explore the builds, reflections, and technical work behind the product."}]'),

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
   '가장 빠르게 AI 변화를 읽고, 필요한 용어를 바로 찾고, 읽은 뉴스와 용어를 쌓아가며, 서로의 해석을 나누는 AI 퍼블리케이션입니다.',
   'An AI publication where readers can follow the latest shifts quickly, look up key terms instantly, build their own archive of news and concepts, and share their interpretations with others.'),

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
   'Visit handbook terms to start tracking your learning progress.');


