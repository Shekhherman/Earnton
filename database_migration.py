import sqlite3
import os

def migrate_database():
    """Migrate database schema to add agreement_accepted field."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'botdata.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add agreement_accepted column if it doesn't exist
        cursor.execute('''
            SELECT COUNT(*) 
            FROM pragma_table_info('users') 
            WHERE name = 'agreement_accepted'
        ''')
        
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                ALTER TABLE users 
                ADD COLUMN agreement_accepted BOOLEAN DEFAULT FALSE
            ''')
            
            # Update existing users to have agreement_accepted = FALSE
            cursor.execute('''
                UPDATE users 
                SET agreement_accepted = FALSE
            ''')
            
            conn.commit()
            print("Database migration completed successfully!")
        else:
            print("Database is already up to date.")
            
    except sqlite3.Error as e:
        print(f"Error during database migration: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
