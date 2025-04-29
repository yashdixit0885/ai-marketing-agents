import psycopg2
from config.settings import settings

def fix_database():
    """Add missing columns to articles table and create article_exports table."""
    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    print("Adding missing columns...")
    
    # Create enum types if they don't exist
    cur.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'review_status') THEN
            CREATE TYPE review_status AS ENUM ('pending', 'approved', 'rejected', 'needs_revision');
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'export_status') THEN
            CREATE TYPE export_status AS ENUM ('pending_review', 'approved', 'rejected', 'needs_revision');
        END IF;
    END
    $$;
    """)
    
    # Add columns to articles table if they don't exist
    cur.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='articles' AND column_name='review_status') THEN
            ALTER TABLE articles ADD COLUMN review_status review_status DEFAULT 'pending';
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='articles' AND column_name='review_comments') THEN
            ALTER TABLE articles ADD COLUMN review_comments TEXT;
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='articles' AND column_name='reviewed_by') THEN
            ALTER TABLE articles ADD COLUMN reviewed_by VARCHAR(255);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='articles' AND column_name='review_date') THEN
            ALTER TABLE articles ADD COLUMN review_date TIMESTAMP WITH TIME ZONE;
        END IF;
    END
    $$;
    """)
    
    # Create article_exports table if it doesn't exist
    cur.execute("""
    CREATE TABLE IF NOT EXISTS article_exports (
        id SERIAL PRIMARY KEY,
        article_id INTEGER NOT NULL REFERENCES articles(id),
        doc_id VARCHAR(255) NOT NULL,
        folder_id VARCHAR(255) NOT NULL,
        doc_url VARCHAR(512),
        export_date TIMESTAMP WITH TIME ZONE DEFAULT now(),
        status export_status DEFAULT 'pending_review',
        review_comments TEXT,
        reviewed_by VARCHAR(255),
        review_date TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE
    );
    """)
    
    print("Database schema fixed successfully!")
    
    # Close connection
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_database()