import csv
import decimal

from django.core.management.base import BaseCommand
from volumes.models import Volume


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open("/home/bitrix/ext_www/skidkipril.plazma-t.ru/static/data/upload_1.csv", "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                obj, created = Volume.objects.get_or_create(
                    company_id=row['company_id'],
                    portal_id=row['portal_id'],
                    defaults={'volume': row['volume'], 'inn': row['inn']}
                )

                if not created:
                    with open("/home/bitrix/ext_www/skidkipril.plazma-t.ru/static/data/result.txt", "a", encoding="utf-8") as resultfile:
                        resultfile.write(f'{obj.pk = }: {obj.volume} + {row["volume"]} = ')
                        obj.volume += decimal.Decimal(row['volume'])
                        obj.save()
                        resultfile.write(f'{obj.volume}\n')
