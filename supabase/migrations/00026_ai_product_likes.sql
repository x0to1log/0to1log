-- ai_product_likes: 사용자가 AI 제품을 찜(하트)하는 기능

CREATE TABLE ai_product_likes (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  product_id  uuid NOT NULL REFERENCES ai_products(id) ON DELETE CASCADE,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, product_id)
);

-- RLS
ALTER TABLE ai_product_likes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user can read own likes"
  ON ai_product_likes FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "user can insert own likes"
  ON ai_product_likes FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "user can delete own likes"
  ON ai_product_likes FOR DELETE
  USING (auth.uid() = user_id);

-- like_count 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION update_product_like_count()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE ai_products SET like_count = like_count + 1 WHERE id = NEW.product_id;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE ai_products SET like_count = GREATEST(like_count - 1, 0) WHERE id = OLD.product_id;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_product_like_count
AFTER INSERT OR DELETE ON ai_product_likes
FOR EACH ROW EXECUTE FUNCTION update_product_like_count();
