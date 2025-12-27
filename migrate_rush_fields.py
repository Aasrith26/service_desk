"""Add rush threshold columns to clinic table"""
from sqlalchemy import create_engine, text, inspect

# Connect to the database
engine = create_engine('sqlite:///clinic.db')

with engine.connect() as conn:
    # Check existing columns
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('clinic')]
    print(f"Existing columns: {columns}")
    
    # Add missing columns if needed
    if 'rush_low_threshold' not in columns:
        conn.execute(text('ALTER TABLE clinic ADD COLUMN rush_low_threshold INTEGER DEFAULT 3'))
        print("Added rush_low_threshold column")
    else:
        print("rush_low_threshold already exists")
        
    if 'rush_medium_threshold' not in columns:
        conn.execute(text('ALTER TABLE clinic ADD COLUMN rush_medium_threshold INTEGER DEFAULT 7'))
        print("Added rush_medium_threshold column")
    else:
        print("rush_medium_threshold already exists")
        
    if 'average_consultation_minutes' not in columns:
        conn.execute(text('ALTER TABLE clinic ADD COLUMN average_consultation_minutes INTEGER DEFAULT 10'))
        print("Added average_consultation_minutes column")
    else:
        print("average_consultation_minutes already exists")
    
    conn.commit()
    print("Migration complete!")
