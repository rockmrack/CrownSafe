-- Fix database schema by adding missing columns
-- Run this on your production database

-- Add severity column if it doesn't exist
ALTER TABLE recalls_enhanced 
ADD COLUMN IF NOT EXISTS severity VARCHAR(50);

-- Add risk_category column if it doesn't exist
ALTER TABLE recalls_enhanced 
ADD COLUMN IF NOT EXISTS risk_category VARCHAR(100);

-- Optional: Set default values for existing rows
UPDATE recalls_enhanced 
SET severity = 'medium' 
WHERE severity IS NULL;

UPDATE recalls_enhanced 
SET risk_category = 'general' 
WHERE risk_category IS NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_recalls_severity ON recalls_enhanced(severity);
CREATE INDEX IF NOT EXISTS idx_recalls_risk_category ON recalls_enhanced(risk_category);

-- Verify the columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'recalls_enhanced' 
  AND column_name IN ('severity', 'risk_category');
