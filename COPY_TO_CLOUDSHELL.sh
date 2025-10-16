# Re-add your IP
MY_IP=$(curl -s https://checkip.amazonaws.com)
SG_ID=sg-0e2aed27cbf2213ed
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5432 --cidr $MY_IP/32 --region eu-north-1

# Check which database has data
PGPASSWORD='MandarunLabadiena25!' psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com -U babyshield_user -d postgres -c 'SELECT COUNT(*) FROM recalls_enhanced;'

PGPASSWORD='MandarunLabadiena25!' psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com -U babyshield_user -d babyshield_db -c 'SELECT COUNT(*) FROM recalls_enhanced;'

# Enable pg_trgm on babyshield_db (the correct database)
PGPASSWORD='MandarunLabadiena25!' psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com -U babyshield_user -d babyshield_db << 'SQL'
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm ON recalls_enhanced USING gin (lower(brand) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm ON recalls_enhanced USING gin (lower(description) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm ON recalls_enhanced USING gin (lower(hazard) gin_trgm_ops);
SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm';
SQL

# Remove IP
aws ec2 revoke-security-group-ingress --group-id $SG_ID --protocol tcp --port 5432 --cidr $MY_IP/32 --region eu-north-1
