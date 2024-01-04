import os.path
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.urls.resolvers import ResolverMatch


class Items:
    def __getitem__(self, index):
        print("index:", index)
        return (100, 200, 300)[index]


if __name__ == "__main__":
    i = Items()
    print(i)
    a, b, c = i
    print(a, b, c)
