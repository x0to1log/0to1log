-- 00045_products_archived_column.sql
-- Add archived boolean to ai_products for soft delete support.

ALTER TABLE ai_products ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT FALSE;
