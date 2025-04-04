# referee/add_referee.py

import os
import sys
import django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yazlab21.settings')
django.setup()

from referee.models import referee

def add_referees():
    """Veritabanına kategorilere uygun hakemler ekleyen fonksiyon"""
    
    referee_data = [
        {"name": "Hakem-1", "branch": "1-Artificial Intelligence and Machine Learning"},
        {"name": "Hakem-2", "branch": "1-Artificial Intelligence and Machine Learning"},
        {"name": "Hakem-3", "branch": "1-Artificial Intelligence and Machine Learning"},
        
        {"name": "Hakem-4", "branch": "2-Human-Computer Interaction"},
        {"name": "Hakem-5", "branch": "2-Human-Computer Interaction"},
        {"name": "Hakem-6", "branch": "2-Human-Computer Interaction"},
        
        {"name": "Hakem-7", "branch": "3-Big Data and Data Analytics"},
        {"name": "Hakem-8", "branch": "3-Big Data and Data Analytics"},
        {"name": "Hakem-9", "branch": "3-Big Data and Data Analytics"},
        
        {"name": "Hakem-10", "branch": "4-Cyber Security"},
        {"name": "Hakem-11", "branch": "4-Cyber Security"},
        {"name": "Hakem-12", "branch": "4-Cyber Security"},
        
        {"name": "Hakem-13", "branch": "5-Network and Distributed Systems"},
        {"name": "Hakem-14", "branch": "5-Network and Distributed Systems"},
        {"name": "Hakem-15", "branch": "5-Network and Distributed Systems"},
    ]
    
    added_count = 0
    updated_count = 0
    
    for ref_data in referee_data:
        try:
            existing_ref = referee.objects.get(referee_name=ref_data["name"])
            # Hakem zaten var, branch'i güncelle
            existing_ref.referee_branch = ref_data["branch"]
            existing_ref.save()
            updated_count += 1
            print(f'Hakem güncellendi: {existing_ref.referee_name} - {existing_ref.referee_branch}')
        except referee.DoesNotExist:
            # Yeni hakem oluştur
            new_ref = referee(
                referee_name=ref_data["name"],
                referee_branch=ref_data["branch"]
            )
            new_ref.save()
            added_count += 1
            print(f'Hakem eklendi: {new_ref.referee_name} - {new_ref.referee_branch}')
    
    print(f'Toplam {added_count} yeni hakem eklendi, {updated_count} hakem güncellendi.')

if __name__ == "__main__":
    add_referees()