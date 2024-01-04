rm -rf staticfiles/*
python manage.py collectstatic -i admin -i django_extensions -i rest_framework -i ckeditor -i rest_framework_swagger -i *.txt -i *.md -i LICENSE
python manage.py compress --force

date=`date +%Y%m%d%H%M%S`
echo "The current datetime is: $date"

git add staticfiles/
git commit -m "compressed staticfiles at $date"
git push origin master