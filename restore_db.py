import os
import django
from django.db import connection

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

def run_restore():
    print("Starting database restore...")
    file_path = 'restore_data.sql'
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    statement = ""
    count = 0
    
    with connection.cursor() as cursor:
        # Disable foreign key checks temporarily
        cursor.execute('SET FOREIGN_KEY_CHECKS=0;')
        
        for line in lines:
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith('--') or stripped.startswith('/*'):
                continue
                
            statement += line
            
            if stripped.endswith(';'):
                try:
                    cursor.execute(statement)
                    count += 1
                except Exception as e:
                    # Ignore some errors like 'Table already exists' if relevant, or just print
                    print(f"Error executing statement #{count}: {e}")
                    # print(f"Statement: {statement[:100]}...")
                
                statement = ""

        # Re-enable foreign key checks
        cursor.execute('SET FOREIGN_KEY_CHECKS=1;')
        
    print(f"Restore finished. Executed {count} statements.")

if __name__ == '__main__':
    run_restore()
